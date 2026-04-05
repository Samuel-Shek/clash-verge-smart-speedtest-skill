#!/bin/bash
set -euo pipefail

TARGET="${1:-both}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="clash-verge-smart-speedtest"
SOURCE_DIR="$REPO_DIR/$SKILL_NAME"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME_DIR="${CLAUDE_HOME:-$HOME/.claude}"

install_one() {
  local root="$1"
  local target_dir="$root/skills/$SKILL_NAME"
  mkdir -p "$root/skills"
  rm -rf "$target_dir"
  cp -R "$SOURCE_DIR" "$target_dir"
  echo "Installed to $target_dir"
}

case "$TARGET" in
  codex)
    install_one "$CODEX_HOME_DIR"
    ;;
  claude)
    install_one "$CLAUDE_HOME_DIR"
    ;;
  both)
    install_one "$CODEX_HOME_DIR"
    install_one "$CLAUDE_HOME_DIR"
    ;;
  *)
    echo "Usage: /bin/bash install.sh [codex|claude|both]" >&2
    exit 1
    ;;
esac
