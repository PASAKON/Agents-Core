"""AI Provider Quota reader and normaliser (Phase 2, part 1).

Reads live usage data for Anthropic (Claude), OpenAI (Codex), and Google (agy),
normalising into unified Quota objects with weekly/daily remaining fractions (0..1).
"""
from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import glob
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config

PLANS_PATH = ROOT / "config" / "plans.yaml"
DEFAULT_HISTORY = Path(__file__).resolve().parents[1] / "state" / "reports" / "quota-history.jsonl"
SNAPSHOT_PATH = ROOT / "state" / "quota-snapshot.json"

RUNNER_TO_PROVIDER = {
    "claude": "anthropic",
    "agy": "google",
    "codex": "openai",
}
PROVIDER_TO_RUNNER = {v: k for k, v in RUNNER_TO_PROVIDER.items()}


@dataclass
class Quota:
    provider: str
    weekly_remaining: float | None = None
    daily_remaining: float | None = None
    weekly_resets_at: str | None = None
    daily_resets_at: str | None = None
    source: str = ""
    error: str | None = None


def load_plans(path: Path | str | None = None) -> dict:
    """Load configuration from config/plans.yaml or specified path."""
    p = Path(path) if path else PLANS_PATH
    if not p.exists():
        raise FileNotFoundError(f"Plans config not found at {p}")
    return yaml.safe_load(p.read_text()) or {}


def bucket_for(candidate: str, cfg: dict) -> str | None:
    """Return the first bucket name whose match prefix candidate starts with, or None."""
    buckets = cfg.get("buckets", {})
    if not isinstance(buckets, dict):
        return None
    for bucket_name, b_info in buckets.items():
        if isinstance(b_info, dict):
            matches = b_info.get("match", [])
            for m in matches:
                if candidate.startswith(m):
                    return bucket_name
    return None


def parse_claude(obj: dict | str, *, source: str = "claude") -> Quota:
    """Parse Claude usage JSON object.

    Input like:
      {"five_hour": {"utilization": 17.0, "resets_at": "2026-09-29T03:10:00+00:00"},
       "seven_day": {"utilization": 98.0, "resets_at": "2026-09-29T10:00:00+00:00"}}

    Utilization is percent used -> remaining = (100 - u) / 100.
    five_hour = daily slot, seven_day = weekly slot.
    """
    try:
        if isinstance(obj, str):
            obj = json.loads(obj)
        if not isinstance(obj, dict):
            raise ValueError(f"expected dict, got {type(obj).__name__}")

        daily_remaining = None
        daily_resets_at = None
        five_hour = obj.get("five_hour")
        if isinstance(five_hour, dict) and "utilization" in five_hour:
            u = float(five_hour["utilization"])
            daily_remaining = max(0.0, min(1.0, round((100.0 - u) / 100.0, 4)))
            daily_resets_at = five_hour.get("resets_at")

        weekly_remaining = None
        weekly_resets_at = None
        seven_day = obj.get("seven_day")
        if isinstance(seven_day, dict) and "utilization" in seven_day:
            u = float(seven_day["utilization"])
            weekly_remaining = max(0.0, min(1.0, round((100.0 - u) / 100.0, 4)))
            weekly_resets_at = seven_day.get("resets_at")

        if weekly_remaining is None and daily_remaining is None:
            raise ValueError("no five_hour or seven_day utilization found in claude usage data")

        return Quota(
            provider="claude",
            weekly_remaining=weekly_remaining,
            daily_remaining=daily_remaining,
            weekly_resets_at=weekly_resets_at,
            daily_resets_at=daily_resets_at,
            source=source,
            error=None,
        )
    except Exception as e:
        return Quota(
            provider="claude",
            weekly_remaining=None,
            daily_remaining=None,
            weekly_resets_at=None,
            daily_resets_at=None,
            source=source,
            error=str(e),
        )


