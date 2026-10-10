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

### Planned next
- Claim the LiteLLM key and add `LITELLM_API_KEY` to `.env`.
- Builder confirms creating the public GitHub repos, then push.
- Open a new Claude Code session in `interlock/` (captured by Entire), wire neatlogs + LiteLLM, and build L0 (Prover).
- Run the agent fleet on issues #1-#3 in the demo repo.
- First #neatHack post.

## Demo

- Pending (video ≤ 3:00; URL to be added).

## Known limitations and next steps

- Interlock is not built yet. Main risks: tool behavior differing from the docs, the $20 model budget, Claude Pro usage limits for the agent fleet, and a live run being non-deterministic on camera.

## Submission

Confirmed requirements (neatlogs.com/hackathon, read 2026-10-10):
- [ ] Public repo with commits dated during the event
- [ ] Demo video ≤ 3:00 covering neatlogs, Entire and cfo.ai: architecture, implementation, runtime, reasoning and result for each
- [ ] cfo.ai business plan (pricing, costs, revenue, runway) included
- [ ] Evidence in the repo: before/after runs, neatlogs traces, Entire checkpoints/graph output, the business plan, a recovered failure, #neatHack posts, dated commits
- [ ] Public quote post of the official neatlogs post on X with team, project name, repo and demo link: window opens **Mon Oct 12, 19:00 IST**, and the **final cutoff will be announced on Discord**

Outstanding: everything above.
