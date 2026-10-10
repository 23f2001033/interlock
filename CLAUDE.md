# Interlock

Interlock is an agent that takes a goal like "land these AI-written branches/PRs on `main`" and finishes only when every change is merged **and** the combined code is proven consistent. It finds changes that pass alone but fail together, proves each with a test, sends the responsible coding agent the exact fix request, and re-verifies, even while `main` keeps moving.

Design: [docs/SPEC.md](docs/SPEC.md). Demo environment and scenario: `../interlock-demo-shop` and [docs/DEMO_SCENARIO.md](docs/DEMO_SCENARIO.md). Build log: [hackathon.md](hackathon.md) (keep it updated with the `neathack` skill).

## Ground rules

- **Never read, print, paste or commit `.env`** (API keys). Load it with `python-dotenv`. Don't echo env values in commands or logs.
- **Trace everything with neatlogs**, and make every LLM call go through the budget governor (the shared LiteLLM key has a hard $20 cap).
- **Commit small and often.** Each commit made in this session carries an Entire checkpoint, and those checkpoints are evidence.
- Navigate code with `entire graph search|def|impact` and use `entire why FILE:LINE` to understand past changes before editing.
- Never fabricate results. Record only the tests and runs that actually happened. After each work session, add a dated entry to `hackathon.md` (planned vs completed).
- Windows + Git Bash: shell out with argument lists (no shell strings). Paths can contain spaces.

## Stack

- Python 3.11+, `uv`, `typer` (CLI), `openai` SDK pointed at the LiteLLM proxy, `neatlogs[openai]`, `python-dotenv`, stdlib `sqlite3`, `pytest`.
- Env vars: `NEATLOGS_API_KEY` (also accept the legacy name `NEATLOG_API_KEY`), `LITELLM_API_KEY`, `LITELLM_BASE_URL` (default `https://litellm.vision.aivar.app/v1`), `CRUSTDATA_API_KEY`.
- LiteLLM model names: `nova-micro`, `nova-lite`, `nova-pro`, `nova-2-lite`, `claude-haiku`, `claude-sonnet-4.6`, `claude-opus-4.6`.
- External tools called through subprocess (each call is a neatlogs TOOL span): `git`, `gh`, `entire`, `uv run pytest`, `claude` (headless, `-p`), optionally `ao`.

## Milestones

| Level | Done when |
|---|---|
| **L0 Prover** | `uv run interlock prove --repo ../interlock-demo-shop --base main <branchX> <branchY>` finds candidate entities with `entire graph`, runs existing tests on X, Y and merge(X,Y), synthesizes an intent test when needed, and reports a **proof**: a test that passes on X and fails on merge(X,Y). Fully traced in neatlogs. |
| **L1 Closed loop** | Intent from `entire why`/`checkpoint explain`; decides who adapts; sends the fix request to the responsible agent (headless `claude -p --resume <session>` in that branch's worktree, falling back to a fresh `claude -p` with context); re-proves after the agent commits; the SQLite ledger resumes after a crash. |
| **L2 Goal mode** | `uv run interlock land --repo ... --base main --branches A B C` plans pairs and merge order, handles textual conflicts (rebase request), lands in dependency order, detects `main` moving mid-run (drift) and re-plans only the affected pairs, runs the final suite, writes a report. `interlock eval` produces v1-vs-v2 metrics. |
| L3 (stretch) | Orchestrator `ao send` adapter, PR comments via `gh`, a public status page, Brain-grounded arbitration. |

## Conventions

- Package layout: `src/interlock/` (`cli.py`, `planner.py`, `graph.py`, `intent.py`, `prover.py`, `coordinator.py`, `lander.py`, `ledger.py`, `llm.py`, `tracing.py`, `tools.py`). Tests in `tests/`.
- Every subprocess wrapper returns structured results (exit code, stdout, stderr, duration) and never raises on non-zero exit. The caller decides.
- Temporary worktrees go under `.interlock/worktrees/` (gitignored). Always clean up, even on failure.
- Prompts live in `src/interlock/prompts/` as plain-text templates (versioned, so before/after runs can be compared).