def parse_codex(lines: Iterable[str] | str, *, source: str = "codex") -> Quota:
    """Parse Codex session rollout JSONL lines.

    Iterates JSONL lines; keeps the LAST object whose payload.rate_limits exists.
    Each of primary/secondary is:
      {"used_percent": 96.0, "window_minutes": 10080, "resets_at": 1790593204} or null.
    Label by window_minutes:
      >= 10080 -> weekly
      <= 1440  -> daily (300 min counts as daily)
    Never label by the key name. resets_at is epoch seconds -> ISO 8601 UTC.
    """
    try:
        if isinstance(lines, str):
            lines = lines.splitlines()

        last_rate_limits = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            if isinstance(data, dict):
                payload = data.get("payload")
                if isinstance(payload, dict):
                    rl = payload.get("rate_limits")
                    if rl is not None and isinstance(rl, dict):
                        last_rate_limits = rl

        if last_rate_limits is None:
            raise ValueError("no payload.rate_limits found in codex session data")

        weekly_remaining = None
        weekly_resets_at = None
        daily_remaining = None
        daily_resets_at = None

        for window_info in (last_rate_limits.get("primary"), last_rate_limits.get("secondary")):
            if not isinstance(window_info, dict):
                continue
            wm = window_info.get("window_minutes")
            up = window_info.get("used_percent")
            raw_reset = window_info.get("resets_at")

            if wm is None or up is None:
                continue

            rem = max(0.0, min(1.0, round((100.0 - float(up)) / 100.0, 4)))

            resets_at_iso = None
            if raw_reset is not None:
                if isinstance(raw_reset, (int, float)):
                    resets_at_iso = datetime.fromtimestamp(raw_reset, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                else:
                    resets_at_iso = str(raw_reset)

            if wm >= 10080:
                weekly_remaining = rem
                weekly_resets_at = resets_at_iso
            elif wm <= 1440:
                daily_remaining = rem
                daily_resets_at = resets_at_iso

        if weekly_remaining is None and daily_remaining is None:
            raise ValueError("no valid primary or secondary window found in rate_limits")

        return Quota(
            provider="codex",
            weekly_remaining=weekly_remaining,
            daily_remaining=daily_remaining,
            weekly_resets_at=weekly_resets_at,
            daily_resets_at=daily_resets_at,
            source=source,
            error=None,
        )
    except Exception as e:
        return Quota(
            provider="codex",
            weekly_remaining=None,
            daily_remaining=None,
            weekly_resets_at=None,
            daily_resets_at=None,
            source=source,
            error=str(e),
        )


def parse_agy(
    obj: dict | str,
    *,
    source: str = "agy",
    group: str = "Gemini Models",
) -> Quota:
    """Parse agy CLI /usage JSON output.

    Structure:
      obj["command"]["data"]["groups"][]
      each {"name": "Gemini Models" | "Claude and GPT models",
            "buckets": [{"window": "weekly" | "5h", "remaining_fraction": 1, "reset_time": "2026-10-06T00:05:38Z"}]}

    "5h" = daily slot.
    The returned Quota.provider is "agy-gemini" for "Gemini Models" and "agy-claude" for "Claude and GPT models".
    """
    if group == "Gemini Models":
        provider_name = "agy-gemini"
    elif group == "Claude and GPT models":
        provider_name = "agy-claude"
    else:
        provider_name = group

    try:
        if isinstance(obj, str):
            obj = json.loads(obj)
        if not isinstance(obj, dict):
            raise ValueError(f"expected dict, got {type(obj).__name__}")

        command = obj.get("command")
        if not isinstance(command, dict):
            raise ValueError("missing 'command' in agy output")
        data = command.get("data")
        if not isinstance(data, dict):
            raise ValueError("missing 'command.data' in agy output")
        groups = data.get("groups")
        if not isinstance(groups, list):
            raise ValueError("missing 'command.data.groups' list in agy output")

        target_group = None
        for g in groups:
            if isinstance(g, dict) and g.get("name") == group:
                target_group = g
                break

        if target_group is None:
            raise ValueError(f"'{group}' group not found in agy groups")

        buckets = target_group.get("buckets", [])
        if not isinstance(buckets, list):
            raise ValueError(f"missing 'buckets' in {group} group")

        weekly_remaining = None
        weekly_resets_at = None
        daily_remaining = None
        daily_resets_at = None

        for b in buckets:
            if not isinstance(b, dict):
                continue
            window = b.get("window")
            rem = b.get("remaining_fraction")
            reset = b.get("reset_time")

            rem_val = max(0.0, min(1.0, round(float(rem), 4))) if rem is not None else None

            if window == "weekly":
                weekly_remaining = rem_val
                weekly_resets_at = str(reset) if reset is not None else None
            elif window in ("5h", "daily"):
                daily_remaining = rem_val
                daily_resets_at = str(reset) if reset is not None else None

        if weekly_remaining is None and daily_remaining is None:
            raise ValueError(f"no weekly or daily buckets found in {group} group")

        return Quota(
            provider=provider_name,
            weekly_remaining=weekly_remaining,
            daily_remaining=daily_remaining,
            weekly_resets_at=weekly_resets_at,
            daily_resets_at=daily_resets_at,
            source=source,
            error=None,
        )
    except Exception as e:
        return Quota(
            provider=provider_name,
            weekly_remaining=None,
            daily_remaining=None,
            weekly_resets_at=None,
            daily_resets_at=None,
            source=source,
            error=str(e),
        )


def _parse_bonus_time(val: str | datetime | None, is_end: bool = False) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # If input was just YYYY-MM-DD (length 10) and is_end is True, cover entire end day
        if is_end and len(val) == 10:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt.astimezone(timezone.utc)
    return None


def apply_bonuses(quota: Quota, bonuses: list[dict], now: datetime | str | None = None) -> Quota:
    """Apply free grants / active surprise resets.

    While active the provider is treated as weekly_remaining = 1.0, with a note in source.
    """
    if now is None:
        current_time = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        current_time = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    else:
        current_time = _parse_bonus_time(str(now)) or datetime.now(timezone.utc)

    prov_lower = quota.provider.lower()
    matched_names = {
        prov_lower,
        RUNNER_TO_PROVIDER.get(prov_lower, "").lower(),
        PROVIDER_TO_RUNNER.get(prov_lower, "").lower(),
    } - {""}
    if prov_lower in ("agy-gemini", "agy-claude"):
        matched_names.update({"google", "agy"})

    for b in bonuses:
        if not isinstance(b, dict):
            continue
        b_prov = str(b.get("provider", "")).lower()
        if b_prov not in matched_names:
            continue

        b_from = _parse_bonus_time(b.get("from"), is_end=False)
        b_to = _parse_bonus_time(b.get("to"), is_end=True)

        if (b_from is None or b_from <= current_time) and (b_to is None or current_time <= b_to):
            quota.weekly_remaining = 1.0
            note = b.get("note") or "active bonus"
            if quota.source:
                quota.source = f"{quota.source} (bonus: {note})"
            else:
                quota.source = f"bonus: {note}"
            break

    return quota


# ---------------------------------------------------------------------------
# Thin fetchers (subprocess/ssh, not tested by unit tests)
# ---------------------------------------------------------------------------

def _ssh_target(alias: str | None) -> str | None:
    if not alias:
        return None
    try:
        from lib import config

        self_ssh = config.host(config.self_host()).get("ssh")
        if alias == self_ssh:
            return None
    except Exception:
        return alias
    return alias


def fetch_claude(cfg: dict | None = None) -> Quota:
    """Fetch Claude usage from configured source (default VPS usage.json)."""
    cfg = cfg or load_plans()
    source_cfg = cfg.get("quota_sources", {}).get("claude", {})
    ssh = _ssh_target(source_cfg.get("ssh"))
    path = source_cfg.get("path", "/opt/claude-usage-monitor/usage.json")
    src_label = f"{ssh}:{path}" if ssh else str(path)

    try:
        if ssh:
            cmd = ["ssh", ssh, f"cat {shlex.quote(str(path))}"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                raise RuntimeError(f"ssh exit {res.returncode}: {res.stderr.strip()[:200]}")
            raw = res.stdout
        else:
            raw = Path(path).read_text()
        return parse_claude(raw, source=src_label)
    except Exception as e:
        return Quota(
            provider="claude",
            weekly_remaining=None,
            daily_remaining=None,
            weekly_resets_at=None,
            daily_resets_at=None,
            source=src_label,
            error=str(e),
        )


def fetch_codex(cfg: dict | None = None) -> Quota:
    """Fetch Codex usage from configured source (newest rollout JSONL)."""
    cfg = cfg or load_plans()
    source_cfg = cfg.get("quota_sources", {}).get("codex", {})
    ssh = _ssh_target(source_cfg.get("ssh"))
    glob_pat = source_cfg.get("sessions_glob", "/root/.codex/sessions/*/*/*/rollout-*.jsonl")
    src_label = f"{ssh}:{glob_pat}" if ssh else str(glob_pat)

    try:
        if ssh:
            # Find the newest rollout file and cat it
            remote_cmd = f"ls -t {glob_pat} 2>/dev/null | head -n 1 | xargs -r cat"
            cmd = ["ssh", ssh, remote_cmd]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                raise RuntimeError(f"ssh exit {res.returncode}: {res.stderr.strip()[:200]}")
            raw = res.stdout
            if not raw.strip():
                raise RuntimeError("no codex session files found on remote host")
            return parse_codex(raw.splitlines(), source=src_label)
        else:
            matches = sorted(glob.glob(glob_pat), key=os.path.getmtime, reverse=True)
            if not matches:
                raise RuntimeError("no codex session files found matching glob")
            lines = Path(matches[0]).read_text().splitlines()
            return parse_codex(lines, source=str(matches[0]))
    except Exception as e:
        return Quota(
            provider="codex",
            weekly_remaining=None,
            daily_remaining=None,
            weekly_resets_at=None,
            daily_resets_at=None,
            source=src_label,
            error=str(e),
        )


def fetch_agy(cfg: dict | None = None) -> dict[str, Quota]:
    """Fetch agy usage via `agy -p /usage --output-format json`."""
    cfg = cfg or load_plans()
    source_cfg = cfg.get("quota_sources", {}).get("agy", {})
    ssh = _ssh_target(source_cfg.get("ssh"))
    cmd_list = list(source_cfg.get("cmd") or ["~/.local/bin/agy", "-p", "/usage", "--output-format", "json"])
    cmd_list[0] = os.path.expanduser(cmd_list[0])
    src_label = f"{ssh}:{shlex.join(cmd_list)}" if ssh else shlex.join(cmd_list)

    try:
        if ssh:
            full_cmd = ["ssh", ssh, shlex.join(cmd_list)]
        else:
            full_cmd = cmd_list
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            raise RuntimeError(f"agy exit {res.returncode}: {res.stderr.strip()[:200]}")
        return {
            "agy-gemini": parse_agy(res.stdout, source=src_label, group="Gemini Models"),
            "agy-claude": parse_agy(res.stdout, source=src_label, group="Claude and GPT models"),
        }
    except Exception as e:
        err = str(e)
        return {
            "agy-gemini": Quota(
                provider="agy-gemini",
                weekly_remaining=None,
                daily_remaining=None,
                weekly_resets_at=None,
                daily_resets_at=None,
                source=src_label,
                error=err,
            ),
            "agy-claude": Quota(
                provider="agy-claude",
                weekly_remaining=None,
                daily_remaining=None,
                weekly_resets_at=None,
                daily_resets_at=None,
                source=src_label,
                error=err,
            ),
        }


def fetch_all_quotas(cfg: dict | None = None, now: datetime | str | None = None) -> dict[str, Quota]:
    """Fetch quotas for all configured buckets, applying active bonuses."""
    cfg = cfg or load_plans()
    bonuses = cfg.get("bonuses", [])

    agy_quotas = fetch_agy(cfg)
    quotas = {
        "claude": apply_bonuses(fetch_claude(cfg), bonuses, now),
        "codex": apply_bonuses(fetch_codex(cfg), bonuses, now),
        "agy-gemini": apply_bonuses(agy_quotas["agy-gemini"], bonuses, now),
        "agy-claude": apply_bonuses(agy_quotas["agy-claude"], bonuses, now),
    }
    return quotas


def record_snapshot(quotas: dict[str, Quota], path: Path | str, now: datetime | None = None) -> int:
    """Append one JSON line per provider to path. Returns the number of lines written."""
    if now is None:
        now_dt = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now_dt = now.replace(tzinfo=timezone.utc)
    else:
        now_dt = now.astimezone(timezone.utc)

    ts = now_dt.isoformat(timespec="seconds")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines_written = 0
    with open(p, "a", encoding="utf-8") as f:
        for provider, q in quotas.items():
            line_data = {
                "ts": ts,
                "provider": provider,
                "weekly_remaining": q.weekly_remaining,
                "daily_remaining": q.daily_remaining,
                "weekly_resets_at": q.weekly_resets_at,
                "daily_resets_at": q.daily_resets_at,
                "source": q.source,
                "error": q.error,
            }
            f.write(json.dumps(line_data, ensure_ascii=False, sort_keys=True) + "\n")
            lines_written += 1

    return lines_written


def write_snapshot(
    quotas: dict[str, Quota],
    path: Path | str | None = None,
    now: datetime | None = None,
) -> Path:
    """Write quota snapshot to JSON file atomically."""
    p = Path(path) if path is not None else SNAPSHOT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)

    if now is None:
        now_dt = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now_dt = now.replace(tzinfo=timezone.utc)
    else:
        now_dt = now.astimezone(timezone.utc)

    ts = now_dt.isoformat(timespec="seconds")
    payload = {
        "ts": ts,
        "buckets": {name: asdict(q) for name, q in quotas.items()},
    }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=p.parent, encoding="utf-8", delete=False) as f:
            temp_path = Path(f.name)
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temp_path, p)
    except Exception:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise

    return p


