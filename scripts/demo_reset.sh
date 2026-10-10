#!/usr/bin/env bash
# Resets the LOCAL demo state so the drift demo can be recorded again from a clean start:
# target branch interlock-drift -> base commit, agent/issue-1 -> the agent's original commit.
# Nothing is pushed. Usage: scripts/demo_reset.sh <path-to-interlock-demo-shop>
set -eu
SHOP="${1:?path to interlock-demo-shop}"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/dev/null
WT1="$(cd "$SHOP/.." && pwd)/shop-wt/issue-1"
git -C "$WT1" reset -q --hard eval/cents
git -C "$SHOP" branch -f interlock-drift 7950d86
echo "reset: interlock-drift -> 7950d86, agent/issue-1 -> $(git -C "$SHOP" rev-parse --short eval/cents)"
echo "record with:"
echo "  (bash scripts/teammate_push.sh \"$SHOP\" interlock-drift agent/issue-4 &)"
echo "  uv run interlock land agent/issue-4 agent/issue-5 agent/issue-1 --into interlock-drift --keep-order --repo \"$SHOP\""
