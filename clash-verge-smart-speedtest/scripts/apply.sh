#!/bin/bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${HOME:-$(eval echo ~)}"
BASE_DIR="${CLASH_VERGE_BASE_DIR:-$HOME_DIR/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev}"
MIHOMO_BIN="${MIHOMO_BIN:-/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo}"
HELPER_SCRIPT="${CLASH_SPEEDTEST_HELPER_SCRIPT:-$HOME_DIR/bin/clash-verge-smart-speedtest.sh}"
REPORT_HELPER_SCRIPT="${CLASH_SPEEDTEST_REPORT_HELPER_SCRIPT:-$HOME_DIR/bin/clash-verge-smart-speedtest-report.sh}"
PLIST_LABEL="${CLASH_SPEEDTEST_LABEL:-com.clash-verge-smart-speedtest}"
REPORT_PLIST_LABEL="${CLASH_SPEEDTEST_REPORT_LABEL:-com.clash-verge-smart-speedtest-report}"
PLIST_PATH="$HOME_DIR/Library/LaunchAgents/$PLIST_LABEL.plist"
REPORT_PLIST_PATH="$HOME_DIR/Library/LaunchAgents/$REPORT_PLIST_LABEL.plist"
SYNC_SCRIPT="$SKILL_DIR/scripts/sync_from_skill.py"
REPORT_SCRIPT="$SKILL_DIR/scripts/report_network.py"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
LAUNCH_INTERVAL="${CLASH_SPEEDTEST_LAUNCH_INTERVAL:-60}"
REPORT_HOUR="${CLASH_REPORT_HOUR:-9}"
REPORT_MINUTE="${CLASH_REPORT_MINUTE:-5}"

mkdir -p "$(dirname "$HELPER_SCRIPT")" "$(dirname "$PLIST_PATH")" "$HOME_DIR/Library/Logs"

cat > "$HELPER_SCRIPT" <<EOF
#!/bin/bash
set -euo pipefail

export CLASH_VERGE_BASE_DIR="$BASE_DIR"
export MIHOMO_BIN="$MIHOMO_BIN"
"$PYTHON_BIN" "$SYNC_SCRIPT" --run-cycle
EOF

cat > "$REPORT_HELPER_SCRIPT" <<EOF
#!/bin/bash
set -euo pipefail

export CLASH_VERGE_BASE_DIR="$BASE_DIR"
export OPENCLAW_BIN="${OPENCLAW_BIN:-$HOME_DIR/.npm-global/bin/openclaw}"
"$PYTHON_BIN" "$REPORT_SCRIPT" --send-discord
EOF

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$HELPER_SCRIPT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME_DIR</string>
    <key>PATH</key>
    <string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string>
  </dict>
  <key>LimitLoadToSessionType</key>
  <array>
    <string>Aqua</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>$LAUNCH_INTERVAL</integer>
  <key>StandardOutPath</key>
  <string>$HOME_DIR/Library/Logs/clash-verge-smart-speedtest.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME_DIR/Library/Logs/clash-verge-smart-speedtest.err.log</string>
</dict>
</plist>
EOF

cat > "$REPORT_PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$REPORT_PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPORT_HELPER_SCRIPT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME_DIR</string>
    <key>PATH</key>
    <string>$HOME_DIR/.npm-global/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string>
  </dict>
  <key>LimitLoadToSessionType</key>
  <array>
    <string>Aqua</string>
  </array>
  <key>RunAtLoad</key>
  <false/>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$REPORT_HOUR</integer>
    <key>Minute</key>
    <integer>$REPORT_MINUTE</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$HOME_DIR/Library/Logs/clash-verge-smart-speedtest-report.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME_DIR/Library/Logs/clash-verge-smart-speedtest-report.err.log</string>
</dict>
</plist>
EOF

chmod +x "$HELPER_SCRIPT" "$REPORT_HELPER_SCRIPT" "$SYNC_SCRIPT" "$REPORT_SCRIPT" "$0"
plutil -lint "$PLIST_PATH" >/dev/null
plutil -lint "$REPORT_PLIST_PATH" >/dev/null
/bin/bash -n "$HELPER_SCRIPT"
/bin/bash -n "$REPORT_HELPER_SCRIPT"
"$MIHOMO_BIN" -t -d "$BASE_DIR" -f "$BASE_DIR/clash-verge.yaml" >/dev/null

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/$PLIST_LABEL"

launchctl bootout "gui/$(id -u)" "$REPORT_PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$REPORT_PLIST_PATH"

"$PYTHON_BIN" "$SYNC_SCRIPT" --run-cycle --force >/dev/null

echo "Applied Clash Verge smart speedtest skill."
echo "Main helper: $HELPER_SCRIPT"
echo "Main LaunchAgent: $PLIST_PATH"
echo "Report helper: $REPORT_HELPER_SCRIPT"
echo "Report LaunchAgent: $REPORT_PLIST_PATH"