def read_snapshot(
    path: Path | str | None = None,
    *,
    max_age_s: int = 900,
    now: datetime | None = None,
) -> dict[str, Quota] | None:
    """Read quota snapshot from JSON file if valid and not older than max_age_s."""
    p = Path(path) if path is not None else SNAPSHOT_PATH
    if not p.is_file():
        return None

    try:
        raw_text = p.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if "ts" not in data or "buckets" not in data:
        return None

    ts_str = data["ts"]
    if not isinstance(ts_str, str):
        return None

    try:
        ts_dt = datetime.fromisoformat(ts_str)
    except Exception:
        return None

    if ts_dt.tzinfo is None:
        ts_dt = ts_dt.replace(tzinfo=timezone.utc)

    if now is None:
        now_dt = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now_dt = now.replace(tzinfo=timezone.utc)
    else:
        now_dt = now.astimezone(timezone.utc)

    age_s = (now_dt - ts_dt).total_seconds()
    if age_s > max_age_s:
        return None

    buckets_data = data["buckets"]
    if not isinstance(buckets_data, dict):
        return None

    quotas: dict[str, Quota] = {}
    try:
        for name, b_dict in buckets_data.items():
            if not isinstance(b_dict, dict):
                return None
            quotas[name] = Quota(**b_dict)
    except Exception:
        return None

    return quotas


