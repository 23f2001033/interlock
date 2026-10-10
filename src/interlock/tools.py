"""Subprocess wrapper. Every external tool call is a neatlogs TOOL span and never raises on failure."""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import neatlogs

# The Entire installer puts `entire` here; processes started before the install don't have it on PATH.
_ENTIRE_DIR = str(Path.home() / ".local" / "bin")
if _ENTIRE_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ENTIRE_DIR + os.pathsep + os.environ.get("PATH", "")

# Interlock's own git operations (temp worktrees, scratch merges) must not trigger repo hooks:
# Entire's commit hooks attribute commits to agent sessions and can block on interactive input.
NO_HOOKS = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": os.devnull}


@dataclass
class Result:
    args: list[str]
    code: int
    out: str
    err: str
    seconds: float

    @property
    def ok(self) -> bool:
        return self.code == 0


def run(
    args: list[str],
    cwd: str | Path | None = None,
    timeout: float = 300,
    tool: str | None = None,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> Result:
    name = tool or Path(args[0]).stem
    attrs = {"interlock.cmd": " ".join(str(a) for a in args)[:500], "interlock.cwd": str(cwd or "")}
    with neatlogs.trace(f"tool.{name}", kind="TOOL", **attrs) as span:
        start = time.time()
        try:
            p = subprocess.run(
                [str(a) for a in args],
                cwd=cwd,
                input=stdin if stdin is not None else "",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env={**os.environ, **(env or {})},
            )
            res = Result(list(args), p.returncode, p.stdout, p.stderr, time.time() - start)
        except subprocess.TimeoutExpired:
            res = Result(list(args), 124, "", f"timed out after {timeout}s", time.time() - start)
        except FileNotFoundError as e:
            res = Result(list(args), 127, "", str(e), time.time() - start)
        span.set_attribute("interlock.exit_code", res.code)
        span.set_attribute("interlock.seconds", round(res.seconds, 3))
        if not res.ok:
            span.set_attribute("interlock.stderr_tail", (res.err or res.out)[-1000:])
        return res
