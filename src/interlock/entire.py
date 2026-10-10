"""Entire integration: entity-level diffs and impact from entire-graph, and the intent behind
AI-made changes from `entire why` (checkpoint, session, model and the agent's original prompt)."""

import json
from pathlib import Path

from interlock.gitops import changed_lines
from interlock.tools import run


def _json(args: list[str], cwd: Path, timeout: float = 180) -> dict | None:
    r = run(["entire", *args], cwd=cwd, tool="entire", timeout=timeout)
    if not r.ok:
        return None
    try:
        return json.loads(r.out)
    except json.JSONDecodeError:
        return None


def entity_changes(wt: Path, base: str, head: str) -> list[dict]:
    """Entity-level changes base..head: [{path, type, kind, name, dependents_count, ...}]."""
    data = _json(["graph", "diff", "--base", base, "--head", head, "--json"], wt)
    if not data:
        return []
    return [{"path": f["path"], **c} for f in data.get("files", []) for c in f.get("changes", [])]


def callers(wt: Path, symbol: str, file: str | None = None) -> list[dict]:
    """Direct and transitive callers of a symbol in the worktree's code."""
    args = ["graph", "impact", "--repo", ".", "--symbol", symbol, "--format", "json", "--depth", "2"]
    if file:
        args += ["--file", file]
    data = _json(args, wt)
    if not data:
        return []
    return [
        {"name": e["endpoint"]["name"], "file": e["endpoint"]["file_path"], "depth": e.get("depth")}
        for e in ((data.get("callers") or {}).get("entries") or [])
    ]


def why(wt: Path, file: str, line: int) -> dict | None:
    data = _json(["why", f"{file}:{line}", "--json"], wt, timeout=60)
    return (data or {}).get("line")


def intent(repo: Path, wt: Path, base: str, head: str, max_lines: int = 8) -> dict:
    """Who made the change base..head and what they were asked to do.

    Samples changed lines (source files first) and asks `entire why` about each, so a change made
    by several sessions or partly by humans is still described correctly."""
    lines = changed_lines(repo, base, head)
    order = sorted(lines, key=lambda f: (f.startswith("tests/") or "/test" in f, f))
    samples = [(f, ls[0]) for f in order for ls in [lines[f]] if ls][:max_lines]
    sessions: dict[str, dict] = {}
    human_lines = 0
    for f, ln in samples:
        info = why(wt, f, ln)
        if not info or info.get("authorship") != "ai" or not info.get("session_id"):
            human_lines += 1
            continue
        sessions.setdefault(info["session_id"], {
            "session_id": info["session_id"],
            "checkpoint_id": info.get("checkpoint_id"),
            "agent": info.get("agent"),
            "model": info.get("model"),
            "prompt": info.get("prompt", ""),
            "commit": info.get("short_commit_sha"),
        })
    return {"sessions": list(sessions.values()), "sampled_lines": len(samples), "human_lines": human_lines}
