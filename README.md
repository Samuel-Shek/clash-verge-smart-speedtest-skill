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

```bash
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
- `CLASH_SPEEDTEST_LABEL`
- `CLASH_SPEEDTEST_REPORT_LABEL`
- `CLASH_REPORT_DISCORD_CHANNEL_ID`
- `CLASH_REPORT_DISCORD_ACCOUNT`
- `OPENCLAW_BIN`

## License

MIT
