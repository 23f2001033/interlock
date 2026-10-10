"""Git operations on the target repository. All of them run with repo hooks disabled."""

import re
import shutil
from pathlib import Path

from interlock.tools import NO_HOOKS, Result, run


def git(repo: str | Path, *args: str, timeout: float = 120) -> Result:
    return run(["git", "-C", str(repo), *args], tool="git", env=NO_HOOKS, timeout=timeout)


def rev(repo: str | Path, ref: str) -> str:
    r = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if not r.ok:
        raise ValueError(f"unknown ref {ref!r}: {r.err.strip()}")
    return r.out.strip()


def merge_base(repo: str | Path, a: str, b: str) -> str:
    return git(repo, "merge-base", a, b).out.strip()


def add_worktree(repo: str | Path, path: Path, ref: str) -> Path:
    if path.exists():
        remove_worktree(repo, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    r = git(repo, "worktree", "add", "--detach", "--force", str(path), ref)
    if not r.ok:
        raise RuntimeError(f"worktree add failed: {r.err.strip()}")
    return path


def remove_worktree(repo: str | Path, path: Path) -> None:
    git(repo, "worktree", "remove", "--force", str(path))
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    git(repo, "worktree", "prune")


def merge(wt: Path, ref: str) -> list[str]:
    """Merge `ref` into the worktree's HEAD. Returns the conflicted files ([] when clean)."""
    r = git(wt, "-c", "user.name=interlock", "-c", "user.email=interlock@localhost",
            "merge", "--no-ff", "--no-edit", ref)
    if r.ok:
        return []
    return [f for f in git(wt, "diff", "--name-only", "--diff-filter=U").out.split() if f]


def commit_all(wt: Path, message: str) -> str:
    git(wt, "add", "-A")
    git(wt, "-c", "user.name=interlock", "-c", "user.email=interlock@localhost", "commit", "-q", "-m", message)
    return git(wt, "rev-parse", "HEAD").out.strip()


def diff(repo: str | Path, a: str, b: str, *paths: str, context: int = 3) -> str:
    return git(repo, "diff", f"-U{context}", a, b, "--", *paths).out


def changed_lines(repo: str | Path, a: str, b: str) -> dict[str, list[int]]:
    """Added/modified line numbers (in b) per file, from a zero-context diff."""
    out: dict[str, list[int]] = {}
    current = None
    for line in git(repo, "diff", "-U0", a, b).out.splitlines():
        if line.startswith("+++ "):
            current = None if line.endswith("/dev/null") else line[6:]
        elif line.startswith("@@") and current:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, count = int(m.group(1)), int(m.group(2) or 1)
            out.setdefault(current, []).extend(range(start, start + count))
    return out
