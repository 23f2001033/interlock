# neatHack Build Log

Maintained per the official neatHack skill (`.claude/skills/neathack/SKILL.md`). Entries are dated (IST). "Planned" and "Completed" are kept separate. No results are recorded unless they actually happened.

## Project

- **Name:** Interlock
- **Purpose:** An agent that takes a goal like "land these AI-written branches on main" and finishes only when every change is merged **and** the combined code is proven consistent.
- **Problem:** Code review checks one PR at a time, but AI coding agents now break each other *across* PRs. Parallel agents (or a background agent working against a `main` that has since moved) produce changes that pass alone but fail together. Git reports no conflict, CI stays green, and the bug ships.

## Team

- Team "Embedding" (solo). Published names/handles: pending, builder to confirm.

## Stack

Status of each item:
- **Entire CLI** 0.11.4 + entire-graph plugin 0.4.0: installed (Windows). Enabled for Claude Code in both repos.
- **neatlogs:** project key available. SDK not integrated yet.
- **LiteLLM key** (Nova + Claude, $20 shared): claim pending.
- **cfo.ai:** signup pending.
- **Crustdata:** key available, not used yet.
- **Orchestrator.inc (`ao`):** stretch (needs WSL + tmux).
- **AWS:** optional host. The team has its own credits; the hackathon allowance is pending.

## Build log

