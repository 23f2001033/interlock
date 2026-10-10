"""Interlock command line."""

import json
from pathlib import Path

import typer
from dotenv import load_dotenv

app = typer.Typer(add_completion=False, help="Land AI-written changes safely: prove 'passes alone, fails together'.")

ICON = {"interference": "✗ INTERFERENCE", "holds": "✓ intent holds", "inconclusive": "? inconclusive"}


@app.command()
def prove(
    x: str = typer.Argument(..., help="First branch/ref"),
    y: str = typer.Argument(..., help="Second branch/ref"),
    repo: Path = typer.Option(Path("."), help="Target git repository"),
    merged: str = typer.Option(None, help="An existing merge/resolution of X and Y to check (default: merge them)"),
    budget: float = typer.Option(1.0, help="Max LLM spend for this run, USD"),
    state_dir: Path = typer.Option(Path(".interlock"), help="Where runs, cache and worktrees live"),
):
    """Check whether X and Y interfere, in both directions, with a test that passes alone and fails together."""
    load_dotenv()
    from interlock.prover import prove as run_prove
    from interlock.tracing import init_tracing

    init_tracing(tags=["prove"])
    r = run_prove(repo.resolve(), x, y, state_dir.resolve(), merged=merged, budget_usd=budget)

    typer.echo(f"\nInterlock run {r.run_id}: {x} × {y} (base {r.base})")
    typer.echo(f"  merge: {r.resolution}" + (f" (conflicts in {', '.join(r.conflicted_files)})" if r.conflicted_files else ""))
    typer.echo(f"  overlapping entities: {', '.join(r.overlap) or 'none'}")
    for name, info in r.intents.items():
        s = info.get("sessions", [])
        who = ", ".join(f"{x['agent']} session {x['session_id'][:8]} (checkpoint {x['checkpoint_id']})" for x in s) or "human"
        typer.echo(f"  intent of {name}: {who}")
    e = r.existing_tests_on_merge
    typer.echo(f"  existing tests on merge: {e.get('passed', 0)} passed, {len(e.get('failed', []))} failed")
    for d in r.directions:
        typer.echo(f"  {ICON[d.verdict]}: intent of {d.intent_of} vs {d.against} "
                   f"(own branch {d.on_own_branch or '-'}, base {d.on_base or '-'}, merge {d.on_merge or '-'}, repairs {d.repairs})")
        if d.verdict == "interference":
            lines = [ln for ln in d.failure.splitlines() if ln.startswith(("E ", "FAILED", "AssertionError"))]
            for ln in lines[:4]:
                typer.echo(f"      {ln.strip()}")
    typer.echo(f"  LLM: {r.llm_calls} calls, {r.llm_cache_hits} cached, ${r.cost_usd:.4f} · {r.seconds}s")
    typer.echo(f"  report: {state_dir / 'runs' / r.run_id / 'report.json'}")


@app.command()
def resolve(
    x: str = typer.Argument(..., help="First branch"),
    y: str = typer.Argument(..., help="Second branch"),
    repo: Path = typer.Option(Path("."), help="Target git repository"),
    rounds: int = typer.Option(3, help="Max fix rounds before escalating"),
    budget: float = typer.Option(1.0, help="Max LLM spend for this run, USD"),
    resume: str = typer.Option(None, help="Resume an earlier run id"),
    state_dir: Path = typer.Option(Path(".interlock"), help="Where runs, cache and worktrees live"),
):
    """Prove interference, then coordinate the responsible agent until both intents hold (or escalate)."""
    load_dotenv()
    from interlock.coordinator import resolve as run_resolve
    from interlock.tracing import init_tracing

    init_tracing(tags=["resolve"])
    st = run_resolve(repo.resolve(), x, y, state_dir.resolve(), rounds=rounds, budget_usd=budget, resume=resume)
    typer.echo(f"\nInterlock run {st['run_id']}: {x} × {y} -> {st['status'].upper()}")
    if st.get("adapts"):
        typer.echo(f"  adapts: {st['adapts']} ({st.get('reason', '')})")
    for r in st.get("rounds", []):
        state = "resolved" if r["intent_tests_ok"] and r["suite_ok"] else f"still failing: {', '.join(r['failed'][:4])}"
        typer.echo(f"  round {r['round']}: head {r['head']} -> {state}")
    typer.echo(f"  Interlock LLM cost: ${st.get('llm_cost_usd', 0):.4f}")
    typer.echo(f"  state: {state_dir / 'runs' / st['run_id'] / 'state.json'}")


@app.command()
def land(
    branches: list[str] = typer.Argument(..., help="Branches to land"),
    into: str = typer.Option("main", help="Target branch"),
    repo: Path = typer.Option(Path("."), help="Target git repository"),
    rounds: int = typer.Option(3, help="Max fix rounds per branch before escalating"),
    budget: float = typer.Option(2.0, help="Max LLM spend per proof/coordination, USD"),
    keep_order: bool = typer.Option(False, help="Land in the given order instead of providers-first"),
    state_dir: Path = typer.Option(Path(".interlock"), help="Where runs, cache and worktrees live"),
):
    """Goal mode: land all branches onto the target, proving each integration and coordinating agents."""
    load_dotenv()
    from interlock.lander import land as run_land
    from interlock.tracing import init_tracing

    init_tracing(tags=["land"])
    st = run_land(repo.resolve(), branches, into, state_dir.resolve(), rounds=rounds, budget_usd=budget,
                  keep_order=keep_order)
    typer.echo(f"\nInterlock {st['run_id']}: goal '{st['goal']}' -> {st['status'].upper()} in {st['seconds']}s")
    for e in st["events"]:
        info = {k: v for k, v in e.items() if k not in ("at", "event")}
        typer.echo(f"  {e['at']} {e['event']:<10} {json.dumps(info)[:220]}")
    typer.echo(f"  state: {state_dir / 'runs' / st['run_id'] / 'state.json'}")


@app.command(name="eval")
def eval_cmd(
    mode: str = typer.Option("v2", help="v1 = merge queue baseline, v2 = Interlock"),
    suite: Path = typer.Option(Path("eval/scenarios.json"), help="Labelled scenario file"),
    repo: Path = typer.Option(Path("."), help="Target git repository"),
    fresh: bool = typer.Option(True, help="Bypass the cache for test synthesis (honest cost numbers)"),
    label: str = typer.Option("", help="Version label for this run, e.g. v2.1 (tagged in neatlogs)"),
    state_dir: Path = typer.Option(Path(".interlock"), help="Where runs, cache and worktrees live"),
):
    """Score v1 (merge queue) or v2 (Interlock) on labelled branch pairs."""
    load_dotenv()
    from interlock.evaluate import evaluate
    from interlock.tracing import init_tracing

    init_tracing(tags=["eval", mode] + ([label] if label else []))
    out = evaluate(repo.resolve(), suite.resolve(), mode, state_dir.resolve(), fresh=fresh, label=label)
    m = out["metrics"]
    typer.echo(f"\n{mode}: recall {m['recall']} precision {m['precision']} (tp {m['tp']} fn {m['fn']} fp {m['fp']} tn {m['tn']})"
               f" cost ${m['cost_usd']} time {m['seconds']}s")
    for r in out["rows"]:
        mark = "ok " if r["correct"] else "BAD"
        typer.echo(f"  [{mark}] {r['name']:<22} truth={r['truth']:<12} flagged={str(r['flagged']):<5} "
                   f"${r.get('cost_usd', 0):.4f} {r['seconds']}s {r.get('evidence', '')[:90]}")


@app.command()
def version():
    """Print the version."""
    typer.echo("interlock 0.1.0")


def main():
    app()
