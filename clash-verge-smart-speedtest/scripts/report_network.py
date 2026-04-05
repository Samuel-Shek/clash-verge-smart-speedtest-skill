#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HOME = Path.home()
BASE = Path(os.environ.get("CLASH_VERGE_BASE_DIR", str(HOME / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"))).expanduser()
HISTORY_PATH = BASE / "clash-verge-smart-speedtest-history.jsonl"
REPORTS_DIR = BASE / "clash-verge-smart-speedtest-reports"
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", str(HOME / ".npm-global/bin/openclaw"))
DEFAULT_CHANNEL_ID = os.environ.get("CLASH_REPORT_DISCORD_CHANNEL_ID", "")
DEFAULT_ACCOUNT = os.environ.get("CLASH_REPORT_DISCORD_ACCOUNT", "miso")
TZ = ZoneInfo(os.environ.get("CLASH_REPORT_TIMEZONE", "Asia/Shanghai"))


@dataclass
class ReportWindow:
    kind: str
    label: str
    start: datetime
    end: datetime
    file_stub: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-discord", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--now-iso", default="")
    return parser.parse_args()


def now_local(now_iso: str) -> datetime:
    if now_iso:
        return datetime.fromisoformat(now_iso).astimezone(TZ)
    return datetime.now(TZ)


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, TZ)


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    rows = []
    for line in HISTORY_PATH.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("ts"), int):
            rows.append(row)
    return rows


def window_entries(rows: list[dict], start: datetime, end: datetime) -> list[dict]:
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    return [row for row in rows if start_ts <= row.get("ts", 0) < end_ts]


