"""Goal mode: land a set of branches onto a target branch, provably consistent.

The goal is finished only when every branch is landed (or explicitly escalated) and the full suite
passes on the final target. The environment may change while we work: if someone else moves the
target branch (drift), we detect it, work out which remaining branches the new commits touch, and
re-check only those. Ref updates are compare-and-swap, so a concurrent push is never overwritten.
"""

import json
import time
from dataclasses import asdict
from pathlib import Path

import neatlogs

from interlock import entire, gitops
from interlock.coordinator import resolve
from interlock.prover import prove
from interlock.testrun import pytest


def _source_entities(repo: Path, base: str, head: str) -> list[dict]:
    return [e for e in entire.entity_changes(repo, base, head) if not e["path"].startswith("tests/")]


def plan(repo: Path, branches: list[str], into: str) -> dict:
    """Order branches so the ones that change widely-used code (providers) land first."""
    with neatlogs.trace("plan", kind="AGENT") as span:
        rows = []
        for b in branches:
            base = gitops.merge_base(repo, b, into)
            ents = _source_entities(repo, base, b)
            rows.append({"branch": b, "base": base[:10], "entities": sorted({e["name"] for e in ents}),
                         "dependents": sum(e.get("dependents_count", 0) for e in ents)})
        for r in rows:
            r["shares_with"] = sorted(o["branch"] for o in rows
                                      if o is not r and set(o["entities"]) & set(r["entities"]))
        order = [r["branch"] for r in sorted(rows, key=lambda r: (-r["dependents"], r["branch"]))]
        span.set_attribute("interlock.order", " -> ".join(order))
        return {"order": order, "branches": rows}


def _drift(repo: Path, expected: str, actual: str, remaining: list[str]) -> dict:
    """Someone else moved the target. Which remaining branches do the new commits touch?"""
    with neatlogs.trace("drift", kind="AGENT") as span:
        commits = gitops.git(repo, "log", "--format=%h %an: %s", f"{expected}..{actual}").out.strip().splitlines()
        touched = {e["name"] for e in _source_entities(repo, expected, actual)}
        affected = []
        for b in remaining:
            base = gitops.merge_base(repo, b, actual)
            mine = {e["name"] for e in _source_entities(repo, base, b)}
            if mine & touched:
                affected.append(b)
        span.set_attribute("interlock.drift_commits", len(commits))
        span.set_attribute("interlock.affected", ",".join(affected))
        return {"commits": commits, "entities": sorted(touched), "affected": affected,
                "unaffected": [b for b in remaining if b not in affected]}


def _land_one(repo: Path, branch: str, into: str, old: str, wt_path: Path) -> tuple[bool, str, str]:
    """Merge `branch` onto `old` (the target commit we verified against) in a scratch worktree, run the
    suite, then compare-and-swap the target ref from `old`. If anyone moved the target since we
    verified, the swap fails and the caller treats it as drift."""
    wt = gitops.add_worktree(repo, wt_path, old)
    try:
        if gitops.git(repo, "merge-base", "--is-ancestor", old, branch).ok:
            gitops.git(wt, "checkout", "-q", "--detach", branch)   # fast-forward
        elif gitops.merge(wt, branch):
            return False, old, "merge conflicts at landing time"
        suite = pytest(wt)
        if not suite.ok:
            return False, old, f"suite fails after merge: {', '.join(suite.failed[:5]) or 'collection error'}"
        new = gitops.git(wt, "rev-parse", "HEAD").out.strip()
        cas = gitops.git(repo, "update-ref", f"refs/heads/{into}", new, old)
        if not cas.ok:
            return False, old, "target moved during landing (compare-and-swap failed)"
        return True, new, f"{len(suite.outcomes)} tests passed"
    finally:
        gitops.remove_worktree(repo, wt)


