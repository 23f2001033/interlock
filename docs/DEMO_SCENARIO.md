# Demo Scenario

The environment is `../interlock-demo-shop`: a tiny Python shop backend (catalog, cart, pricing, payments, orders, receipts) with 16 passing tests. Entire is enabled there, so every coding-agent commit carries a checkpoint (prompt, session, transcript).

**Rule: we never hand-write the conflicting code.** We give realistic, neutral issues to independent coding agents that branch from the same `main`. Whatever interference they produce is real, and we record it honestly (including "no interference found").

## Issues for the agent fleet

The texts are in [`issues/`](issues). They are neutral, with no hints about other work:

| # | Issue | Touches |
|---|---|---|
| 1 | Represent money as integer cents end-to-end | catalog, cart, pricing, orders, receipts (changes the *meaning* of every amount) |
| 2 | Small-order fee under $15.00 | pricing quote (thresholds written in dollars) |
| 3 | SAVE10 discount (10% off subtotals ≥ $40.00) | orders, pricing quote (thresholds in dollars) |

Expected kinds of outcome (not guaranteed, which is the point):
- **#1 × #2 / #1 × #3**: semantic interference (dollar thresholds vs cent amounts). It is either caught by the existing tests on the merge, or silent if the agent's tests call the new function directly with dollar literals. Only a synthesized intent test catches the silent case.
- **#2 × #3**: a probable textual conflict in `quote()`, which leads to a rebase request.

## Running the fleet (sequential is fine, since every agent starts from the same base commit)

From Git Bash, after restarting VS Code so `entire` is on PATH:

```bash
cd ../interlock-demo-shop
for n in 1 2 3; do git worktree add "../shop-wt/issue-$n" -b "agent/issue-$n" main; done
for n in 1 2 3; do
  (cd "../shop-wt/issue-$n" && claude -p "$(cat ../../interlock/docs/issues/issue-$n.md)" \
     --permission-mode acceptEdits \
     --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Bash(uv run pytest:*)" "Bash(git status:*)" "Bash(git diff:*)" "Bash(git add:*)" "Bash(git commit:*)")
done
```

Then check: `git log --oneline main..agent/issue-N` in each worktree shows the agent's commits, and `entire checkpoint list` / `entire why <file>:<line>` returns the agent's prompt and session.

The Orchestrator variant (stretch, needs WSL + tmux) is `ao spawn` with the same issues.

## Drift (a teammate merges to `main` mid-run)

While `interlock land` is running, a "human" commit lands on `main` with no Entire checkpoint. It adds a storefront banner helper that depends on the meaning of `Cart.subtotal()`:

```python
# shop/banner.py
from shop.cart import Cart
from shop.money import format_money
from shop.pricing import FREE_SHIPPING_THRESHOLD


def free_shipping_banner(cart: Cart) -> str:
    remaining = FREE_SHIPPING_THRESHOLD - cart.subtotal()
    if remaining <= 0:
        return "You've unlocked free shipping!"
    return f"Add {format_money(remaining)} more for free shipping"
```

It comes with a test: one tote bag ($9.95) → `"Add $40.05 more for free shipping"`.

Interlock must notice `main` moved, treat the new commit as a change set, re-plan only the pairs it touches (e.g. #1 × banner), and handle it.

## Demo beats (≤ 3:00 video)

1. Three agents, three green branches. A naive merge with green CI still ships a broken checkout.
2. `interlock land`: plan → candidates (graph impact) → intent (`entire why`) → proof (passes alone, fails together) → fix request to the agent's own session → re-proof → `main` moves → re-plan → land → final suite green.
3. neatlogs trace tree, a recovered failure, v1 vs v2 numbers. Entire checkpoints on the agents' commits and on ours. cfo.ai unit economics from the measured $/pair.