def main() -> None:
    parser = argparse.ArgumentParser(description="Read quota across AI providers")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--config", help="Path to plans.yaml")
    parser.add_argument(
        "--record",
        nargs="?",
        const=str(DEFAULT_HISTORY),
        default=None,
        help="Record snapshot to history file (default: %(const)s)",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Fetch quotas, write snapshot, append history",
    )
    args = parser.parse_args()

    cfg = load_plans(args.config)
    quotas = fetch_all_quotas(cfg)

    if args.snapshot:
        now_dt = datetime.now(timezone.utc)
        snap_path = write_snapshot(quotas, now=now_dt)
        record_snapshot(quotas, DEFAULT_HISTORY, now=now_dt)
        ts = now_dt.isoformat(timespec="seconds")
        print(f"snapshot: {snap_path} {len(quotas)} buckets {ts}")
        return

    if args.record is not None:
        n = record_snapshot(quotas, args.record)
        print(f"recorded {n} lines -> {args.record}", file=sys.stderr)

    if args.json:
        data = {k: asdict(v) for k, v in quotas.items()}
        print(json.dumps(data, indent=2))
    else:
        for name, q in quotas.items():
            if q.error:
                print(f"{name}: error: {q.error}")
            else:
                w_str = f"{q.weekly_remaining * 100:.1f}%" if q.weekly_remaining is not None else "unknown"
                d_str = f"{q.daily_remaining * 100:.1f}%" if q.daily_remaining is not None else "unknown"
                w_reset = f" (resets {q.weekly_resets_at})" if q.weekly_resets_at else ""
                d_reset = f" (resets {q.daily_resets_at})" if q.daily_resets_at else ""
                src = f" [{q.source}]" if q.source else ""
                print(f"{name}: weekly {w_str}{w_reset}, daily {d_str}{d_reset}{src}")


if __name__ == "__main__":
    main()