def land(repo: Path, branches: list[str], into: str, state_dir: Path, rounds: int = 3,
         budget_usd: float = 2.0) -> dict:
    started = time.time()
    run_id = "land-" + time.strftime("%Y%m%d-%H%M%S")
    run_dir = state_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"run_id": run_id, "into": into, "goal": f"land {', '.join(branches)} on {into}",
             "events": [], "landed": [], "escalated": []}

    def event(kind: str, **info):
        state["events"].append({"at": time.strftime("%H:%M:%S"), "event": kind, **info})
        (run_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    with neatlogs.trace("interlock.land", kind="WORKFLOW", **{"interlock.run": run_id, "interlock.goal": state["goal"]}) as root:
        p = plan(repo, branches, into)
        state["plan"] = p
        event("plan", order=p["order"])
        expected = gitops.rev(repo, into)
        queue = list(p["order"])

        while queue:
            b = queue.pop(0)
            with neatlogs.trace(f"land.{b}", kind="CHAIN", **{"interlock.branch": b}) as span:
                actual = gitops.rev(repo, into)
                if actual != expected:
                    d = _drift(repo, expected, actual, [b, *queue])
                    event("drift", **d)
                    expected = actual

                if gitops.git(repo, "merge-base", "--is-ancestor", b, into).ok:
                    state["landed"].append(b)
                    event("already_integrated", branch=b, detail=f"{b} is already contained in {into}")
                    span.set_attribute("interlock.outcome", "already_integrated")
                    continue

                base = gitops.merge_base(repo, b, into)
                if base != actual:
                    # The target has moved past this branch's base: prove the integration before landing.
                    report = asdict(prove(repo, b, into, state_dir, budget_usd=budget_usd))
                    verdicts = [x["verdict"] for x in report["directions"]]
                    event("prove", branch=b, against=into, verdicts=verdicts,
                          conflicts=report["conflicted_files"], run=report["run_id"])
                    if "interference" in verdicts or report["conflicted_files"]:
                        st = resolve(repo, b, into, state_dir, rounds=rounds, budget_usd=budget_usd,
                                     force_adapts=b, report=report)
                        event("coordinate", branch=b, status=st["status"], rounds=len(st.get("rounds", [])),
                              run=st["run_id"])
                        if st["status"] != "resolved":
                            state["escalated"].append(b)
                            span.set_attribute("interlock.outcome", "escalated")
                            continue

                for attempt in range(3):
                    ok, new, info = _land_one(repo, b, into, expected,
                                              state_dir / "worktrees" / run_id / f"land-{len(state['landed'])}")
                    if ok or "compare-and-swap" not in info:
                        break
                    event("retry", branch=b, reason=info)       # someone pushed while we landed
                    d = _drift(repo, expected, gitops.rev(repo, into), [b, *queue])
                    event("drift", **d)
                    expected = gitops.rev(repo, into)
                    if b in d["affected"]:
                        queue.insert(0, b)                       # re-prove against the new target
                        break
                if ok:
                    state["landed"].append(b)
                    expected = new
                    event("landed", branch=b, head=new[:10], detail=info)
                    span.set_attribute("interlock.outcome", "landed")
                elif b not in queue:
                    state["escalated"].append(b)
                    event("escalate", branch=b, reason=info)
                    span.set_attribute("interlock.outcome", "escalated")

        final_wt = gitops.add_worktree(repo, state_dir / "worktrees" / run_id / "final", into)
        try:
            final = pytest(final_wt)
        finally:
            gitops.remove_worktree(repo, final_wt)
        state["final_suite"] = {"passed": sum(o == "passed" for o in final.outcomes.values()), "failed": final.failed}
        state["status"] = "done" if final.ok and not state["escalated"] else ("partial" if final.ok else "failed")
        state["seconds"] = round(time.time() - started, 1)
        root.set_attribute("interlock.status", state["status"])
        event("finish", status=state["status"], landed=state["landed"], escalated=state["escalated"],
              final_suite=state["final_suite"])
    return state
