import subprocess
from pathlib import Path

import pytest

from interlock import gitops
from interlock.coordinator import owner_worktree
from interlock.llm import extract_code


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    sh(r, "init", "-q", "-b", "main")
    sh(r, "config", "user.name", "t")
    sh(r, "config", "user.email", "t@t")
    (r / "a.py").write_text("x = 1\ny = 2\n")
    sh(r, "add", "-A")
    sh(r, "commit", "-q", "-m", "base")
    return r


def test_changed_lines_reports_added_and_modified_lines(repo: Path):
    base = sh(repo, "rev-parse", "HEAD")
    (repo / "a.py").write_text("x = 1\ny = 3\nz = 4\n")
    (repo / "b.py").write_text("new = True\n")
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", "change")
    assert gitops.changed_lines(repo, base, "HEAD") == {"a.py": [2, 3], "b.py": [1]}


def test_owner_worktree_finds_where_a_branch_is_checked_out(repo: Path, tmp_path: Path):
    wt = tmp_path / "wt-feature"
    sh(repo, "worktree", "add", "-q", "-b", "agent/feature", str(wt))
    assert owner_worktree(repo, "agent/feature").resolve() == wt.resolve()
    assert owner_worktree(repo, "agent/missing") is None


def test_ref_update_is_compare_and_swap(repo: Path):
    """Landing must never overwrite a concurrent push to the target branch."""
    old = sh(repo, "rev-parse", "HEAD")
    (repo / "a.py").write_text("x = 9\n")
    sh(repo, "commit", "-qam", "teammate")
    teammate = sh(repo, "rev-parse", "HEAD")
    sh(repo, "branch", "target", old)
    sh(repo, "update-ref", "refs/heads/target", teammate, old)        # teammate pushes first
    assert not gitops.git(repo, "update-ref", "refs/heads/target", old, old).ok   # our stale CAS fails
    assert sh(repo, "rev-parse", "target") == teammate


def test_merge_reports_conflicted_files(repo: Path, tmp_path: Path):
    sh(repo, "checkout", "-q", "-b", "left")
    (repo / "a.py").write_text("x = 'left'\ny = 2\n")
    sh(repo, "commit", "-qam", "left")
    sh(repo, "checkout", "-q", "-b", "right", "main")
    (repo / "a.py").write_text("x = 'right'\ny = 2\n")
    sh(repo, "commit", "-qam", "right")
    wt = gitops.add_worktree(repo, tmp_path / "scratch", "left")
    try:
        assert gitops.merge(wt, "right") == ["a.py"]
    finally:
        gitops.remove_worktree(repo, wt)


def test_extract_code_takes_the_fenced_block():
    assert extract_code("Here:\n```python\nprint(1)\n```\nthanks") == "print(1)\n"
    assert extract_code("print(2)") == "print(2)\n"
