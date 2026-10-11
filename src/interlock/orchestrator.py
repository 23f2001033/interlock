"""Orchestrator.inc (`ao`) adapter: find the ao session that owns a branch, deliver a fix request with
`ao send`, and wait until the agent has pushed new work to that branch and gone idle."""

import json
import time
from pathlib import Path

import neatlogs

from interlock import gitops
from interlock.tools import run


def _ao(*args: str, timeout: float = 30) -> dict | list | None:
    r = run(["ao", *args, "--json"], tool="ao", timeout=timeout)
    if not r.ok:
        return None
    try:
        return json.loads(r.out)
    except json.JSONDecodeError:
        return None


def available() -> bool:
    status = _ao("status")
    return isinstance(status, dict) and status.get("state") == "running"


def _sessions() -> list[dict]:
    data = _ao("session", "ls")
    if isinstance(data, dict):
        data = data.get("sessions") or data.get("items") or []
    return data if isinstance(data, list) else []


def session_for_branch(branch: str) -> dict | None:
    """The live ao session working on `branch` (field names differ across ao versions, so look broadly)."""
    for s in _sessions():
        names = {str(s.get(k, "")) for k in ("branch", "branchName", "worktreeBranch", "git_branch")}
        if branch in names or f"refs/heads/{branch}" in names:
            return s
    return None


def deliver(repo: Path, branch: str, session: dict, message: str, timeout: float = 1200) -> dict:
    """Send the fix request through Orchestrator and wait for a new commit on the branch plus an idle agent."""
    sid = str(session.get("id") or session.get("sessionId"))
    before = gitops.rev(repo, branch)
    with neatlogs.trace("agent_message", kind="AGENT", **{
            "interlock.via": "orchestrator", "interlock.to_session": sid, "interlock.message": message[:4000]}) as span:
        sent = run(["ao", "send", "--session", sid, "--message", message], tool="ao", timeout=60)
        if not sent.ok:
            return {"ok": False, "session_id": sid, "reply": sent.err[-1000:], "agent_cost_usd": None, "turns": None}
        deadline = time.time() + timeout
        status = ""
        while time.time() < deadline:
            time.sleep(10)
            info = _ao("session", "get", sid) or {}
            status = str(info.get("status") or info.get("state") or "")
            moved = gitops.rev(repo, branch) != before
            if moved and status.lower() in ("idle", "waiting", "needs_input", "done", "ready", "review_pending", "pr_open"):
                break
        span.set_attribute("interlock.agent_status", status)
        return {"ok": gitops.rev(repo, branch) != before, "session_id": sid,
                "reply": f"(via Orchestrator; agent status {status or 'unknown'})", "agent_cost_usd": None, "turns": None}
