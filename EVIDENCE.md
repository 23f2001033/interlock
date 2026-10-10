# Evidence

Each claim below links to something a judge can check. Run files live in `evidence/runs/`, eval results in `eval/results/`, and the dated build log in `hackathon.md`.

## 1. The agent improved (before → after runs, with the compared numbers)

*Filled in by the improvement loops below. Each loop is: find the failure or waste in neatlogs, locate the code, fix it, re-run the same eval, compare.*

| Loop | What the traces showed | Fix | Before → after |
|---|---|---|---|
| 1 | *(pending)* | | |
| 2 | *(pending)* | | |
| 3 | *(pending)* | | |

## 2. We used neatlogs

- Every Interlock command initialises neatlogs (`src/interlock/tracing.py`):
  - workflow spans `interlock.prove` / `resolve` / `land` / `eval.*`;
  - agent spans `planner`, `intent`, `resolver`, `prove.<branch>`, `decide`, `agent_message`, `drift`;
  - a TOOL span for every subprocess (`git`, `entire`, `pytest`, `claude`);
  - LLM spans from `neatlogs.wrap(OpenAI(...))`;
  - CHAIN spans `llm.<purpose>` with `interlock.cost_usd`, `interlock.cache_hit` and `interlock.tokens_in`.
- Traces carry tags (`prove`, `resolve`, `land`, `eval`, `v1`/`v2`, version labels) for comparing runs.
- Screenshots: *(to add: the `interlock.land` trace tree, the agent_message span with the fix request and reply, an eval before/after comparison)*

## 3. We used Entire

- **Checkpoints on agent work:** every agent commit in [interlock-demo-shop](https://github.com/23f2001033/interlock-demo-shop) has an `Entire-Checkpoint` trailer, and the checkpoint refs are pushed (`refs/entire/checkpoints/*`):
  - #1 `01M4KNS0TF70B4VB0GM2B406WN`
  - #2 `01M4KNS1S0ZXHCS4VV4EBT8BZE`
  - #3 `01M4KNS2VKRRSM71AKT5VY8X9E`
  - #2's coordinated merge `01M4KPZYFV1T68YZETD7XJ897W`
- **`entire why --json` inside Interlock:** returns `authorship: ai`, checkpoint, session, model and the agent's original prompt for any changed line. It is shown in every `report.json` under `intents`.
- **entire-graph inside Interlock:**
  - `graph diff --json` for planning and drift;
  - `graph impact --format json` for overlap and "new code depends on what this branch changes".
  - The overlap found for issue-2 × issue-1 (`Cart.subtotal, price_of, quote, round_money, shipping_for, tax_for`) is in `evidence/runs/20261011-013325/report.json`.
- **`entire session attach`:** Interlock links each coordinated commit back to the agent session that made it.

## 4. We used cfo.ai

- `business-plan/plan.md` covers pricing, costs (measured cost per proof), revenue scenarios and runway. The cfo.ai model exports and screenshots will sit next to it. *(cfo.ai model: pending, builder)*

## 5. The agent recovers from failures

- **Failed actions handled in real runs:**
  - two of the first fleet's agent commits hung inside Entire's hook → committed with hooks off, then linked with `entire session attach` (`hackathon.md`, 2026-10-11 00:55);
  - automated conflict resolution broke a merge (`NameError`) → proven and handed back to the responsible agent, then fixed in round 1 (`evidence/runs/20261011-013837/state.json`).
- **Mechanisms in code:**
  - test repair loop (`recover.repair_test`);
  - next fix round with the failure output (`recover.next_round`);
  - compare-and-swap retry on a concurrent push, plus drift re-plan (`lander.py`);
  - budget cap → `BudgetExceeded` → inconclusive instead of a crash;
  - escalation after N rounds.

## 6. We built in public

| # | Post | Link |
|---|---|---|
| 1 | "3 AI agents → 3 green PRs → merged → checkout broken" (X + LinkedIn) | *(add URL)* |
| 2 | The bets / poll | *(add URL)* |

## 7. We wrote the code during the hackathon

- Public repos [interlock](https://github.com/23f2001033/interlock) and [interlock-demo-shop](https://github.com/23f2001033/interlock-demo-shop). The first commit is dated 2026-10-11 00:17 IST, after the 2026-10-10 12:30 IST start.
