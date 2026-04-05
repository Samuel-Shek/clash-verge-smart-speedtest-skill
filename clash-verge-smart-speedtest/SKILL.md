---
name: clash-verge-smart-speedtest
description: Configure Clash Verge / Mihomo to keep the best available non-Hong-Kong route using preferred regions, threshold fallback, failed-region cooldown, unlocked-only active tests, and optional Discord health reports. Use when the user wants to tune Clash Verge automatic speed tests, proxy-group routing, unlocked-only checks, route quality monitoring, or Discord network reports. Do not edit the user's Clash rules baseline unless they explicitly ask.
argument-hint: "apply | status | report | uninstall"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# Clash Verge Smart Speedtest

Use this skill when the task is to keep Clash Verge / Mihomo on the best available route without relying on Hong Kong nodes.

## One Screen

- Goal: Keep Clash Verge on the best available non-Hong-Kong route with minimal manual intervention.
- Excluded Regions: 香港。
- Candidate Regions: 台湾、日本、新加坡、美国、英国、马来西亚、土耳其、阿根廷。
- Preferred Regions: 台湾、日本、新加坡。
- Fallback Regions: 美国、英国、马来西亚、土耳其、阿根廷。
- Routing Mode: Compare preferred and fallback pools every active cycle. Stay on preferred unless fallback beats it by more than the preferred threshold.
- Preferred Threshold: 80 毫秒。
- Failed Region Cooldown: 30 分钟。
- Active Test Cadence: Only when the desktop is unlocked, every 10 minutes.
- Reporting: Write local history on every real test. Generate a daily report at 09:05. On Monday/month start/quarter start/year start, also generate the longer-period report. If OpenClaw Discord delivery is configured, send the report there.
- Scope Boundary: Only manage Clash proxy groups, helper scripts, LaunchAgents, local history, and optional report delivery. Do not change the Clash `rules` baseline unless the user explicitly asks.

Try to keep these field names stable and only edit the values after the colon.

## Paths

Defaults:

- Clash base dir: `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev`
- Main config: `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml`
- Profiles dir: `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles`
- Mihomo binary: `/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo`
- Mihomo socket: `/tmp/verge/verge-mihomo.sock`
- Helper script install path: `~/bin/clash-verge-smart-speedtest.sh`
- Report helper install path: `~/bin/clash-verge-smart-speedtest-report.sh`

Override with environment variables when needed:

- `CLASH_VERGE_BASE_DIR`
- `MIHOMO_BIN`
- `MIHOMO_SOCK`
- `CLASH_SPEEDTEST_LABEL`
- `CLASH_SPEEDTEST_REPORT_LABEL`
- `CLASH_REPORT_DISCORD_CHANNEL_ID`
- `CLASH_REPORT_DISCORD_ACCOUNT`
- `OPENCLAW_BIN`

## Standard Implementation

- `自动测速优选` and `自动测速候补` are `url-test` groups.
- `自动测速` is a `select` group that switches between those two pools.
- Keep group `interval` low-frequency and let LaunchAgent handle the real cadence.
- Use `lazy: true`, `timeout: 5000`, and `expected-status: 204` for `url-test`.
- Use unlocked-only gating by checking `IOConsoleLocked`.
- Record every real test into a local JSONL history file.
- Reports are local-file first, Discord second.

## Workflow

1. Read `SKILL.md` and resolve policy from natural-language fields first, YAML fallback second.
2. Find the Clash profile JS that contains `自动测速`.
3. Update profile JS and generated YAML so they stay consistent.
4. Run Mihomo config validation before reload.
5. Reload Mihomo only when config changes.
6. Active-test preferred and fallback groups.
7. Apply threshold selection, then region cooldown logic.
8. Save state and append history.
9. If report job runs, summarize the relevant window and optionally deliver to Discord through OpenClaw.

## Validation

Run and report:

```bash
"$MIHOMO_BIN" -t -d "$CLASH_VERGE_BASE_DIR" -f "$CLASH_VERGE_BASE_DIR/clash-verge.yaml"

launchctl print "gui/$(id -u)/$CLASH_SPEEDTEST_LABEL"

/bin/bash -n ~/bin/clash-verge-smart-speedtest.sh

python3 scripts/sync_from_skill.py --print-policy
python3 scripts/sync_from_skill.py --run-cycle --force
python3 scripts/report_network.py --dry-run
```

Success means:

- Mihomo config test passes
- LaunchAgent is loaded
- a forced cycle chooses a sensible pool
- a dry-run report renders without errors

## Machine Policy Fallback

```yaml
mode: prefer_with_threshold
exclude_regions:
  - 香港
prefer_regions:
  - 台湾
  - 日本
  - 新加坡
fallback_regions:
  - 美国
  - 英国
  - 马来西亚
  - 土耳其
  - 阿根廷
target_groups:
  - 节点组
  - 国外流量
group_interval_seconds: 86400
trigger_interval_seconds: 600
test_url: http://www.gstatic.com/generate_204
timeout_ms: 5000
prefer_threshold_ms: 80
region_cooldown_seconds: 1800
report_hour: 9
report_minute: 5
```

Prefer editing the natural-language fields above. Use this YAML only as a fallback.
