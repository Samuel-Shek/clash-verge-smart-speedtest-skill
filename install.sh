#!/bin/bash
set -euo pipefail

TARGET="${1:-both}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="clash-verge-smart-speedtest"
SOURCE_DIR="$REPO_DIR/$SKILL_NAME"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"
OPENCLAW_SKILLS_DIR="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}"

install_one() {
  local target_dir="$1"
  mkdir -p "$(dirname "$target_dir")"
  rm -rf "$target_dir"
  cp -R "$SOURCE_DIR" "$target_dir"
  echo "Installed to $target_dir"
}

case "$TARGET" in
  codex)
    install_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    ;;
  claude)
    install_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    ;;
  both)
    install_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    install_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    ;;
  openclaw)
    install_one "$OPENCLAW_SKILLS_DIR/$SKILL_NAME"
    ;;
  all)
    install_one "$CODEX_HOME_DIR/skills/$SKILL_NAME"
    install_one "$CLAUDE_HOME_DIR/skills/$SKILL_NAME"
    install_one "$OPENCLAW_SKILLS_DIR/$SKILL_NAME"
    ;;
  *)
    echo "Usage: /bin/bash install.sh [codex|claude|both|openclaw|all]" >&2
    exit 1
    ;;
esac