### 2026-10-09: Planning (completed, no code)
- Read the hackathon page, FAQ, Luma page and the official skill. Drafted an approval rubric.
- Researched recent agent-hackathon winners. Evaluated ideas. Rejected "Agent Medic" (overlaps neatlogs triage and Arize's cost agent). Chose Interlock.

### 2026-10-10: Planning update (completed, no code)
- Re-read the updated page:
  - models come only through a $20 shared LiteLLM key;
  - Bedrock is not in the $25 AWS allowance;
  - AWS credits go to the first 350 teams;
  - the final submission cutoff will be announced on Discord.
- Checked the Entire docs:
  - `entire review` is single-branch and LLM-only;
  - Brain stores decisions but doesn't enforce them;
  - `entire graph diff/impact/verify/explain`, `entire why --json` and `entire checkpoint explain --json` exist.

### 2026-10-11 00:10-00:30: Setup (completed)
- Web check-in done (team "Embedding", solo).
- Installed the Entire CLI 0.11.4 (official Windows installer) and the entire-graph plugin 0.4.0. `entire graph capabilities` lists Python, and `entire graph def` / `impact` work on the demo code (e.g. the impact of `price_of` = 2 direct and 8 transitive callers).
- Created two local git repos: `interlock` (this agent) and `interlock-demo-shop` (the demo environment). Ran `entire enable --agent claude-code` in both: 9 Claude Code hooks plus git hooks installed. Past session history was **not** imported.
- `.env` is gitignored, and `.env.example` lists the variable names only. Commits use the GitHub noreply email. Line endings normalized to LF.
- Wrote the demo shop baseline (catalog, cart, pricing, payments, orders, receipts) with 16 tests. **Tests run: `uv run pytest -q` → 16 passed.** Committed locally (2 commits).
- Wrote `CLAUDE.md`, `docs/SPEC.md`, `docs/DEMO_SCENARIO.md` and three neutral issue texts for the agent fleet.
- Known issue found: Entire's hooks skip silently when `entire` isn't on PATH, and the editor started before the installer updated PATH. **Fix: fully restart VS Code before any captured session.**

### 2026-10-11 ~00:40: Building in public (completed)
- Post #1 published with #neatHack on X (@quantizationer) and LinkedIn: the problem hook ("3 AI agents → 3 green PRs → merged → CI still green → checkout broken"). Post URLs: pending, builder to add.

### 2026-10-11 00:55-01:35: Experiment run #1, the agent fleet (completed)
- Ran 3 headless Claude Code agents (`scripts/fleet.sh`) on issues #1 (integer cents), #2 (small-order fee) and #3 (SAVE10), each in its own worktree branched from the same commit (`7950d86`).
- **Failure and recovery:**
  - Launching 3 sessions at the same instant made 2 of them exit with code 127. They were relaunched staggered by 20 s.
  - Agents #2 and #3 then finished their code, but `git commit` hung inside Entire's `prepare-commit-msg` hook. Diagnosis: several concurrent sessions were active on the same base commit, and the hook waited for interactive input.
  - Fix: committed their staged work with hooks disabled, then linked each commit to the agent session that wrote it with `entire session attach <session-id> --force`. Checkpoints: #1 `01M4KNS0TF70B4VB0GM2B406WN`, #2 `01M4KNS1S0ZXHCS4VV4EBT8BZE`, #3 `01M4KNS2VKRRSM71AKT5VY8X9E`.
- **Tests run:** each branch passes its own suite: #1 21 passed, #2 19 passed, #3 26 passed. The agents reported equivalent costs of $0.79, $0.47 and $0.69.
- **Verified:** `entire why shop/pricing.py:16 --json` on branch #2 returns authorship `ai`, the checkpoint, the session id, the model and the agent's original prompt.
- **Result:**
  - `git merge-tree` reports textual conflicts for all 3 pairs, because all 3 agents rewrote `quote()`.
  - In the #1 + #2 merge, git **auto-merged without any conflict** `SMALL_ORDER_FEE = 1.50` and `SMALL_ORDER_THRESHOLD = 15.00` (dollars) next to #1's `FREE_SHIPPING_THRESHOLD = 5000` (cents). That is a silent unit mismatch which survives a textual resolution. This is the kind of interference Interlock must prove.

### 2026-10-11 01:30-01:45: L0 Prover works on real agent branches (completed)
- Built `interlock prove X Y`:
  - `tools.py`: traced subprocess wrapper;
  - `gitops.py`: temp worktrees and merges with repo hooks disabled;
  - `entire.py`: `entire graph diff/impact` plus `entire why` intent;
  - `testrun.py`: pytest + JUnit parsing;
  - `llm.py`: LiteLLM via `neatlogs.wrap`, response cache, budget cap, cost from the `x-litellm-response-cost` header;
  - `prover.py`: the "passes alone, fails together" oracle, both directions, with test repair;
  - `cli.py`.
- Bugs hit and fixed during the first runs:
  - `entire graph impact` can return `entries: null`;
  - Windows held the `mkstemp` temp file open, so it is now closed before pytest writes to it.
- **Run `20261011-013325`, agent/issue-2 × agent/issue-1** (evidence in `evidence/runs/20261011-013325/`):
  - Both branches have textual conflicts (`shop/pricing.py`, `tests/test_pricing.py`), resolved by an automated LLM resolver to simulate common practice.
  - Overlapping entities via entire-graph: `Cart.subtotal`, `price_of`, `quote`, `round_money`, `shipping_for`, `tax_for`.
  - Intents recovered from Entire: sessions `b5459f40` and `38dab3b0`, with their checkpoints and original prompts.
  - Existing tests on the merge: 15 passed, 9 failed.
  - **Both directions proven as interference.** The synthesized intent tests pass on their own branch, fail on the base and fail on the merge. Root error: `NameError: name 'round_money' is not defined`. The resolver kept #2's fee code, which calls `round_money`, but lost the import that #1 had removed.
  - Cost: $0.0623, 47 s.

### 2026-10-11 01:45-02:00: L1 closed loop resolves a real interference (completed)
- Built `interlock resolve X Y` (`coordinator.py`). The loop:
  1. prove;
  2. decide who adapts (`claude-haiku`);
  3. summarize the other side's change (`nova-lite`);
  4. write a fix request with both intent tests attached;
  5. **resume the responsible agent's own Claude Code session**, whose id comes from `entire why`, in that branch's worktree;
  6. link the agent's new commit to its session (`entire session attach`);
  7. re-verify on the new head with the saved intent tests plus the full suite, never trusting the agent's claim;
  8. go to the next round with the failure output, up to N rounds, then escalate.

  Run state is saved after every step (`state.json`), and `--resume` continues a run.
- **Run `20261011-013837`, agent/issue-2 × agent/issue-1 → RESOLVED in 1 round** (evidence: `evidence/runs/20261011-013837/state.json`, which contains the full message and reply):
  - Interference proven in both directions, re-using the cached LLM results ($0).
  - Decision: agent/issue-2 adapts. Reason: #1 changed the money contract to integer cents on purpose, and #2 built on the old float contract.
  - The fix request went to session `b5459f40` (the agent that wrote the fee). That agent merged `agent/issue-1`, moved the fee to cents (150 cents under 1500 cents) and committed `5418237`. Its Entire checkpoint is `01M4KPZYFV1T68YZETD7XJ897W`.
  - **Tests run (by Interlock on the new head):** intent tests passed and the full suite passed (30 tests).
  - The agent also reported a remaining cross-feature gap: `Order`/receipt has no `fee` line, so the receipt lines add up to $1.50 less than the total.
  - Interlock's own LLM cost was $0.0011. The agent reported an equivalent cost of $0.85. 01:39:02 → 01:40:24.
- Pushed `agent/issue-1..3` and **4 Entire checkpoint refs** to `github.com/23f2001033/interlock-demo-shop`.

### 2026-10-11 02:00-02:45: L2 goal mode lands all three agent branches (completed)
- Built `interlock land B1 B2 ... --into T` (`lander.py`):
  1. plan a landing order from entire-graph dependents (providers first);
  2. for each branch, check whether it is already integrated, then prove it against the current target;
  3. coordinate the branch's agent when there is interference or a textual conflict;
  4. land by merging in a scratch worktree, running the full suite, then **compare-and-swapping** the target ref;
  5. on drift (someone else moved the target), find the remaining branches whose entities the new commits touch and re-check only those;
  6. run the final suite.

  `scripts/teammate_push.sh` simulates a human teammate pushing to the target mid-run.
- **Run `land-20261011-023216` → DONE in ~4 min** (evidence: `evidence/runs/land-20261011-023216/`, `evidence/runs/20261011-023314/`):
  - Plan: issue-2 → issue-1 → issue-3. issue-2 landed by fast-forward (30 tests). issue-1 was proven to hold against the target and landed (32 tests, now including the teammate's banner tests).
  - issue-3 against the target: **interference in both directions**, plus textual conflicts in 3 files. Interlock resumed agent #3's own session `6114927c`; the agent merged the target and adapted SAVE10 to cents in 1 round (26 turns). Interlock re-verified and landed it.
  - **Final suite: 48 passed, 0 failed.**
- **Bugs found by this run, then fixed:**
  1. A branch already contained in the target (issue-1 inside issue-2) was re-proved instead of skipped. Added an `already_integrated` check.
  2. **Drift went undetected.** The teammate pushed *while* issue-1 was being proven, and `_land_one` re-read the target at landing time instead of compare-and-swapping against the commit the proof had verified. Fixed: landing now CASes from the verified commit, so a concurrent push fails the swap, is recorded as drift, and triggers a re-check if the branch is affected.
- Added unit tests for Interlock itself (`tests/test_core.py`): diff-line parsing, owner worktree lookup, compare-and-swap against a concurrent push, conflict detection, code extraction. **Tests run: 5 passed.**
- Added `interlock eval` (v1 merge-queue baseline vs v2 Interlock on labelled pairs, with an honest-cost mode that bypasses the cache) and `scripts/market_size.py` (Crustdata). **Crustdata results:**
  - 125,562 job postings since 2026-01-01 mention AI coding tools ("claude code" 76,842; "github copilot" 59,306; "coding agents" 15,769);
  - at least 1,000 distinct companies (the API caps buckets at 1,000).

### 2026-10-11 02:40-03:20: Fleet #2, evaluation and improvement loops (completed)
- **Fleet #2:** agents on #4 (IN-MH tax region) and #5 (currency on charges). Branch tests: 19 passed and 24 passed.
  - Entire's `prepare-commit-msg` hook hung again, even with the agents running one at a time. So the cause is headless sessions here, not concurrency.
  - Same fix as before: commit with hooks off, then `entire session attach`. Checkpoints: #4 `01M4KTRB51MXA4AV8VM3Z33927`, #5 `01M4KTRC57RYSWS08S3JCYQCGQ`.
  - `scripts/fleet.sh` now does this automatically.
- **Eval suite:** `eval/scenarios.json` has 8 labelled pairs (2 interfering, 6 benign), each with a stated reason, on stable tags `eval/*`. **Results** (`eval/results/`, real costs because the cache is bypassed for test synthesis):

  | Version | Recall | Precision | Cost | Time |
  |---|---|---|---|---|
  | v1 merge queue | 1.00 | 0.40 | $0.11 | 61 s |
  | v2.0 | 1.00 | 0.67 | $0.52 | 296 s |
  | v2.1 | 1.00 | 0.67 | $0.40 | 276 s |
  | v2.2 | 1.00 | 1.00 | $0.55 | 307 s |
  | v2.3 | 1.00 | 1.00 | $0.38 | 367 s |

- **Loop 1 (v2.1):**
  - Traces showed benign pairs with no shared code still paying for test synthesis.
  - They also showed a bug: the overlap check only looked one way, so `currency × save10` was reported with no overlap.
  - Fixed: the overlap check now runs in both directions, and a free entire-graph pre-check clears pairs that share nothing.
- **Loop 2 (v2.2):**
  - The one false alarm came from an intent test that hard-coded dollars.
  - Added a second-opinion confirmation: the same intent is re-expressed in the merged code's representation, and the proof is withdrawn only if that test passes on the merge and fails on the base.
  - Result: precision went to 1.0. All 4 real findings were confirmed, and the false alarm was reclassified as `representation_only`.
- **Loop 3 (v2.3):** model ladder (Haiku first, then Sonnet). Cost fell 31% with the same accuracy: 12 of 14 tests were written by Haiku and 2 were escalated to Sonnet.
- **Drift demo #1** (`evidence/runs/land-20261011-031043`): goal "land #4, #5, #1"; simulated teammate "Priya" pushed a free-shipping banner right after #4 landed.
  - Landing #5 hit a **failed compare-and-swap**, which was recorded as drift.
  - Drift analysis showed the banner's new code depends on `Cart.subtotal`, `price_of` and `round_money`, which #1 changes, so **#1 was affected and #5 was not**.
  - #5 then landed (29 tests). #1 was re-proved: intents hold, but `tests/test_pricing.py` had a textual conflict, so Interlock coordinated agent #1.
  - **Agent #1 pushed back:** an acceptance test written for the target's IN-MH intent hard-coded dollars (`tax == 7.2`), which contradicts #1's own task (integer cents). It refused to break its task for 3 rounds, and Interlock **escalated** instead of forcing (`evidence/runs/20261011-031122/state.json`).
- **Loop 4 (from that escalation):** the coordinator now **arbitrates**. When an acceptance test fails, Interlock re-expresses that intent in the new head's representation and accepts the new test only if it passes on the head and fails on the base (`coordinator.reexpress_acceptance`, `arbitrate.reexpress` span). Drift demo #2 re-runs the same scenario from a clean start.

### 2026-10-11 03:16-03:19: Drift demo #2 resolves autonomously (completed)
- `evidence/runs/land-20261011-031600` + `evidence/runs/20261011-031629`: the same goal from a clean start (agent/issue-1 reset to its original commit `c6b4dca`).
- #4 landed, then the teammate pushed (`be772b0`).
- #5's landing CAS failed → drift recorded. #1 affected (the new code depends on `Cart.subtotal`, `price_of`, `round_money`); #5 unaffected → #5 landed (29 tests).
- #1 re-proved: intents hold, but `tests/test_pricing.py` conflicted. Agent #1's own session was resumed and merged the target.
  - **Arbitration re-expressed** the contradictory dollar-based acceptance test `tests/test_interlock_intent_interlock_drift.py`. It was accepted only after passing on the head and failing on the base.
  - Verified → **resolved in round 1** (was: escalated after 3 rounds).
- #1 landed. **Final suite: 48 passed, 0 failed. Goal DONE in 2.5 min, no human.**

### 2026-10-11 10:20-10:45: Orchestrator and neatlogs agent tracing (completed)
- Installed Orchestrator (`ao`). `ao doctor` passes natively on Windows (ConPTY, git worktrees, claude-code and codex harnesses, gh token).
  - `ao start` downloaded and installed the desktop app to `...\Programsgent-orchestrator\`, but then looked for it in `...\Programs\Agent Orchestrator\`: a path-mismatch bug.
  - The app did not start its daemon when launched headlessly; it needs a first run by the builder.
- Added `orchestrator.py`: when the adapting branch belongs to a live `ao` session, the fix request goes through `ao send`, and Interlock waits for a new commit and an idle agent before re-verifying. Otherwise it falls back to resuming the Claude Code session. Not yet exercised against a running daemon.
- Added the neatlogs Claude Code integration to the demo repo (`neatlogs-claude-code setup --project`): 15 hooks, with the key stored in the user config, **not** in the repo (checked). A headless agent turn ran normally with both the neatlogs and Entire hooks.
- Unit tests: 5 passed.

### 2026-10-12 09:30-10:30: Evidence, business model and launch assets (completed)
- Re-read neatlogs.com/hackathon and the official skill: **no changes** since 2026-10-10. Submission window: Mon Oct 12, 19:00 to about 23:55 IST; final cutoff announced on Discord.
- **neatlogs MCP** (`scripts/neatlogs_mcp.py`, project key over `https://ingest.neatlogs.com/mcp`):
  - pulled our traces back from neatlogs: 4 `interlock.land` traces; the drift demo is `01f31441…` with 244 spans → `evidence/neatlogs/`;
  - created a detection group "Interlock" with 3 detections (`recover.next_round`, `recover.repair_test`, `arbitrate.reexpress`). Each was previewed first; after backfill they fire on the drift-demo trace.
- **Business model** (`scripts/business_model.py`): a 12-month Base/Growth model driven by the measured $0.0474 per checked pair → `business-plan/model.csv` and `model_summary.md`.
  - Base breaks even in month 7 (lowest cash $29,122); Growth in month 5.
  - `plan.md` §6 is the cfo.ai data-entry sheet.
- **Share cards** generated from the evidence files (`scripts/make_cards.py` → `docs/media/`): silent bug, agents talking, the agent saying no, scoreboard, drift timeline. They are embedded in the README.
- **Tests run:** `pytest tests` 5 passed.
- **Secrets scan:** 0 matches of any `.env` key in either repo.
- Could not do from this session (no browser or computer-use connection):
  - building the cfo.ai model in the web app;
  - the Orchestrator desktop app's first run (the daemon didn't start headlessly), so the `ao send` path is still not exercised live;
  - posting to X.

### Remaining (builder)
- Enter the cfo.ai model from `business-plan/plan.md` §6 and add the three screenshots.
- Publish the queued posts with the `docs/media` cards and add the URLs to `EVIDENCE.md` §6.
- Record the demo video (≤ 3:00).
- Submit: a quote post of the official neatlogs post (19:00 to the Discord cutoff).

## Demo

- Pending (video ≤ 3:00; URL to be added).

## Known limitations and next steps

- Interlock is not built yet. Main risks: tool behavior differing from the docs, the $20 model budget, Claude Pro usage limits for the agent fleet, and a live run being non-deterministic on camera.

## Submission

Confirmed requirements (neatlogs.com/hackathon, read 2026-10-10):
- [x] Public repo with commits dated during the event (first commit 2026-10-11 00:19 IST)
- [ ] Demo video ≤ 3:00 covering neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning and result for each
- [~] Business plan (pricing, costs, revenue, runway) included in `business-plan/`. cfo.ai model screenshots still pending.
- [x] Evidence in the repo: before/after runs, neatlogs traces (MCP pull), Entire checkpoints/graph output, the business plan, a recovered failure, dated commits (see `EVIDENCE.md`)
- [ ] #neatHack post URLs added to `EVIDENCE.md`
- [ ] Public quote post of the official neatlogs post on X with team, project name, repo and demo link: window opens **Mon Oct 12, 19:00 IST**, and the **final cutoff will be announced on Discord**

Outstanding: cfo.ai screenshots, post URLs, the demo video, and the X quote post.
