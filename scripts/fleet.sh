#!/usr/bin/env bash
# Runs the demo agent fleet: one headless Claude Code session per issue, each in its own
# git worktree branched from the same base commit. Sessions are captured by Entire.
# Agents run one after another: they still all start from the same base commit (that is what makes
# them "parallel" for integration), and Entire's commit hook can block when several sessions are
# active in one repository at once.
# Usage: scripts/fleet.sh <path-to-interlock-demo-shop> [issue numbers...]
set -u
export PATH="$HOME/.local/bin:$PATH"   # Entire hooks skip silently if `entire` is not on PATH

SHOP="${1:?usage: fleet.sh <path-to-interlock-demo-shop> [issues...]}"; shift
ISSUES_DIR="$(cd "$(dirname "$0")/../docs/issues" && pwd)"
NUMS=("${@:-1 2 3}"); [ "$#" -eq 0 ] && NUMS=(1 2 3)
WT="$(cd "$SHOP/.." && pwd)/shop-wt"
LOGS="$WT/logs"
mkdir -p "$LOGS"

for n in "${NUMS[@]}"; do
  git -C "$SHOP" worktree add -q "$WT/issue-$n" -b "agent/issue-$n" main
done

for n in "${NUMS[@]}"; do
  (
    cd "$WT/issue-$n" &&
    claude -p "$(cat "$ISSUES_DIR/issue-$n.md")" \
      --permission-mode acceptEdits \
      --allowedTools Read Edit Write Glob Grep \
        "Bash(uv run pytest:*)" "Bash(uv run python:*)" \
        "Bash(git status:*)" "Bash(git diff:*)" "Bash(git add:*)" "Bash(git commit:*)" "Bash(git log:*)" \
      --output-format json > "$LOGS/issue-$n.json" 2> "$LOGS/issue-$n.err"
    echo "issue-$n exited $?"
  )
done
for n in "${NUMS[@]}"; do
  echo "== agent/issue-$n"; git -C "$WT/issue-$n" log --oneline main..HEAD
done
