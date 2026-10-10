# Interlock: Business Plan

> Source of truth for the model we build in **cfo.ai** (Unit economics · Runway · Scenarios).
> Every cost input is **measured** (neatlogs traces and LiteLLM cost headers, see `evidence/`), and market inputs come from **Crustdata**.
> Status: draft numbers below; final figures will be copied from the cfo.ai model.

## 1. Customer and problem

- **Buyer:** engineering teams that run several AI coding agents on one codebase: parallel agent fleets (Orchestrator, Claude Code, Codex, Cursor background agents) and background PR agents.
- **Pain:** code review is per-PR, but AI changes break each other *across* PRs. Fixing a cross-PR regression after it ships costs hours of senior engineering time and sometimes revenue (our demo: a fee that silently never charges).
- **Market signal (Crustdata, job postings since 2026-01-01, `business-plan/market_crustdata.json`):**
  - **125,562** postings mention AI coding tools: "claude code" 76,842, "github copilot" 59,306, "coding agents" 15,769, "cursor ai" 1,320, "codex cli" 297.
  - **≥ 1,000** distinct hiring companies. This is a lower bound, because the API caps buckets at 1,000.

## 2. Product and pricing

| Plan | Price | Includes |
|---|---|---|
| Free (OSS CLI) | $0 | `interlock prove` / `land`, bring your own model key |
| **Team** | **$30 per developer / month** | Hosted goal mode on every PR queue, agent coordination, neatlogs-traced reports, 500 proofs per month |
| Scale | $3,000+ / month | SSO, self-hosted runners, unlimited proofs, SLA |

Why per developer: the value (prevented cross-PR regressions) grows with the number of agents each developer runs. Per developer is also simple to buy.

## 3. Unit economics (measured)

| Input | Value | Source |
|---|---|---|
| LLM cost per checked pair, current version (v2.3: graph pre-check + second opinion + Haiku-first ladder) | **$0.047** average ($0.38 for 8 pairs) | `eval/results/v2.3-*.json` |
| LLM cost per pair that shares no code (cleared by entire-graph) | **$0.00** | `cleared_by_graph` |
| LLM cost per real interference (proof + confirmation, both directions) | **≈ $0.09** | eval v2.3 rows `fee_x_cents`, `save10_x_cents` |
| LLM cost per coordination decision + summary | **$0.0011** | run `20261011-013837` |
| Accuracy on the labelled suite | recall 1.0, precision 1.0 (merge queue: precision 0.40) | `EVIDENCE.md` |
| Agent fix turns | **$0 to us** (they run on the customer's own agent subscription) | design |

**COGS per Team customer (10 devs, ~400 agent PRs/month, ~2 pair checks per PR):** 800 checks × $0.047 + hosting $10 ≈ **$48/month** against **$300/month** revenue, so **gross margin ≈ 84%**. With v2.0 costs ($0.065 per check) the same customer would cost ≈ $62/month (79%).

**Decision driven by the model:** inference is the only cost that grows with usage, so the margin depends on cost per check. That is why the improvement loops target it: the entire-graph pre-check (free for unrelated pairs) and the Haiku-first ladder cut cost per check from $0.065 to $0.047 (−28%) while raising precision from 0.67 to 1.0. See `EVIDENCE.md`.

## 4. Scenarios (monthly, month 12)

| | Base | Growth |
|---|---|---|
| Team customers | 40 | 120 |
| Avg developers per customer | 10 | 12 |
| MRR | $12,000 | $43,200 |
| Infra + inference (COGS) | $1,920 | $6,600 |
| Gross margin | 84% | 85% |

## 5. Costs and runway

- Team: solo founder now; first hire (founding engineer) once MRR reaches $10k.
- Monthly burn before revenue: about $2,500 (founder stipend, infra, model credits, tools).
- Starting cash: [to fill in cfo.ai] → runway = cash / net burn (computed in cfo.ai's Runway tab).

## 6. cfo.ai checklist (builder)

1. Create the model "Interlock" with Base and Growth scenarios, using the inputs above.
2. Unit economics tab: price per developer, proofs per customer, cost per proof ($0.062), hosting.
3. Runway tab: burn and cash.
4. Export or screenshot the three tabs into `business-plan/` and link them from the README.
