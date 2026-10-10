#!/usr/bin/env bash
# Simulated teammate (a human, no AI session): once `wait_for` has landed on the target branch,
# pushes a storefront banner commit to it. Used to show Interlock working while the environment changes.
# Usage: scripts/teammate_push.sh <repo> <target-branch> <wait_for-ref>
set -eu
REPO="$1"; INTO="$2"; WAIT_FOR="$3"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null
until git -C "$REPO" merge-base --is-ancestor "$WAIT_FOR" "$INTO" 2>/dev/null; do sleep 2; done
WT="$(mktemp -d)/teammate"
git -C "$REPO" worktree add -q --detach "$WT" "$INTO"
cat > "$WT/shop/banner.py" <<'PY'
"""Storefront banner for the cart page."""

from shop.cart import Cart
from shop.money import format_money
from shop.pricing import FREE_SHIPPING_THRESHOLD


def free_shipping_banner(cart: Cart) -> str:
    remaining = FREE_SHIPPING_THRESHOLD - cart.subtotal()
    if remaining <= 0:
        return "You've unlocked free shipping!"
    return f"Add {format_money(remaining)} more for free shipping"
PY
cat > "$WT/tests/test_banner.py" <<'PY'
from shop.banner import free_shipping_banner
from shop.cart import Cart


def test_banner_shows_amount_left_for_free_shipping():
    cart = Cart()
    cart.add("BAG-01")
    assert free_shipping_banner(cart) == "Add $40.05 more for free shipping"


def test_banner_when_free_shipping_unlocked():
    cart = Cart()
    cart.add("MUG-01", 4)
    assert free_shipping_banner(cart) == "You've unlocked free shipping!"
PY
git -C "$WT" add -A
git -C "$WT" -c user.name="Priya (teammate)" -c user.email=teammate@example.com commit -q -m "Add free-shipping banner for the cart page"
OLD=$(git -C "$REPO" rev-parse "$INTO"); NEW=$(git -C "$WT" rev-parse HEAD)
git -C "$REPO" update-ref "refs/heads/$INTO" "$NEW" "$OLD" && echo "teammate pushed $NEW onto $INTO"
git -C "$REPO" worktree remove --force "$WT"
