"""Prove whether two change sets interfere: "passes alone, fails together".

For a pair (X, Y) with merge base B, a proof of interference of Y on X is a test T_X that encodes the
intent of X, PASSES on X, and FAILS on merge(X, Y). The only difference between X and the merge is Y,
so Y caused the failure. Both directions are checked.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path

import neatlogs

from interlock import entire, gitops
from interlock.llm import LLM, MID, STRONG, BudgetExceeded, extract_code
from interlock.testrun import pytest

TEST_FILE = "tests/test_interlock_intent.py"
MAX_REPAIRS = 2


def _ladder() -> list[tuple[str, int]]:
    """Which models write intent tests, cheapest first, with how many repairs each gets.
    INTERLOCK_MODEL_LADDER=0 uses only the strong model (the pre-ladder behavior)."""
    if os.environ.get("INTERLOCK_MODEL_LADDER", "1") == "0":
        return [(STRONG, MAX_REPAIRS)]
    return [(MID, 1), (STRONG, MAX_REPAIRS)]


def _prompt(name: str, **kw) -> str:
    template = resources.files("interlock.prompts").joinpath(f"{name}.txt").read_text(encoding="utf-8")
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n... [{len(text) - limit} more chars clipped]"


@dataclass
class Direction:
    intent_of: str            # branch whose intent is tested
    against: str              # branch merged in
    verdict: str = "inconclusive"   # interference | holds | inconclusive
    test: str = ""
    on_own_branch: str = ""
    on_base: str = ""
    on_merge: str = ""
    failure: str = ""
    repairs: int = 0
    model: str = ""           # model that wrote the accepted intent test
    confirmation: str = ""    # second-opinion test result: confirmed | representation_only | vacuous


@dataclass
class PairReport:
    run_id: str
    repo: str
    x: str
    y: str
    base: str
    resolution: str = ""              # clean | llm | given
    conflicted_files: list[str] = field(default_factory=list)
    overlap: list[str] = field(default_factory=list)
    intents: dict = field(default_factory=dict)
    existing_tests_on_merge: dict = field(default_factory=dict)
    directions: list[Direction] = field(default_factory=list)
    llm_calls: int = 0
    llm_cache_hits: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    seconds: float = 0.0


def _overlap(wt_x: Path, wt_y: Path, ex: list[dict], ey: list[dict]) -> list[str]:
    """Source entities changed by one side that the other side's changes also change or call.
    Checked in both directions: X's new code may call what Y changed, and Y's may call what X changed."""
    src = lambda es: {(e["path"], e["name"]) for e in es if not e["path"].startswith("tests/")}
    sx, sy = src(ex), src(ey)
    shared = {n for _, n in sx & sy}
    for wt, mine, theirs in ((wt_x, sx, sy), (wt_y, sy, sx)):
        my_names = {n for _, n in mine}
        for path, name in theirs - mine:
            if any(c["name"] in my_names for c in entire.callers(wt, name, path)):
                shared.add(name)
    return sorted(shared)


def _resolve_conflicts(llm: LLM, wt: Path, files: list[str]) -> None:
    with neatlogs.trace("resolver", kind="AGENT", **{"interlock.files": ",".join(files)}):
        for f in files:
            content = (wt / f).read_text(encoding="utf-8")
            fence = "python" if f.endswith(".py") else ""
            text = llm.complete([{"role": "user", "content": _prompt(
                "resolve_conflict", path=f, content=content, language="Python" if fence else "text", fence=fence)}],
                model=STRONG, purpose="resolve_conflict", max_tokens=6000)
            (wt / f).write_text(extract_code(text), encoding="utf-8")
        gitops.commit_all(wt, "Merge with conflicts resolved by an automated resolver")


def _intent_text(info: dict) -> str:
    prompts = [s["prompt"].strip() for s in info.get("sessions", []) if s.get("prompt")]
    return "\n\n".join(prompts) or "(no recorded agent prompt: change made by a human; infer the intent from the diff)"


def _prove_direction(llm: LLM, repo: Path, d: Direction, own_wt: Path, base_wt: Path, merge_wt: Path,
                     base: str, own: str, other: str, intents: dict, shared_files: list[str]) -> Direction:
    with neatlogs.trace(f"prove.{d.intent_of}", kind="AGENT",
                        **{"interlock.intent_of": d.intent_of, "interlock.against": d.against}) as span:
        merged_files = "\n".join(
            f"### {f}\n```python\n{_clip((merge_wt / f).read_text(encoding='utf-8'), 6000)}\n```"
            for f in shared_files if (merge_wt / f).exists())
        prompt = _prompt(
            "synthesize_test",
            x_intent=_intent_text(intents[d.intent_of]),
            x_diff=_clip(gitops.diff(repo, base, own), 12000),
            y_intent=_intent_text(intents[d.against]),
            y_diff=_clip(gitops.diff(repo, base, other, ":!tests"), 8000),
            merged_files=merged_files or "(none)",
        )
        messages = [{"role": "user", "content": prompt}]
        passed = False
        for model, repairs in _ladder():
            with neatlogs.trace(f"synthesize.{model}", kind="CHAIN", **{"interlock.model": model}):
                test = extract_code(llm.complete(messages, model=model, purpose="synthesize_test", max_tokens=3000))
                for attempt in range(repairs + 1):
                    (own_wt / TEST_FILE).write_text(test, encoding="utf-8")
                    own_run = pytest(own_wt, TEST_FILE)
                    if own_run.ok:
                        passed = True
                        break
                    if attempt == repairs:
                        break
                    d.repairs += 1
                    with neatlogs.trace("recover.repair_test", kind="CHAIN", **{"interlock.attempt": attempt + 1}):
                        test = extract_code(llm.complete(
                            [{"role": "user", "content": _prompt("repair_test", test=test, output=own_run.output[-3000:])}],
                            model=model, purpose="repair_test", max_tokens=3000))
            if passed:
                d.model = model
                break
            span.set_attribute("interlock.escalated_from", model)   # recovery: escalate to a stronger model
        if not passed:
            d.test, d.on_own_branch, d.failure = test, "failed", own_run.output[-1500:]
            span.set_attribute("interlock.verdict", d.verdict)
            return d

        d.test, d.on_own_branch = test, "passed"
        (base_wt / TEST_FILE).write_text(test, encoding="utf-8")
        d.on_base = "passed" if pytest(base_wt, TEST_FILE).ok else "failed"
        (merge_wt / TEST_FILE).write_text(test, encoding="utf-8")
        merge_run = pytest(merge_wt, TEST_FILE)
        if merge_run.ok:
            d.on_merge, d.verdict = "passed", "holds"
        else:
            d.on_merge, d.verdict, d.failure = "failed", "interference", merge_run.output[-1500:]
            _confirm(llm, d, base_wt, merge_wt, intents, merged_files)
        span.set_attribute("interlock.verdict", d.verdict)
        return d


def _confirm(llm: LLM, d: Direction, base_wt: Path, merge_wt: Path, intents: dict, merged_files: str) -> None:
    """Second opinion before reporting interference: re-express the same intent in the merged code's own
    representation. Withdraw the proof only if that test passes on the merge AND fails on the base (where
    X's feature does not exist yet), so a weakened or vacuous test can never clear a real conflict."""
    with neatlogs.trace("verify.confirm", kind="CHAIN") as span:
        test = extract_code(llm.complete([{"role": "user", "content": _prompt(
            "confirm_intent", x_intent=_intent_text(intents[d.intent_of]), test=d.test,
            failure=d.failure[-2500:], merged_files=merged_files or "(none)")}],
            model=STRONG, purpose="confirm_intent", max_tokens=3000))
        name = "tests/test_interlock_confirm.py"
        (merge_wt / name).write_text(test, encoding="utf-8")
        on_merge = pytest(merge_wt, name)
        (base_wt / name).write_text(test, encoding="utf-8")
        on_base = pytest(base_wt, name)
        if on_merge.ok and not on_base.ok:
            d.verdict, d.confirmation = "holds", "representation_only"
        elif on_merge.ok:
            d.confirmation = "vacuous"           # passes even without X's feature: not evidence, keep the proof
        else:
            d.confirmation = "confirmed"
        span.set_attribute("interlock.confirmation", d.confirmation)


def prove(repo: Path, x: str, y: str, state_dir: Path, merged: str | None = None,
          budget_usd: float = 1.0, fresh: bool = False) -> PairReport:
    started = time.time()
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = state_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    wts = state_dir / "worktrees" / run_id
    llm = LLM(state_dir, budget_usd=budget_usd, no_cache={"synthesize_test", "repair_test"} if fresh else None)
    X, Y = gitops.rev(repo, x), gitops.rev(repo, y)
    base = gitops.merge_base(repo, X, Y)
    report = PairReport(run_id, str(repo), x, y, base[:10])

    with neatlogs.trace("interlock.prove", kind="WORKFLOW",
                        **{"interlock.run": run_id, "interlock.pair": f"{x}|{y}"}) as root:
        wt = {name: gitops.add_worktree(repo, wts / name, ref)
              for name, ref in (("x", X), ("y", Y), ("base", base), ("merge", merged or X))}
        try:
            with neatlogs.trace("planner", kind="AGENT"):
                ex = entire.entity_changes(wt["x"], base, X)
                ey = entire.entity_changes(wt["y"], base, Y)
                report.overlap = _overlap(wt["x"], wt["y"], ex, ey)
                files = lambda es: {e["path"] for e in es if not e["path"].startswith("tests/")}
                shared_files = sorted(files(ex) | files(ey))
                common_files = files(ex) & files(ey)

            if merged:
                report.resolution = "given"
            else:
                report.conflicted_files = gitops.merge(wt["merge"], Y)
                if report.conflicted_files:
                    report.resolution = "llm"
                    _resolve_conflicts(llm, wt["merge"], report.conflicted_files)
                else:
                    report.resolution = "clean"

            with neatlogs.trace("intent", kind="AGENT"):
                report.intents = {x: entire.intent(repo, wt["x"], base, X), y: entire.intent(repo, wt["y"], base, Y)}

            existing = pytest(wt["merge"])
            report.existing_tests_on_merge = {"collected": existing.collected,
                                              "passed": sum(o == "passed" for o in existing.outcomes.values()),
                                              "failed": existing.failed}

            # Free pre-check (no model call): no shared or called entities, no shared source files, a clean
            # merge and a green existing suite on it -> the pair is cleared by entire-graph alone.
            cleared = (not report.overlap and not common_files and not report.conflicted_files and existing.ok)
            if cleared:
                with neatlogs.trace("cleared_by_graph", kind="CHAIN"):
                    report.directions = [Direction(intent_of=a, against=b, verdict="holds", on_merge="cleared")
                                         for a, b in ((x, y), (y, x))]

            for own, other, own_ref, other_ref in (() if cleared else ((x, y, X, Y), (y, x, Y, X))):
                d = Direction(intent_of=own, against=other)
                try:
                    _prove_direction(llm, repo, d, wt["x" if own == x else "y"], wt["base"], wt["merge"],
                                     base, own_ref, other_ref, report.intents, shared_files)
                except BudgetExceeded as e:
                    d.verdict, d.failure = "inconclusive", str(e)
                report.directions.append(d)
        finally:
            _cleanup(report, llm, root, wt, repo, started)
    return _write(report, run_dir)


def _cleanup(report: PairReport, llm: LLM, root, wt: dict, repo: Path, started: float) -> None:
    for path in wt.values():
        gitops.remove_worktree(repo, path)
    report.llm_calls, report.llm_cache_hits = llm.calls, llm.cache_hits
    report.cost_usd = round(llm.spent_usd, 6)
    report.tokens_in = llm.tokens_in
    report.seconds = round(time.time() - started, 1)
    root.set_attribute("interlock.verdicts", ",".join(d.verdict for d in report.directions))
    root.set_attribute("interlock.cost_usd", report.cost_usd)


def _write(report: PairReport, run_dir: Path) -> PairReport:
    (run_dir / "report.json").write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    for d in report.directions:
        if d.test:
            (run_dir / f"test_intent_of_{d.intent_of.replace('/', '_')}.py").write_text(d.test, encoding="utf-8")
    return report
