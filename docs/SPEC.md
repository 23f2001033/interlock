# Interlock: Design Spec

## 1. Problem

Code review is per-PR; breakage between AI-written changes is cross-PR.

- **Parallel agents.** Two coding agents branch from the same `main`. Agent X builds a feature on top of `Cart.subtotal()`, while agent Y changes what `Cart.subtotal()` returns. Each branch's tests pass and git merges them with no conflict markers, but X's feature is broken on the merged code.
- **Stale base.** A background agent works while humans and other agents keep merging to `main`. Its change was right for the `main` it started from and wrong for the `main` it lands on.

Reference: "Passes Alone, Fails Together: Benchmarking Semantic Coordination in Parallel LLM-Agent Development" (arXiv 2609.25396). It found interference in 97% of constructed runs, and **a message describing the concurrent change recovered 82%** of them.

## 2. Definitions

- **Change set**: a branch (or PR head) relative to its merge base with the target branch. `main` commits that landed after another change set's base also form a change set (drift).
- **Intent of X**: what X's author was asked to do. Recovered from Entire: `entire why FILE:LINE --json` → checkpoint/prompt/session, then `entire checkpoint explain <id> --json`. Lines with no checkpoint are attributed to a human.
- **Interference of Y on X**: behavior that X intends, and that holds on X alone, no longer holds on `merge(X, Y)`.
- **Proof**: a test `T_X` that **passes on X** and **fails on merge(X, Y)**. This is "passes alone, fails together". Because the only difference between X and merge(X, Y) is Y's change, the failure is attributed to Y.
  - *Existing-test proof*: a test from X's own suite that passes on X and fails on the merge.
  - *Synthesized proof*: when the existing tests all pass on the merge, Interlock writes `T_X` from X's intent and diff. To be accepted, `T_X` must pass on X (repair up to 2 times otherwise), should fail on X's merge base (shows it exercises X's change), and then fail on the merge.
- **Textual conflict**: `git merge-tree --write-tree X Y` reports conflicts. No proof is needed. Handled by a rebase request.

## 3. Pipeline (goal mode)

`interlock land --repo R --base main --branches A B C [--watch-main]`

1. **Plan.** For each change set: `entire graph diff --base <merge-base> --head <branch>` gives entity-level changes (fallback: `git diff` plus Python `ast`). Then compute dependencies: for each entity E changed by Y, `entire graph impact --repo <wt> --symbol E` gives E's callers and dependents. A pair (X, Y) is a **candidate** if X adds or changes code that calls or depends on an entity Y changes, or both change the same entity. Output: a candidate list ranked by risk, a merge order (providers before consumers), and a budget per pair. Pairs with no dependency are cleared without any LLM call.
2. **Textual check** on each pair with `git merge-tree --write-tree`.
3. **Intent** for each change set (cached per head SHA). A small model summarizes it into: task, entities it meant to change, assumptions.
4. **Prove** each candidate in both directions (T_X against Y, T_Y against X):
   1. Create temp worktrees for X and for merge(X, Y) under `.interlock/worktrees/`.
   2. Run X's tests on both. Any test that passes on X and fails on the merge is a proof.
   3. Otherwise synthesize `T_X`. Context: X's intent, X's diff, Y's diff (just the changed entities), and declarations and impact slices from `entire graph def/impact`, capped by bytes. Write it to `tests/test_interlock_<pair>.py` and validate as in §2.
5. **Decide who adapts.** If Y's change to entity E is *not* in Y's intent (an accidental behavior change), Y adapts (revert or compatibility shim). Otherwise X, the consumer, adapts to Y. Stretch: check Entire Brain for a recorded decision about E.
6. **Coordinate.** Write the fix request: which entity changed, from what to what (before/after), where X depends on it (file:line), the proof test (content and command), and the acceptance criteria (the proof test passes on the merge, and the branch's own tests pass). Deliver it through an adapter:
   1. `claude -p --resume <session_id>` run in that branch's worktree (the agent keeps its full original context);
   2. a fresh `claude -p` with the original prompt and transcript summary as context;
   3. `ao send <session>` (Orchestrator);
   4. a PR comment for human authors.
7. **Re-verify** after the agent commits: re-run the proof on the new heads. Up to 3 rounds, then escalate with an evidence pack.
8. **Land** in dependency order. After each merge, re-check the remaining pairs against the new `main`.
9. **Drift.** If `main` moves during the run, the new commits become change set M. Invalidate only the proofs whose entities M touches, and re-plan.
10. **Finish.** Run the full test suite on final `main`. Write `.interlock/reports/<run>.md` and the neatlogs trace links. Stretch: `entire brain remember` each resolution.

## 4. State: ledger

Per-run state file `.interlock/runs/<run>/state.json` (prove report, decision, rounds, steps); planned SQLite ledger for goal mode. Tables (planned): `runs`, `change_sets` (branch, head sha, base sha, intent json), `pairs` (status: candidate|cleared|textual|proven|resolved|escalated), `proofs` (test path and content, results on X/base/merge), `rounds`, `messages`, `llm_calls` (model, tokens, cost, cache hit).

Every step is keyed by (run, pair, head SHAs) and is idempotent, so `interlock land --resume <run>` continues after a crash.

## 5. Models and budget governor

| Tier | Model | Used for |
|---|---|---|
| small | `nova-lite` / `nova-micro` | Intent summaries, message drafting |
| mid | `claude-haiku` / `nova-pro` | Test repair, who-adapts reasoning |
| strong | `claude-sonnet-4.6` | Test synthesis, only after existing tests found no proof |

- Content-hash response cache in `.interlock/cache/`, so dev reruns cost $0.
- Per-call cost comes from usage × a price table (or LiteLLM's cost header if present).
- Caps: per-pair (default $0.25) and per-run. At 80% of the team budget, switch to deterministic-only mode (existing tests + graph) and say so in the report.

## 6. Tracing (neatlogs)

- `neatlogs.init(workflow_name="interlock", instrumentations=["openai"], tags=[...])`, with `flush()`/`shutdown()` on exit.
- Spans:
  - `WORKFLOW`: `land`
  - `AGENT`: `planner`, `prover`, `coordinator`, `lander`
  - `TOOL`: every subprocess (`git`, `entire`, `pytest`, `claude`, `gh`, `ao`)
  - `CHAIN`: per pair
- Attributes: `interlock.run`, `interlock.pair`, `interlock.branch`, `interlock.session`, `interlock.phase` (plan|intent|prove|coordinate|verify|land|drift), `interlock.focus_area` (planning|tool_use|state|context|execution|recovery|verification|iteration), `interlock.cost_usd`.
- Detections to configure in neatlogs: discarded tests, pair cost over cap, escalations, re-proof failures, budget over 80%.

## 7. CLI

- `interlock prove --repo R --base main X Y`: one pair, both directions
- `interlock land --repo R --base main --branches A B C [--watch-main] [--resume RUN]`
- `interlock status [RUN]`
- `interlock report RUN`
- `interlock eval --suite eval/scenarios.yaml --mode v1|v2` → `eval/results/<mode>.json` (recall, precision, resolution rate, rounds, time-to-proof, $/pair, tokens/pair)
  - **v1 baseline:** merge plus existing tests only (what a merge queue does)
  - **v2:** full Interlock

## 8. Evaluation evidence

Keep `EVIDENCE.md` with:
- before/after runs (neatlogs links and the compared numbers);
- a recovered failure;
- Entire checkpoints and graph output;
- the business plan link;
- #neatHack post links.
