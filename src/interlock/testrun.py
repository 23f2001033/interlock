"""Run the target repo's pytest suite in a worktree and parse per-test outcomes from JUnit XML."""

import os
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from interlock.tools import run


@dataclass
class TestRun:
    outcomes: dict[str, str] = field(default_factory=dict)  # test id -> passed|failed|error|skipped
    output: str = ""
    collected: bool = True

    @property
    def failed(self) -> list[str]:
        return [t for t, o in self.outcomes.items() if o in ("failed", "error")]

    @property
    def ok(self) -> bool:
        return self.collected and not self.failed and bool(self.outcomes)


def pytest(wt: Path, *paths: str, timeout: float = 300) -> TestRun:
    fd, name = tempfile.mkstemp(suffix=".xml", prefix="interlock-")
    os.close(fd)
    junit = Path(name)
    r = run(["uv", "run", "--quiet", "pytest", "-q", "-p", "no:cacheprovider",
             f"--junitxml={junit}", *paths], cwd=wt, tool="pytest", timeout=timeout)
    result = TestRun(output=(r.out + r.err)[-4000:])
    try:
        root = ET.parse(junit).getroot()
    except (ET.ParseError, FileNotFoundError):
        result.collected = False
        return result
    finally:
        junit.unlink(missing_ok=True)
    for case in root.iter("testcase"):
        tid = f"{case.get('classname')}::{case.get('name')}"
        if case.find("failure") is not None:
            result.outcomes[tid] = "failed"
        elif case.find("error") is not None:
            result.outcomes[tid] = "error"
        elif case.find("skipped") is not None:
            result.outcomes[tid] = "skipped"
        else:
            result.outcomes[tid] = "passed"
    if not result.outcomes and r.code not in (0, 5):
        result.collected = False
    return result
