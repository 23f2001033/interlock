"""Evaluation: a plain merge queue (v1) vs Interlock (v2) on labelled branch pairs.

v1 (what a merge queue does): merge the pair (the same automated resolver handles textual conflicts,
so both modes see identical merged code), run the existing test suite, flag the pair if anything fails.
v2 (Interlock): prove "passes alone, fails together" in both directions with intent tests.

Ground-truth labels and their reasoning live in the suite file; they are a human judgement, stated openly.
"""

import json
import time
from dataclasses import asdict
from pathlib import Path

import neatlogs

from interlock import gitops
from interlock.llm import LLM
from interlock.prover import _resolve_conflicts, prove
from interlock.testrun import pytest


def _v1(repo: Path, x: str, y: str, state_dir: Path, wt_path: Path) -> dict:
    llm = LLM(state_dir, budget_usd=1.0)
    wt = gitops.add_worktree(repo, wt_path, gitops.rev(repo, x))
    try:
        conflicts = gitops.merge(wt, y)
        if conflicts:
            _resolve_conflicts(llm, wt, conflicts)
        run = pytest(wt)
        return {"flagged": not run.ok, "conflicts": conflicts, "failed_tests": run.failed[:10],
                "cost_usd": round(llm.spent_usd, 6), "evidence": "existing test failures" if run.failed else ""}
    finally:
        gitops.remove_worktree(repo, wt)


def evaluate(repo: Path, suite_path: Path, mode: str, state_dir: Path, fresh: bool = True) -> dict:
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    rows = []
    with neatlogs.trace(f"interlock.eval.{mode}", kind="WORKFLOW", **{"interlock.mode": mode}) as root:
        for sc in suite["scenarios"]:
            with neatlogs.trace(f"eval.{sc['name']}", kind="CHAIN", **{"interlock.truth": sc["truth"]}) as span:
                t0 = time.time()
                if mode == "v1":
                    r = _v1(repo, sc["x"], sc["y"], state_dir,
                            state_dir / "worktrees" / f"eval-{mode}" / sc["name"])
                else:
                    rep = asdict(prove(repo, sc["x"], sc["y"], state_dir, budget_usd=1.0, fresh=fresh))
                    verdicts = [d["verdict"] for d in rep["directions"]]
                    r = {"flagged": "interference" in verdicts, "verdicts": verdicts,
                         "conflicts": rep["conflicted_files"], "overlap": rep["overlap"], "cost_usd": rep["cost_usd"],
                         "tokens_in": rep["tokens_in"], "run": rep["run_id"],
                         "evidence": "; ".join(f"intent of {d['intent_of']}: passes alone, fails together"
                                               for d in rep["directions"] if d["verdict"] == "interference")}
                r.update(name=sc["name"], truth=sc["truth"], seconds=round(time.time() - t0, 1))
                r["correct"] = r["flagged"] == (sc["truth"] == "interference")
                span.set_attribute("interlock.flagged", r["flagged"])
                rows.append(r)

        tp = sum(r["flagged"] and r["truth"] == "interference" for r in rows)
        fn = sum(not r["flagged"] and r["truth"] == "interference" for r in rows)
        fp = sum(r["flagged"] and r["truth"] == "benign" for r in rows)
        tn = sum(not r["flagged"] and r["truth"] == "benign" for r in rows)
        metrics = {"mode": mode, "pairs": len(rows), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
                   "recall": round(tp / (tp + fn), 3) if tp + fn else None,
                   "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                   "cost_usd": round(sum(r.get("cost_usd", 0) for r in rows), 4),
                   "seconds": round(sum(r["seconds"] for r in rows), 1)}
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                root.set_attribute(f"interlock.{k}", v)
    out = {"metrics": metrics, "rows": rows, "suite": str(suite_path), "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    dest = suite_path.parent / "results"
    dest.mkdir(exist_ok=True)
    (dest / f"{mode}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
