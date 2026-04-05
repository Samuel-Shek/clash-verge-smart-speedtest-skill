#!/bin/bash
set -euo pipefail

TARGET="${1:-both}"
SKILL_NAME="clash-verge-smart-speedtest"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"

remove_one() {
  local root="$1"
  local target_dir="$root/skills/$SKILL_NAME"
  rm -rf "$target_dir"
  echo "Removed $target_dir"
}

case "$TARGET" in
  codex)
    remove_one "$CODEX_HOME_DIR"
    ;;
  claude)
    remove_one "$CLAUDE_HOME_DIR"
    ;;
  both)
    remove_one "$CODEX_HOME_DIR"
    remove_one "$CLAUDE_HOME_DIR"
    ;;
  *)
    echo "Usage: /bin/bash uninstall.sh [codex|claude|both]" >&2
    exit 1
    ;;
esac
