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
| LLM cost per proven pair (2 intent tests, Sonnet) | **$0.062** | run `20261011-013325`, LiteLLM cost header |
| LLM cost per coordination decision + summary | **$0.0011** | run `20261011-013837` |
| Share of PR pairs needing an LLM proof (no shared entities → cleared by entire-graph for free) | to measure with `interlock eval` | eval results |
| Agent fix turns | **$0 to us** (they run on the customer's own agent subscription) | design |

**COGS per Team customer (10 devs, ~400 agent PRs/month, assume 25% need a proof):** 100 proofs × $0.062 + hosting $5 ≈ **$11/month** against **$300/month** revenue, so **gross margin ≈ 96%**.

**Decision driven by the model:** if every pair needed a Sonnet proof, COGS would be about 4× higher. That is why Interlock clears pairs with entire-graph first and uses a model ladder (nova/haiku before sonnet). See the improvement loops in `EVIDENCE.md`.

## 4. Scenarios (monthly, month 12)

| | Base | Growth |
|---|---|---|
| Team customers | 40 | 120 |
| Avg developers per customer | 10 | 12 |
| MRR | $12,000 | $43,200 |
| Infra + inference (COGS) | $480 | $1,700 |
| Gross margin | 96% | 96% |

## 5. Costs and runway

- Team: solo founder now; first hire (founding engineer) once MRR reaches $10k.
- Monthly burn before revenue: about $2,500 (founder stipend, infra, model credits, tools).
- Starting cash: [to fill in cfo.ai] → runway = cash / net burn (computed in cfo.ai's Runway tab).

## 6. cfo.ai checklist (builder)

1. Create the model "Interlock" with Base and Growth scenarios, using the inputs above.
2. Unit economics tab: price per developer, proofs per customer, cost per proof ($0.062), hosting.
3. Runway tab: burn and cash.
4. Export or screenshot the three tabs into `business-plan/` and link them from the README.