def completed_windows(now: datetime) -> list[ReportWindow]:
    windows = []
    yesterday = now.date() - timedelta(days=1)
    windows.append(ReportWindow("daily", f"日报 {yesterday.isoformat()}", start_of_day(yesterday), start_of_day(now.date()), f"daily/{yesterday.isoformat()}"))
    if now.weekday() == 0:
        week_end = now.date()
        week_start = week_end - timedelta(days=7)
        iso_year, iso_week, _ = (week_end - timedelta(days=1)).isocalendar()
        windows.append(ReportWindow("weekly", f"周报 {week_start.isoformat()} ~ {(week_end - timedelta(days=1)).isoformat()}", start_of_day(week_start), start_of_day(week_end), f"weekly/{iso_year}-W{iso_week:02d}"))
    if now.day == 1:
        prev_month_last = now.date() - timedelta(days=1)
        month_start = prev_month_last.replace(day=1)
        windows.append(ReportWindow("monthly", f"月报 {prev_month_last.strftime('%Y-%m')}", start_of_day(month_start), start_of_day(now.date()), f"monthly/{prev_month_last.strftime('%Y-%m')}"))
    if now.day == 1 and now.month in (1, 4, 7, 10):
        quarter_end = now.date() - timedelta(days=1)
        quarter = ((quarter_end.month - 1) // 3) + 1
        quarter_start = date(quarter_end.year, 3 * (quarter - 1) + 1, 1)
        windows.append(ReportWindow("quarterly", f"季度报 {quarter_end.year} Q{quarter}", start_of_day(quarter_start), start_of_day(now.date()), f"quarterly/{quarter_end.year}-Q{quarter}"))
    if now.month == 1 and now.day == 1:
        prev_year = now.year - 1
        windows.append(ReportWindow("yearly", f"年报 {prev_year}", start_of_day(date(prev_year, 1, 1)), start_of_day(date(now.year, 1, 1)), f"yearly/{prev_year}"))
    return windows


def median_or_none(values: list[int]) -> int | None:
    return int(statistics.median(values)) if values else None


def format_ms(value: int | None) -> str:
    return f"{value}ms" if value is not None else "无数据"


def summarize(window: ReportWindow, rows: list[dict]) -> tuple[str, str]:
    if not rows:
        body = f"📡 **网络{window.label}**\n\n- 数据量：0\n- 结论：这一周期没有采样数据。"
        return body, body

    chosen_groups = Counter(row.get("chosen_group") or "未选择" for row in rows)
    chosen_nodes = Counter(row.get("chosen_node") or "未选择" for row in rows)
    cooled_regions = Counter(region for row in rows for region in row.get("cooled_regions_this_cycle", []))
    active_cooldowns = Counter(region for row in rows for region in row.get("active_cooldown_regions", []))

    chosen_delay = median_or_none([row["chosen_delay_ms"] for row in rows if isinstance(row.get("chosen_delay_ms"), int)])
    prefer_best = median_or_none([row["prefer_best_ms"] for row in rows if isinstance(row.get("prefer_best_ms"), int)])
    fallback_best = median_or_none([row["fallback_best_ms"] for row in rows if isinstance(row.get("fallback_best_ms"), int)])

    best_group, best_group_count = chosen_groups.most_common(1)[0]
    best_node, best_node_count = chosen_nodes.most_common(1)[0]
    if prefer_best is not None and fallback_best is not None and fallback_best + 80 < prefer_best:
        judgment = "候补池整体更优，当前策略切到候补池是对的。"
    elif prefer_best is not None and fallback_best is not None:
        judgment = "优选池和候补池差距不大，优先地区偏好仍成立。"
    else:
        judgment = "采样不足，先继续积累数据。"

    cooled_text = "、".join(region for region, _ in cooled_regions.most_common(3)) or "无"
    active_text = "、".join(region for region, _ in active_cooldowns.most_common(3)) or "无"
    message = (
        f"📡 **网络{window.label}**\n\n"
        f"- 数据量：{len(rows)} 次采样\n"
        f"- 主出入口：`{best_group}`（{best_group_count} 次）\n"
        f"- 最常用节点：`{best_node}`（{best_node_count} 次）\n"
        f"- 中位最终延迟：`{format_ms(chosen_delay)}`\n"
        f"- 优选池中位最佳：`{format_ms(prefer_best)}`\n"
        f"- 候补池中位最佳：`{format_ms(fallback_best)}`\n"
        f"- 本周期新冷却地区：{cooled_text}\n"
        f"- 周期末仍在冷却：{active_text}\n"
        f"- 结论：{judgment}"
    )
    markdown = (
        f"# 网络{window.label}\n\n"
        f"- 周期：{window.start.strftime('%Y-%m-%d %H:%M')} ~ {window.end.strftime('%Y-%m-%d %H:%M')}\n"
        f"- 数据量：{len(rows)} 次采样\n"
        f"- 主出入口：{best_group}（{best_group_count} 次）\n"
        f"- 最常用节点：{best_node}（{best_node_count} 次）\n"
        f"- 中位最终延迟：{format_ms(chosen_delay)}\n"
        f"- 优选池中位最佳：{format_ms(prefer_best)}\n"
        f"- 候补池中位最佳：{format_ms(fallback_best)}\n"
        f"- 本周期新冷却地区：{cooled_text}\n"
        f"- 周期末仍在冷却：{active_text}\n"
        f"- 结论：{judgment}\n"
    )
    return message, markdown


def write_report(window: ReportWindow, markdown: str) -> Path:
    path = REPORTS_DIR / f"{window.file_stub}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    return path


def send_discord(message: str, channel_id: str, account: str, dry_run: bool) -> dict:
    if not channel_id:
        return {"skipped": "missing_channel_id"}
    if not Path(OPENCLAW_BIN).exists():
        return {"skipped": "missing_openclaw"}
    cmd = [
        OPENCLAW_BIN,
        "message",
        "send",
        "--channel",
        "discord",
        "--account",
        account,
        "--target",
        channel_id,
        "--message",
        message,
        "--json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, text=True, capture_output=True, check=True)
    return {"stdout": proc.stdout.strip()}


def main() -> int:
    args = parse_args()
    rows = load_history()
    now = now_local(args.now_iso)
    outputs = []
    for window in completed_windows(now):
        entries = window_entries(rows, window.start, window.end)
        message, markdown = summarize(window, entries)
        path = write_report(window, markdown)
        output = {"kind": window.kind, "path": str(path), "message": message, "count": len(entries)}
        if args.send_discord:
            output["discord"] = send_discord(message, args.channel_id, args.account, args.dry_run)
        outputs.append(output)
    print(json.dumps({"ok": True, "reports": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
