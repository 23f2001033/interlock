"""Coordinate a proven interference to resolution.

1. Decide which side adapts (the side building on a contract the other changed on purpose).
2. Write a precise fix request: what the other side changed, and the intent tests that must pass.
3. Deliver it to the agent that made the change by resuming its own Claude Code session
   (session id from Entire) in the worktree where it works, so it keeps its full context.
4. Re-verify: never trust "fixed". Run the saved intent tests and the full suite on the new head.
   Up to N rounds, then escalate.

Run state is saved after every step (state.json), so `resolve --resume <run>` continues after a crash.
"""

import json
import os
import shutil
import time
from dataclasses import asdict
from pathlib import Path

import neatlogs

from interlock import entire, gitops
from interlock.llm import LLM, MID, SMALL, STRONG, extract_code
from interlock.prover import _clip, _intent_text, _prompt, prove
from interlock.testrun import pytest
from interlock.tools import NO_HOOKS, run

AGENT_TOOLS = ["Read", "Edit", "Write", "Glob", "Grep",
               "Bash(uv run pytest:*)", "Bash(uv run python:*)", "Bash(git status:*)", "Bash(git diff:*)",
               "Bash(git merge:*)", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git log:*)", "Bash(git show:*)"]


def _claude_exe() -> str:
    """The real claude executable (the npm .cmd shim mangles multi-line arguments on Windows)."""
    found = shutil.which("claude") or "claude"
    if found.lower().endswith((".cmd", ".ps1", ".bat")) or not Path(found).suffix:
        exe = Path(found).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        if exe.exists():
            return str(exe)
    return found


def owner_worktree(repo: Path, branch: str) -> Path | None:
    """The worktree where `branch` is checked out (where its agent session lives)."""
    current = None
    for line in gitops.git(repo, "worktree", "list", "--porcelain").out.splitlines():
        if line.startswith("worktree "):
            current = Path(line[9:])
        elif line == f"branch refs/heads/{branch}":
            return current
    return None


