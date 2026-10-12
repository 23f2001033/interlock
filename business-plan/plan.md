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

## 4. Scenarios (12 months; full monthly table in `model_summary.md` / `model.csv`)

Months 1-3 are free design-partner pilots with 3 teams (costs, no revenue). Paid conversion starts in month 4.

| | Base | Growth |
|---|---|---|
| Paying teams, month 12 | 40 (10 devs each) | 120 (12 devs each) |
| MRR, month 12 | $12,000 (ARR $144k) | $43,200 (ARR $518k) |
| COGS, month 12 (inference + hosting) | $1,918 | $6,665 |
| Gross margin | 84% | 85% |
| Break-even month | 7 | 5 |
| Lowest cash | $29,122 (month 6) | $33,327 (month 4) |
| Cash, month 12 | $45,978 | $127,688 |

## 5. Costs and runway

- **Opex:** $4,500/month (founder stipend $3,000, tools $400, base infra $300, marketing and community $800). A founding engineer ($6,000/month) is added the month after MRR first reaches $15k (month 9 in Growth; not within 12 months in Base).
- **Starting cash:** $50,000 (assumption, editable).
- **Runway:** pre-revenue burn is about $4.6k/month, so ~10.8 months of runway with no revenue at all. In both scenarios cash never falls below $29k and the business is cash-flow positive by month 7 (Base) or month 5 (Growth).
- **Biggest risk lever:** cost per check. At v2.0 costs ($0.065 per check) the Base margin drops to about 79% and break-even slips from month 7 to month 8. That is why the improvement loops target cost.

## 6. cfo.ai data-entry sheet (builder, ~10 minutes)

Create a model named **Interlock** and enter these drivers exactly (all are in `scripts/business_model.py`):

| Driver | Base | Growth |
|---|---|---|
| Price per developer / month | $30 | $30 |
| Developers per customer | 10 | 12 |
| Paying customers: month 4 → month 12 | 4 → 40 (linear) | 6 → 120 (accelerating) |
| Pilot customers, months 1-3 (no revenue) | 3 | 3 |
| Inference cost per check (measured) | $0.0474 | $0.0474 |
| Checks per developer / month | 80 | 80 |
| Hosting per customer / month | $10 | $10 |
| Opex / month | $4,500 | $4,500 |
| Founding engineer | $6,000/month once MRR ≥ $15k | same |
| Starting cash | $50,000 | $50,000 |

Then screenshot (or export) the **Unit economics**, **Scenarios** and **Runway** views into this folder (`cfo-unit-economics.png`, `cfo-scenarios.png`, `cfo-runway.png`) and check the cfo.ai numbers against `model_summary.md`.
