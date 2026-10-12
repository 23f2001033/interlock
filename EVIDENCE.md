# Evidence

Each claim below links to something a judge can check. Run files live in `evidence/runs/`, eval results in `eval/results/`, and the dated build log in `hackathon.md`.

## 1. The agent improved (before → after runs, with the compared numbers)

Same labelled suite each time (`eval/scenarios.json`: 8 pairs of real agent branches, 2 interfering and 6 benign). The cache is bypassed for test synthesis so costs are real. Every run is traced in neatlogs and tagged with its version (`v1`, `v2.0` … `v2.3`). Result files are in `eval/results/`.

| Version | Recall | Precision | False alarms | Cost (8 pairs) | Time |
|---|---|---|---|---|---|
| v1: plain merge queue (merge + existing tests) | 1.00 | 0.40 | 3 / 6 | $0.11 | 61 s |
| v2.0: Interlock | 1.00 | 0.67 | 1 / 6 | $0.52 | 296 s |
| v2.1: + entire-graph pre-check, two-direction overlap | 1.00 | 0.67 | 1 / 6 | **$0.40** (−22%) | 276 s |
| v2.2: + second-opinion confirmation | 1.00 | **1.00** | **0 / 6** | $0.55 | 307 s |
| v2.3: + model ladder (Haiku first, then Sonnet) | **1.00** | **1.00** | **0 / 6** | **$0.38** (−31% vs v2.2) | 367 s |

| Loop | What the traces showed | Fix (code) | Before → after |
|---|---|---|---|
| 1 | Benign pairs that share no code still spent $0.03-0.09 each writing intent tests. The overlap check only looked one way, so `currency × save10` (where `place_order` calls the changed `charge()`) showed no overlap. | `prover._overlap` checks both directions. Pairs with no shared or called entities, no shared files, a clean merge and a green suite are cleared by entire-graph with no model call (`cleared_by_graph` span). | $0.52 → $0.40, 296 s → 276 s. `currency × region` cleared for $0 in 9 s. Charge-related overlap now detected. |
| 2 | The one false alarm (`region × cents`) came from an intent test that hard-coded dollars (`round(order.total * 100)`): a representation clash, not broken behavior. | `prover._confirm`: before reporting interference, re-express the same intent in the merged code's representation. Withdraw the proof only if that test passes on the merge **and** fails on the base (so a vacuous test can't clear a real conflict). | Precision 0.67 → **1.00**. All 4 real findings `confirmed`; the false one became `representation_only`. Cost +$0.15. |
| 3 | `llm.synthesize_test` spans were all Sonnet; most tests are simple. | `prover._ladder`: Claude Haiku first (1 repair), escalating to Sonnet only if needed (`synthesize.<model>` spans, `interlock.escalated_from`). | $0.55 → **$0.38** at the same recall/precision. 12 of 14 intent tests written by Haiku, 2 escalated to Sonnet. Slower (307 s → 367 s): an honest trade-off. |

| 4 | Drift demo #1 escalated after 3 rounds. The `agent_message` spans show agent #1 explaining that an acceptance test hard-coded dollars (`tax == 7.2`) and contradicted its own task (integer cents). | `coordinator.reexpress_acceptance`: when acceptance tests fail, re-express the intent in the new head's representation and accept it only if it passes on the head and fails on the base (`arbitrate.reexpress` span). | Same scenario: **escalated after 3 rounds → resolved in round 1**, goal DONE, 48/48 (`evidence/runs/20261011-031122` → `evidence/runs/20261011-031629`). |

## 2. We used neatlogs

- Every Interlock command initialises neatlogs (`src/interlock/tracing.py`):
  - workflow spans `interlock.prove` / `resolve` / `land` / `eval.*`;
  - agent spans `planner`, `intent`, `resolver`, `prove.<branch>`, `decide`, `agent_message`, `drift`;
  - a TOOL span for every subprocess (`git`, `entire`, `pytest`, `claude`);
  - LLM spans from `neatlogs.wrap(OpenAI(...))`;
  - CHAIN spans `llm.<purpose>` with `interlock.cost_usd`, `interlock.cache_hit` and `interlock.tokens_in`.
- Traces carry tags (`prove`, `resolve`, `land`, `eval`, `v1`/`v2`, version labels) for comparing runs.
- **Server-side proof, pulled through the neatlogs MCP** (`scripts/neatlogs_mcp.py`, no screenshot needed):
  - [evidence/neatlogs/trace_drift_demo.md](evidence/neatlogs/trace_drift_demo.md): the drift-demo trace `01f314416618f766c98ba1f50110a89c` (244 spans, 208 tool calls, success) as a span tree;
  - [evidence/neatlogs/mcp_pull.json](evidence/neatlogs/mcp_pull.json): `search_traces` results for `interlock.land`, `agent_message`, `arbitrate.reexpress`, `interlock.eval` and `cleared_by_graph`.
- **Detections we created in neatlogs** (group "Interlock", [evidence/neatlogs/detections.json](evidence/neatlogs/detections.json)): *fix round failed* (`recover.next_round`), *intent test repaired* (`recover.repair_test`) and *acceptance test arbitrated* (`arbitrate.reexpress`). Each was previewed first and then backfilled; they already fire on the drift-demo trace.
- **Dashboard screenshot:** [evidence/neatlogs/dashboard-traces.png](evidence/neatlogs/dashboard-traces.png): the Traces list with the Interlock detection badges (*acceptance test arbitrated*, *fix round failed*, *intent test repaired*) and a traced coding-agent session ("Reply with exactly: OK").
- **Coding agents traced too:** the neatlogs Claude Code integration is installed in the demo repo (`.claude/settings.json`, with the key kept in the user config, not the repo).

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

- [business-plan/plan.md](business-plan/plan.md) covers pricing ($30/developer), unit economics from the **measured** $0.0474 per checked pair, Base/Growth scenarios, costs and runway (break-even month 7 / 5, lowest cash $29k / $33k).
- The 12-month model is generated from the eval results by `scripts/business_model.py` → [model_summary.md](business-plan/model_summary.md) and [model.csv](business-plan/model.csv). The same drivers are entered into cfo.ai (data-entry sheet in plan.md §6).
- cfo.ai views: `business-plan/cfo-unit-economics.png`, `cfo-scenarios.png`, `cfo-runway.png` *(builder adds)*.

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
| 0 | **Submission post** (tags @neatlogs @EntireHQ @arithecfo) | https://x.com/quantizationer/status/2109709745682870283 |
| 1 | "3 AI agents → 3 green PRs → merged → checkout broken" (X + LinkedIn) | *(add URL)* |
| 2 | The experiment and the bets | *(add URL)* |
| 3 | Result 1: git silently merged dollars into cents (`docs/media/silent_bug.png`) | *(add URL)* |
| 4 | We made the agents talk to each other (`docs/media/agents_talk.png`) | *(add URL)* |
| 5 | The agent said no, and it was right (`docs/media/agent_said_no.png`) | *(add URL)* |
| 6 | Scoreboard: merge queue vs Interlock (`docs/media/scoreboard.png`) | *(add URL)* |
| 7 | Landing while a teammate pushes (`docs/media/drift_timeline.png`) | *(add URL)* |

## 7. We wrote the code during the hackathon

- Public repos [interlock](https://github.com/23f2001033/interlock) and [interlock-demo-shop](https://github.com/23f2001033/interlock-demo-shop). The first commit is dated 2026-10-11 00:19 IST, after the 2026-10-10 12:30 IST start.