class Run:
    """Tiny persistent state for one resolve run."""

    def __init__(self, path: Path, data: dict):
        self.path, self.data = path, data

    @classmethod
    def load(cls, path: Path) -> "Run":
        return cls(path, json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def step(self, name: str, **info) -> None:
        self.data.setdefault("steps", []).append({"step": name, "at": time.strftime("%H:%M:%S"), **info})
        self.save()


def who_adapts(llm: LLM, report: dict) -> tuple[str, str]:
    x, y = report["x"], report["y"]
    proofs = "\n".join(f"- intent of {d['intent_of']}: on combination {d['on_merge'] or '-'} ({d['verdict']})"
                       for d in report["directions"])
    text = llm.complete([{"role": "user", "content": _prompt(
        "who_adapts", a=x, b=y, a_intent=_intent_text(report["intents"][x]),
        b_intent=_intent_text(report["intents"][y]), overlap=", ".join(report["overlap"]) or "-", proofs=proofs)}],
        model=MID, purpose="who_adapts", max_tokens=300)
    try:
        decision = json.loads(text[text.index("{"): text.rindex("}") + 1])
        side = x if decision.get("adapts", "").strip().upper().startswith("A") else y
        return side, decision.get("reason", "")
    except (ValueError, json.JSONDecodeError):
        return x, "fallback: the first branch adapts"


def deliver(wt: Path, session_id: str, message: str, timeout: float = 1200) -> dict:
    """Resume the agent's own Claude Code session with the fix request."""
    with neatlogs.trace("agent_message", kind="AGENT", **{
            "interlock.to_session": session_id, "interlock.message": message[:4000]}) as span:
        r = run([_claude_exe(), "-p", "--resume", session_id, "--permission-mode", "acceptEdits",
                 "--allowedTools", *AGENT_TOOLS, "--output-format", "json"],
                cwd=wt, tool="claude", timeout=timeout, env=NO_HOOKS, stdin=message)
        try:
            out = json.loads(r.out)
        except json.JSONDecodeError:
            out = {"is_error": True, "result": (r.err or r.out)[-2000:]}
        span.set_attribute("interlock.agent_reply", (out.get("result") or "")[:4000])
        span.set_attribute("interlock.agent_cost_usd", out.get("total_cost_usd") or 0)
        return {"ok": r.ok and not out.get("is_error"), "session_id": out.get("session_id", session_id),
                "reply": out.get("result", ""), "agent_cost_usd": out.get("total_cost_usd"), "turns": out.get("num_turns")}


def verify(repo: Path, ref: str, tests: dict[str, str], wt_path: Path) -> dict:
    """Run the saved intent tests and the full suite on `ref`."""
    wt = gitops.add_worktree(repo, wt_path, ref)
    try:
        for name, src in tests.items():
            (wt / name).write_text(src, encoding="utf-8")
        intent_run = pytest(wt, *tests.keys())
        suite = pytest(wt)
        return {"head": gitops.rev(repo, ref)[:10], "intent_tests_ok": intent_run.ok, "suite_ok": suite.ok,
                "failed": sorted(set(intent_run.failed + suite.failed)),
                "output": (intent_run.output if not intent_run.ok else suite.output)[-2500:]}
    finally:
        gitops.remove_worktree(repo, wt)


def reexpress_acceptance(llm: LLM, repo: Path, report: dict, tests: dict[str, str], test_owner: dict[str, str],
                         failed: list[str], output: str, head: str, wt_root: Path) -> list[str]:
    """Arbitrate when an acceptance test contradicts the adapting agent's own task (e.g. it hard-codes dollars
    after an intended switch to cents). Re-express that intent in the new head's representation and accept the
    new test only if it passes on the head AND fails on the base, so the intent is still really checked."""
    files = sorted({f"{t.split('::')[0].replace('.', '/')}.py" for t in failed} & set(tests))
    if not files:
        return []
    changed = []
    with neatlogs.trace("arbitrate.reexpress", kind="AGENT", **{"interlock.tests": ",".join(files)}):
        wt_head = gitops.add_worktree(repo, wt_root / "arb-head", head)
        wt_base = gitops.add_worktree(repo, wt_root / "arb-base", report["base"])
        try:
            src = [f for f in gitops.git(repo, "diff", "--name-only", report["base"], head, "--", ":!tests").out.split() if f]
            merged = "\n".join(f"### {f}\n```python\n{_clip((wt_head / f).read_text(encoding='utf-8'), 6000)}\n```"
                               for f in src if (wt_head / f).exists() and f.endswith(".py"))
            for name in files:
                owner = test_owner[name]
                new = extract_code(llm.complete([{"role": "user", "content": _prompt(
                    "confirm_intent", x_intent=_intent_text(report["intents"][owner]), test=tests[name],
                    failure=output[-2500:], merged_files=merged or "(none)")}],
                    model=STRONG, purpose="reexpress_acceptance", max_tokens=3000))
                (wt_head / name).write_text(new, encoding="utf-8")
                (wt_base / name).write_text(new, encoding="utf-8")
                if pytest(wt_head, name).ok and not pytest(wt_base, name).ok:
                    tests[name] = new
                    changed.append(name)
        finally:
            gitops.remove_worktree(repo, wt_head)
            gitops.remove_worktree(repo, wt_base)
    return changed


def resolve(repo: Path, x: str, y: str, state_dir: Path, rounds: int = 3, budget_usd: float = 1.0,
            resume: str | None = None, force_adapts: str | None = None, report: dict | None = None) -> dict:
    llm = LLM(state_dir, budget_usd=budget_usd)
    with neatlogs.trace("interlock.resolve", kind="WORKFLOW", **{"interlock.pair": f"{x}|{y}"}) as root:
        if resume:
            st = Run.load(state_dir / "runs" / resume / "state.json")
        else:
            report = report or asdict(prove(repo, x, y, state_dir, budget_usd=budget_usd))
            st = Run(state_dir / "runs" / report["run_id"] / "state.json",
                     {"run_id": report["run_id"], "x": x, "y": y, "report": report, "status": "proved", "rounds": []})
            st.step("prove", verdicts=[d["verdict"] for d in report["directions"]])
        report = st.data["report"]
        root.set_attribute("interlock.run", st.data["run_id"])
        if st.data.get("status") in ("resolved", "escalated", "no_interference"):
            return st.data

        if not any(d["verdict"] == "interference" for d in report["directions"]) and not report.get("conflicted_files"):
            st.data["status"] = "no_interference"
            st.save()
            return st.data

        test_owner = {f"tests/test_interlock_intent_{d['intent_of'].split('/')[-1].replace('-', '_')}.py": d["intent_of"]
                      for d in report["directions"] if d.get("test") and d["on_own_branch"] == "passed"}
        tests = st.data.get("tests") or {name: next(d["test"] for d in report["directions"] if d["intent_of"] == owner)
                                         for name, owner in test_owner.items()}

        if "adapts" not in st.data:
            with neatlogs.trace("decide", kind="AGENT") as span:
                if force_adapts:
                    side, reason = force_adapts, f"{force_adapts} is landing onto already-integrated code, so it adapts"
                else:
                    side, reason = who_adapts(llm, report)
                span.set_attribute("interlock.adapts", side)
            other = y if side == x else x
            summary = llm.complete([{"role": "user", "content": _prompt(
                "summarize_change", intent=_intent_text(report["intents"][other]),
                diff=_clip(gitops.diff(repo, report["base"], other, ":!tests"), 10000))}],
                model=SMALL, purpose="summarize_change", max_tokens=400)
            st.data.update(adapts=side, other=other, reason=reason, other_summary=summary.strip())
            st.step("decide", adapts=side, reason=reason)

        side, other = st.data["adapts"], st.data["other"]
        sessions = report["intents"][side].get("sessions", [])
        wt = owner_worktree(repo, side)
        if not sessions or wt is None:
            st.data["status"] = "escalated"
            st.step("escalate", reason="no agent session or worktree for the adapting branch (human-authored change?)")
            return st.data
        session_id = st.data.get("session_id") or sessions[0]["session_id"]

        previous_failure = ""
        while len(st.data["rounds"]) < rounds:
            n = len(st.data["rounds"]) + 1
            with neatlogs.trace(f"round.{n}", kind="CHAIN", **{"interlock.round": n}) as span:
                message = _prompt(
                    "fix_request", own=side, other=other,
                    other_task=_intent_text(report["intents"][other]).splitlines()[0].lstrip("# "),
                    other_summary=st.data["other_summary"],
                    tests="\n\n".join(f"`{name}`:\n```python\n{src.strip()}\n```" for name, src in tests.items()),
                    previous_failure=previous_failure)
                st.step("message", round=n, to_session=session_id)
                reply = deliver(wt, session_id, message)
                session_id = reply["session_id"] or session_id
                st.data["session_id"] = session_id
                st.step("agent_replied", round=n, ok=reply["ok"], turns=reply["turns"], agent_cost_usd=reply["agent_cost_usd"])
                # Link the agent's new commit to its session in Entire (we ran it with hooks disabled).
                run(["entire", "session", "attach", session_id, "--force"], cwd=wt, tool="entire", env=NO_HOOKS, timeout=180)

                result = verify(repo, side, tests, state_dir / "worktrees" / st.data["run_id"] / f"verify-{n}")
                ok = result["intent_tests_ok"] and result["suite_ok"]
                if not ok and result["failed"]:
                    # The agent may be right that an acceptance test contradicts its own task: arbitrate.
                    changed = reexpress_acceptance(llm, repo, report, tests, test_owner, result["failed"],
                                                   result["output"], side,
                                                   state_dir / "worktrees" / st.data["run_id"] / f"arb-{n}")
                    if changed:
                        st.data["tests"] = tests
                        st.step("arbitrate", round=n, reexpressed=changed)
                        result = verify(repo, side, tests, state_dir / "worktrees" / st.data["run_id"] / f"verify-{n}b")
                        ok = result["intent_tests_ok"] and result["suite_ok"]
                span.set_attribute("interlock.resolved", ok)
                st.data["rounds"].append({"round": n, "message": message, "reply": reply["reply"][-3000:], **result})
                st.step("verify", round=n, resolved=ok, failed=result["failed"][:10])
                if ok:
                    st.data["status"] = "resolved"
                    st.save()
                    break
                with neatlogs.trace("recover.next_round", kind="CHAIN"):
                    previous_failure = ("\nIMPORTANT: Interlock re-ran the checks on your latest commit "
                                        f"({result['head']}) and they still fail:\n```\n{result['output'][-1500:]}\n```\n"
                                        "Fix the remaining problems, keep both features working, and commit.")
        else:
            st.data["status"] = "escalated"
            st.step("escalate", reason=f"not resolved after {rounds} rounds")

        st.data["llm_cost_usd"] = round(llm.spent_usd + report.get("cost_usd", 0), 6)
        root.set_attribute("interlock.status", st.data["status"])
        st.save()
        return st.data
