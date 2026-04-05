#!/bin/bash
set -euo pipefail

HOME_DIR="${HOME:-$(eval echo ~)}"
HELPER_SCRIPT="${CLASH_SPEEDTEST_HELPER_SCRIPT:-$HOME_DIR/bin/clash-verge-smart-speedtest.sh}"
REPORT_HELPER_SCRIPT="${CLASH_SPEEDTEST_REPORT_HELPER_SCRIPT:-$HOME_DIR/bin/clash-verge-smart-speedtest-report.sh}"
PLIST_LABEL="${CLASH_SPEEDTEST_LABEL:-com.clash-verge-smart-speedtest}"
REPORT_PLIST_LABEL="${CLASH_SPEEDTEST_REPORT_LABEL:-com.clash-verge-smart-speedtest-report}"
PLIST_PATH="$HOME_DIR/Library/LaunchAgents/$PLIST_LABEL.plist"
REPORT_PLIST_PATH="$HOME_DIR/Library/LaunchAgents/$REPORT_PLIST_LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "$REPORT_PLIST_PATH" >/dev/null 2>&1 || true

rm -f "$PLIST_PATH" "$REPORT_PLIST_PATH" "$HELPER_SCRIPT" "$REPORT_HELPER_SCRIPT"

echo "Removed Clash Verge smart speedtest LaunchAgents and helper scripts."
