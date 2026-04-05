# Clash Verge Smart Speedtest Skill

Public skill for keeping Clash Verge / Mihomo on the fastest available non-Hong-Kong route with:

- unlocked-only active tests
- preferred-region routing with threshold fallback
- failed-region cooldown
- optional Discord daily/weekly/monthly/quarterly/yearly reports

The skill itself lives in:

- [clash-verge-smart-speedtest/SKILL.md](./clash-verge-smart-speedtest/SKILL.md)

## What it changes

It only manages:

- `proxy-groups`
- local helper scripts
- LaunchAgents used for scheduled tests and reports

It does **not** rewrite your Clash `rules` baseline.

## Install

Clone the repo:

```bash
git clone https://github.com/Samuel-Shek/clash-verge-smart-speedtest-skill.git
cd clash-verge-smart-speedtest-skill
```

Optional: export environment variables before install:

```bash
cp examples/env.example .env.local
```

Then install:

```bash
/bin/bash clash-verge-smart-speedtest/scripts/apply.sh
```

## Quick start

The default install assumes:

- Clash Verge is already installed
- Mihomo socket is available at `/tmp/verge/verge-mihomo.sock`
- Your Clash config is under `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev`

If that matches your machine, `apply.sh` is enough.

If not, export overrides first, for example:

```bash
export CLASH_VERGE_BASE_DIR="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
export MIHOMO_BIN="/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo"
export MIHOMO_SOCK="/tmp/verge/verge-mihomo.sock"
export CLASH_REPORT_DISCORD_CHANNEL_ID="123456789012345678"
export CLASH_REPORT_DISCORD_ACCOUNT="miso"
/bin/bash clash-verge-smart-speedtest/scripts/apply.sh
```

## Defaults

- Exclude `香港`
- Prefer `台湾 / 日本 / 新加坡`
- Fallback `美国 / 英国 / 马来西亚 / 土耳其 / 阿根廷`
- Switch to fallback only when it beats preferred by more than `80ms`
- Cool down fully failed regions for `30` minutes
- Trigger active tests every `10` minutes when the desktop is unlocked
- Send reports daily at `09:05`

## Optional environment variables

- `CLASH_VERGE_BASE_DIR`
- `MIHOMO_BIN`
- `MIHOMO_SOCK`
- `CLASH_SPEEDTEST_HELPER_SCRIPT`
- `CLASH_SPEEDTEST_REPORT_HELPER_SCRIPT`
- `CLASH_SPEEDTEST_LABEL`
- `CLASH_SPEEDTEST_REPORT_LABEL`
- `CLASH_SPEEDTEST_LAUNCH_INTERVAL`
- `CLASH_REPORT_HOUR`
- `CLASH_REPORT_MINUTE`
- `CLASH_REPORT_DISCORD_CHANNEL_ID`
- `CLASH_REPORT_DISCORD_ACCOUNT`
- `CLASH_REPORT_TIMEZONE`
- `PYTHON_BIN`
- `OPENCLAW_BIN`

## Uninstall

```bash
/bin/bash clash-verge-smart-speedtest/scripts/uninstall.sh
```

This removes only the LaunchAgents and helper scripts installed by this skill. It does not touch your Clash `rules`.

## Generated files

The public skill writes:

- `~/bin/clash-verge-smart-speedtest.sh`
- `~/bin/clash-verge-smart-speedtest-report.sh`
- `~/Library/LaunchAgents/com.clash-verge-smart-speedtest.plist`
- `~/Library/LaunchAgents/com.clash-verge-smart-speedtest-report.plist`
- `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge-smart-speedtest-state.json`
- `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge-smart-speedtest-history.jsonl`
- `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge-smart-speedtest-reports/`

## License

MIT
