#!/bin/bash
set -euo pipefail

TARGET="${1:-both}"
SKILL_NAME="clash-verge-smart-speedtest"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"
OPENCLAW_SKILLS_DIR="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}"

remove_one() {
  local target_dir="$1"
  rm -rf "$target_dir"
  echo "Removed $target_dir"
}

case "$TARGET" in
  codex)
    remove_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    ;;
  claude)
    remove_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    ;;
  both)
    remove_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    remove_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    ;;
  openclaw)
    remove_one "$OPENCLAW_SKILLS_DIR/$SKILL_NAME"
    ;;
  all)
    remove_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    remove_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    remove_one "$OPENCLAW_SKILLS_DIR/$SKILL_NAME"
    ;;
  *)
    echo "Usage: /bin/bash uninstall.sh [codex|claude|both|openclaw|all]" >&2
    exit 1
    ;;
esac
