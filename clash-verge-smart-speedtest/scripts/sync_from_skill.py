#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HOME = Path.home()
BASE = Path(os.environ.get("CLASH_VERGE_BASE_DIR", str(HOME / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"))).expanduser()
MAIN_YAML = BASE / "clash-verge.yaml"
PROFILES_DIR = BASE / "profiles"
MIHOMO_BIN = Path(os.environ.get("MIHOMO_BIN", "/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo")).expanduser()
MIHOMO_SOCK = Path(os.environ.get("MIHOMO_SOCK", "/tmp/verge/verge-mihomo.sock")).expanduser()
STATE_PATH = BASE / "clash-verge-smart-speedtest-state.json"
HISTORY_PATH = BASE / "clash-verge-smart-speedtest-history.jsonl"
RUBY_BIN = "/usr/bin/ruby"

AUTO_GROUP = "自动测速"
PREFER_GROUP = "自动测速优选"
FALLBACK_GROUP = "自动测速候补"
MANAGED_GROUPS = {AUTO_GROUP, PREFER_GROUP, FALLBACK_GROUP}

DEFAULT_POLICY = {
    "mode": "prefer_with_threshold",
    "exclude_regions": ["香港"],
    "prefer_regions": ["台湾", "日本", "新加坡"],
    "fallback_regions": ["美国", "英国", "马来西亚", "土耳其", "阿根廷"],
    "target_groups": ["节点组", "国外流量"],
    "group_interval_seconds": 86400,
    "trigger_interval_seconds": 600,
    "test_url": "http://www.gstatic.com/generate_204",
    "timeout_ms": 5000,
    "prefer_threshold_ms": 80,
    "region_cooldown_seconds": 1800,
    "report_hour": 9,
    "report_minute": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-cycle", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--print-policy", action="store_true")
    return parser.parse_args()


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def ruby_load_yaml_text(text: str):
    proc = subprocess.run(
        [
            RUBY_BIN,
            "-ryaml",
            "-rjson",
            "-e",
            'data = YAML.safe_load(STDIN.read, aliases: true) || {}; puts JSON.generate(data)',
        ],
        input=text,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def load_yaml_file(path: Path):
    return ruby_load_yaml_text(path.read_text())


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.S | re.M)
    return match.group(1) if match else ""


def ordered_regions_in_text(text: str, available_regions: list[str]) -> list[str]:
    hits = []
    for region in available_regions:
        idx = text.find(region)
        if idx >= 0:
            hits.append((idx, region))
    hits.sort()
    return [region for _, region in hits]


def parse_duration_to_seconds(text: str) -> int | None:
    minute = re.search(r"(\d+)\s*分钟", text)
    if minute:
        return int(minute.group(1)) * 60
    second = re.search(r"(\d+)\s*秒", text)
    if second:
        return int(second.group(1))
    hour = re.search(r"(\d+)\s*小时", text)
    if hour:
        return int(hour.group(1)) * 3600
    return None


def parse_natural_language_policy(text: str, available_regions: list[str]) -> dict:
    result: dict = {}
    overview = extract_section(text, "One Screen")
    target_groups_known = [
        "节点组",
        "国外流量",
        "ChatGPT",
        "Gemini",
        "Netflix",
        "Youtube",
        "Facebook",
        "苹果服务",
        "其他流量",
    ]

    candidate_regions: list[str] = []
    prefer_regions: list[str] = []
    fallback_regions: list[str] = []
    exclude_regions: list[str] = []

    for line in overview.splitlines():
        normalized = line.strip().lstrip("- ").strip()
        if not normalized:
            continue
        if normalized.startswith("Excluded Regions:"):
            exclude_regions = ordered_regions_in_text(normalized, available_regions)
        elif normalized.startswith("Candidate Regions:"):
            candidate_regions = ordered_regions_in_text(normalized, available_regions)
        elif normalized.startswith("Preferred Regions:"):
            prefer_regions = ordered_regions_in_text(normalized, available_regions)
        elif normalized.startswith("Fallback Regions:"):
            fallback_regions = ordered_regions_in_text(normalized, available_regions)
        elif normalized.startswith("Preferred Threshold:"):
            match = re.search(r"(\d+)", normalized)
            if match:
                result["prefer_threshold_ms"] = int(match.group(1))
        elif normalized.startswith("Failed Region Cooldown:"):
            duration = parse_duration_to_seconds(normalized)
            if duration:
                result["region_cooldown_seconds"] = duration
        elif normalized.startswith("Active Test Cadence:"):
            duration = parse_duration_to_seconds(normalized)
            if duration:
                result["trigger_interval_seconds"] = duration
        elif normalized.startswith("Routing Mode:"):
            if "threshold" in normalized.lower() or "快过优选池超过" in normalized:
                result["mode"] = "prefer_with_threshold"
        elif normalized.startswith("Reporting:"):
            hour_match = re.search(r"(\d{1,2}):(\d{2})", normalized)
            if hour_match:
                result["report_hour"] = int(hour_match.group(1))
                result["report_minute"] = int(hour_match.group(2))
        elif normalized.startswith("Scope Boundary:"):
            targets = [group for group in target_groups_known if group in normalized]
            if targets:
                result["target_groups"] = targets

    if candidate_regions:
        result["candidate_regions"] = candidate_regions
    if exclude_regions:
        result["exclude_regions"] = exclude_regions
    if prefer_regions:
        result["prefer_regions"] = prefer_regions
    if fallback_regions:
        result["fallback_regions"] = fallback_regions
    if candidate_regions and not fallback_regions and prefer_regions:
        result["fallback_regions"] = [region for region in candidate_regions if region not in prefer_regions]
    return result


def load_policy() -> dict:
    skill_md = SKILL_DIR / "SKILL.md"
    text = skill_md.read_text()
    proxy_names = [proxy["name"] for proxy in load_yaml_file(MAIN_YAML).get("proxies", []) if proxy.get("name")]
    available_regions = []
    for name in proxy_names:
        match = re.match(r"(.+)-\d+$", name)
        if match and match.group(1) not in available_regions:
            available_regions.append(match.group(1))

    policy = dict(DEFAULT_POLICY)
    match = re.search(r"^## Machine Policy Fallback\s*$.*?^```ya?ml\s*\n(.*?)^```", text, re.S | re.M)
    if match:
        raw = ruby_load_yaml_text(match.group(1)) or {}
        if isinstance(raw, dict):
            policy.update(raw)

    natural = parse_natural_language_policy(text, available_regions)
    policy.update(natural)
    for key in ("exclude_regions", "prefer_regions", "fallback_regions", "target_groups"):
        policy[key] = unique([str(item).strip() for item in policy.get(key, []) if str(item).strip()])
    for key in ("group_interval_seconds", "trigger_interval_seconds", "timeout_ms", "prefer_threshold_ms", "region_cooldown_seconds", "report_hour", "report_minute"):
        policy[key] = int(policy.get(key, DEFAULT_POLICY[key]))
    policy["mode"] = str(policy.get("mode", DEFAULT_POLICY["mode"])).strip() or DEFAULT_POLICY["mode"]
    policy["test_url"] = str(policy.get("test_url", DEFAULT_POLICY["test_url"])).strip()
    return policy


def find_profile_js() -> Path:
    for path in sorted(PROFILES_DIR.glob("*.js")):
        try:
            text = path.read_text()
        except OSError:
            continue
        if "自动测速" in text:
            return path
    raise SystemExit(f"Could not find a Clash Verge profile JS containing 自动测速 under {PROFILES_DIR}")


def region_matches(name: str, prefixes: list[str]) -> bool:
    return any(name.startswith(prefix) for prefix in prefixes)


def region_from_proxy_name(name: str) -> str | None:
    match = re.match(r"(.+)-\d+$", name)
    return match.group(1) if match else None


def collect_nodes(proxy_names: list[str], policy: dict) -> tuple[list[str], list[str], list[str]]:
    exclude = policy["exclude_regions"]
    prefer = policy["prefer_regions"]
    fallback = policy["fallback_regions"]
    candidate_nodes = [name for name in proxy_names if not region_matches(name, exclude)]
    preferred_nodes = [name for name in candidate_nodes if region_matches(name, prefer)]
    if fallback:
        fallback_nodes = [name for name in candidate_nodes if region_matches(name, fallback)]
    else:
        fallback_nodes = [name for name in candidate_nodes if name not in preferred_nodes]
    preferred_set = set(preferred_nodes)
    fallback_nodes = [name for name in fallback_nodes if name not in preferred_set]
    return candidate_nodes, preferred_nodes, fallback_nodes


def render_profile_js(policy: dict, preferred_nodes: list[str], fallback_nodes: list[str]) -> str:
    exclude_json = json.dumps(policy["exclude_regions"], ensure_ascii=False)
    prefer_json = json.dumps(policy["prefer_regions"], ensure_ascii=False)
    target_groups_json = json.dumps(policy["target_groups"], ensure_ascii=False)
    test_url_json = json.dumps(policy["test_url"], ensure_ascii=False)
    group_interval = policy["group_interval_seconds"]
    timeout_ms = policy["timeout_ms"]
    return f"""function main(config, profileName) {{
  const excludePrefixes = {exclude_json};
  const preferPrefixes = {prefer_json};
  const targetGroups = {target_groups_json};
  const testUrl = {test_url_json};
  const groupInterval = {group_interval};
  const testTimeout = {timeout_ms};
  const tolerance = 50;

  const allProxies = (config.proxies || []).map(p => p.name).filter(Boolean);
  const candidateNodes = allProxies.filter(name => !excludePrefixes.some(prefix => name.startsWith(prefix)));
  const preferredNodes = candidateNodes.filter(name => preferPrefixes.some(prefix => name.startsWith(prefix)));
  const fallbackNodes = candidateNodes.filter(name => !preferPrefixes.some(prefix => name.startsWith(prefix)));

  if (candidateNodes.length === 0) return config;

  const managedNames = new Set(["{AUTO_GROUP}", "{PREFER_GROUP}", "{FALLBACK_GROUP}"]);
  const existingGroups = (config["proxy-groups"] || []).filter(group => !managedNames.has(group.name));
  const managedGroups = [];
  const autoOptions = [];

  if (preferredNodes.length > 0) {{
    managedGroups.push({{
      name: "{PREFER_GROUP}",
      type: "url-test",
      proxies: preferredNodes,
      url: testUrl,
      interval: groupInterval,
      tolerance,
      lazy: true,
      timeout: testTimeout,
      "expected-status": 204,
    }});
    autoOptions.push("{PREFER_GROUP}");
  }}

  if (fallbackNodes.length > 0) {{
    managedGroups.push({{
      name: "{FALLBACK_GROUP}",
      type: "url-test",
      proxies: fallbackNodes,
      url: testUrl,
      interval: groupInterval,
      tolerance,
      lazy: true,
      timeout: testTimeout,
      "expected-status": 204,
    }});
    autoOptions.push("{FALLBACK_GROUP}");
  }}

  managedGroups.unshift({{
    name: "{AUTO_GROUP}",
    type: "select",
    proxies: autoOptions,
  }});

  config["proxy-groups"] = [...managedGroups, ...existingGroups];

  for (const group of config["proxy-groups"]) {{
    if (group.type === "select" && targetGroups.includes(group.name)) {{
      group.proxies = (group.proxies || []).filter(name => name !== "{AUTO_GROUP}");
      group.proxies.unshift("{AUTO_GROUP}");
    }}
  }}

  return config;
}}
"""


def update_profile_js(policy: dict, proxy_names: list[str]) -> tuple[bool, Path]:
    _, preferred_nodes, fallback_nodes = collect_nodes(proxy_names, policy)
    profile_js = find_profile_js()
    new_text = render_profile_js(policy, preferred_nodes, fallback_nodes)
    old_text = profile_js.read_text()
    if old_text == new_text:
        return False, profile_js
    profile_js.write_text(new_text)
    return True, profile_js


def build_managed_groups(policy: dict, proxy_names: list[str]) -> list[dict]:
    candidate_nodes, preferred_nodes, fallback_nodes = collect_nodes(proxy_names, policy)
    if not candidate_nodes:
        raise SystemExit("No candidate proxies remain after applying exclude_regions.")

    groups = []
    options = []
    if preferred_nodes:
        groups.append(
            {
                "name": PREFER_GROUP,
                "type": "url-test",
                "proxies": preferred_nodes,
                "url": policy["test_url"],
                "interval": policy["group_interval_seconds"],
                "lazy": True,
                "timeout": policy["timeout_ms"],
                "expected-status": 204,
                "tolerance": 50,
            }
        )
        options.append(PREFER_GROUP)
    if fallback_nodes:
        groups.append(
            {
                "name": FALLBACK_GROUP,
                "type": "url-test",
                "proxies": fallback_nodes,
                "url": policy["test_url"],
                "interval": policy["group_interval_seconds"],
                "lazy": True,
                "timeout": policy["timeout_ms"],
                "expected-status": 204,
                "tolerance": 50,
            }
        )
        options.append(FALLBACK_GROUP)

    groups.insert(0, {"name": AUTO_GROUP, "type": "select", "proxies": options})
    return groups


def update_main_yaml(policy: dict) -> bool:
    data = load_yaml_file(MAIN_YAML)
    proxy_names = [proxy["name"] for proxy in data.get("proxies", []) if proxy.get("name")]
    managed_groups = build_managed_groups(policy, proxy_names)
    proxy_groups = [group for group in data.get("proxy-groups", []) if group.get("name") not in MANAGED_GROUPS]
    for group in proxy_groups:
        if group.get("type") == "select" and group.get("name") in policy["target_groups"]:
            proxies = [name for name in group.get("proxies", []) if name != AUTO_GROUP]
            group["proxies"] = [AUTO_GROUP, *proxies]

    new_data = dict(data)
    new_data["proxy-groups"] = managed_groups + proxy_groups
    old_text = MAIN_YAML.read_text()
    proc = subprocess.run(
        [RUBY_BIN, "-ryaml", "-rjson", "-e", 'data = JSON.parse(STDIN.read); puts YAML.dump(data)'],
        input=json.dumps(new_data, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=True,
    )
    if old_text == proc.stdout:
        return False
    MAIN_YAML.write_text(proc.stdout)
    return True


def run_config_test() -> None:
    subprocess.run(
        [str(MIHOMO_BIN), "-t", "-d", str(BASE), "-f", str(MAIN_YAML)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def request(method: str, path: str, body: dict | None = None) -> tuple[int, str]:
    if not MIHOMO_SOCK.exists():
        raise RuntimeError(f"Mihomo socket not found: {MIHOMO_SOCK}")
    payload = b""
    headers = ""
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode()
        headers = "Content-Type: application/json\r\n" f"Content-Length: {len(payload)}\r\n"
    req = (f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n{headers}Connection: close\r\n\r\n").encode() + payload
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(str(MIHOMO_SOCK))
    sock.sendall(req)
    chunks = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
    sock.close()
    raw = b"".join(chunks).decode("utf-8", "replace")
    status_line, _, body_text = raw.partition("\r\n")
    status_code = int(status_line.split()[1])
    return status_code, body_text.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in body_text else ""


def reload_config() -> None:
    status, body = request("PUT", "/configs", {"path": str(MAIN_YAML)})
    if status >= 400:
        raise RuntimeError(f"Failed to reload config: HTTP {status} {body}")


def selector_set(group: str, target: str) -> None:
    path = f"/proxies/{urllib.parse.quote(group, safe='')}"
    status, body = request("PUT", path, {"name": target})
    if status >= 400:
        raise RuntimeError(f"Failed to set {group} -> {target}: HTTP {status} {body}")


def group_delay(group: str, policy: dict) -> dict[str, int]:
    path = (
        f"/group/{urllib.parse.quote(group, safe='')}/delay"
        f"?url={urllib.parse.quote(policy['test_url'], safe='')}"
        f"&timeout={policy['timeout_ms']}"
    )
    status, body = request("GET", path)
    if status >= 400:
        return {}
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(result, dict):
        return {}
    return {name: int(delay) for name, delay in result.items() if isinstance(delay, int)}


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def append_history(sample: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a") as handle:
        handle.write(json.dumps(sample, ensure_ascii=False) + "\n")


def prune_cooldowns(state: dict, now: int) -> None:
    cooldowns = state.get("region_cooldowns", {})
    if not isinstance(cooldowns, dict):
        state["region_cooldowns"] = {}
        return
    state["region_cooldowns"] = {
        str(region): int(until_ts)
        for region, until_ts in cooldowns.items()
        if isinstance(until_ts, int) and until_ts > now
    }


def active_cooldown_regions(state: dict, now: int) -> list[str]:
    prune_cooldowns(state, now)
    return unique(list(state.get("region_cooldowns", {}).keys()))


def successful_regions(results: dict[str, int]) -> set[str]:
    return {region for region in (region_from_proxy_name(name) for name in results) if region}


def update_region_cooldowns(
    state: dict,
    now: int,
    policy: dict,
    preferred_nodes: list[str],
    fallback_nodes: list[str],
    prefer_results: dict[str, int],
    fallback_results: dict[str, int],
) -> tuple[list[str], list[str]]:
    prune_cooldowns(state, now)
    cooldowns = state.setdefault("region_cooldowns", {})
    all_regions = {region_from_proxy_name(name) for name in preferred_nodes + fallback_nodes}
    success_regions = successful_regions(prefer_results) | successful_regions(fallback_results)
    cooled = []
    recovered = []
    for region in sorted(region for region in all_regions if region):
        if region in success_regions:
            if region in cooldowns:
                cooldowns.pop(region, None)
                recovered.append(region)
        else:
            if region not in cooldowns:
                cooled.append(region)
            cooldowns[region] = now + policy["region_cooldown_seconds"]
    prune_cooldowns(state, now)
    return cooled, recovered


def unlocked() -> bool:
    script = """
import plistlib
import subprocess
import sys

root = plistlib.loads(subprocess.check_output(["/usr/sbin/ioreg", "-n", "Root", "-d1", "-a"]))
locked = bool(root.get("IOConsoleLocked", False))
sys.exit(1 if locked else 0)
"""
    return subprocess.run(["/usr/bin/python3", "-c", script]).returncode == 0


def apply_policy(policy: dict, state: dict | None = None, now: int | None = None) -> dict:
    if state is None:
        state = {}
    if now is None:
        now = int(time.time())

    data = load_yaml_file(MAIN_YAML)
    proxy_names = [proxy["name"] for proxy in data.get("proxies", []) if proxy.get("name")]

    cooldown_regions = active_cooldown_regions(state, now)
    effective_policy = dict(policy)
    effective_policy["exclude_regions"] = unique(policy["exclude_regions"] + cooldown_regions)
    candidate_nodes, preferred_nodes, fallback_nodes = collect_nodes(proxy_names, effective_policy)
    if not candidate_nodes:
        effective_policy["exclude_regions"] = list(policy["exclude_regions"])
        candidate_nodes, preferred_nodes, fallback_nodes = collect_nodes(proxy_names, effective_policy)
        cooldown_regions = []

    changed_js, profile_js = update_profile_js(effective_policy, proxy_names)
    changed_yaml = update_main_yaml(effective_policy)
    if changed_js or changed_yaml:
        run_config_test()
        reload_config()

    for group in unique(policy["target_groups"] + ["节点组", "国外流量"]):
        if group in policy["target_groups"] or group in ("节点组", "国外流量"):
            try:
                selector_set(group, AUTO_GROUP)
            except RuntimeError:
                pass

    prefer_results = group_delay(PREFER_GROUP, effective_policy)
    fallback_results = group_delay(FALLBACK_GROUP, effective_policy)
    prefer_best = min(prefer_results.values()) if prefer_results else None
    fallback_best = min(fallback_results.values()) if fallback_results else None

    cooled, recovered = update_region_cooldowns(
        state, now, policy, preferred_nodes, fallback_nodes, prefer_results, fallback_results
    )
    cooldown_regions = active_cooldown_regions(state, now)

    chosen_group = None
    if policy["mode"] == "prefer_then_fallback":
        if prefer_results:
            chosen_group = PREFER_GROUP
        elif fallback_results:
            chosen_group = FALLBACK_GROUP
    elif policy["mode"] == "prefer_with_threshold":
        if prefer_results and fallback_results:
            if prefer_best is not None and fallback_best is not None and prefer_best <= fallback_best + policy["prefer_threshold_ms"]:
                chosen_group = PREFER_GROUP
            else:
                chosen_group = FALLBACK_GROUP
        elif prefer_results:
            chosen_group = PREFER_GROUP
        elif fallback_results:
            chosen_group = FALLBACK_GROUP
    else:
        candidates = []
        if prefer_best is not None:
            candidates.append((PREFER_GROUP, prefer_best))
        if fallback_best is not None:
            candidates.append((FALLBACK_GROUP, fallback_best))
        if candidates:
            chosen_group = min(candidates, key=lambda item: item[1])[0]

    if chosen_group:
        selector_set(AUTO_GROUP, chosen_group)

    chosen_results = prefer_results if chosen_group == PREFER_GROUP else fallback_results
    chosen_node = None
    chosen_delay = None
    if chosen_results:
        chosen_node, chosen_delay = min(chosen_results.items(), key=lambda item: item[1])

    return {
        "profile_js": str(profile_js),
        "config_changed": changed_js or changed_yaml,
        "chosen_group": chosen_group,
        "chosen_node": chosen_node,
        "chosen_delay_ms": chosen_delay,
        "prefer_best_ms": prefer_best,
        "fallback_best_ms": fallback_best,
        "prefer_threshold_ms": policy["prefer_threshold_ms"],
        "active_cooldown_regions": cooldown_regions,
        "cooled_regions_this_cycle": cooled,
        "recovered_regions_this_cycle": recovered,
        "prefer_count": len(prefer_results),
        "fallback_count": len(fallback_results),
    }


def main() -> int:
    args = parse_args()
    policy = load_policy()

    if args.print_policy:
        print(json.dumps(policy, ensure_ascii=False, indent=2))
        return 0

    if args.run_cycle:
        if not unlocked():
            if sys.stdout.isatty():
                print(json.dumps({"ok": True, "skipped": "locked"}, ensure_ascii=False))
            return 0

        state = load_state()
        now = int(time.time())
        last_run = int(state.get("last_run_ts", 0))
        interval = policy["trigger_interval_seconds"]
        if not args.force and last_run and now - last_run < interval:
            if sys.stdout.isatty():
                print(json.dumps({"ok": True, "skipped": "cadence", "next_in_seconds": interval - (now - last_run)}, ensure_ascii=False))
            return 0

        result = apply_policy(policy, state=state, now=now)
        state["last_run_ts"] = now
        state["last_result"] = result
        save_state(state)
        append_history(
            {
                "ts": now,
                "mode": policy["mode"],
                "chosen_group": result["chosen_group"],
                "chosen_node": result["chosen_node"],
                "chosen_delay_ms": result["chosen_delay_ms"],
                "prefer_best_ms": result["prefer_best_ms"],
                "fallback_best_ms": result["fallback_best_ms"],
                "prefer_threshold_ms": result["prefer_threshold_ms"],
                "active_cooldown_regions": result["active_cooldown_regions"],
                "cooled_regions_this_cycle": result["cooled_regions_this_cycle"],
                "recovered_regions_this_cycle": result["recovered_regions_this_cycle"],
                "prefer_count": result["prefer_count"],
                "fallback_count": result["fallback_count"],
            }
        )
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0

    result = apply_policy(policy, state=load_state(), now=int(time.time()))
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise
