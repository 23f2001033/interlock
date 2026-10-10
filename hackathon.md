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
