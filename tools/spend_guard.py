#!/usr/bin/env python3
"""Spend guard, phase 1: a model-free check of OpenRouter and fal spend every 15 minutes.

CEO card Q-20261013-1958-bc81, option 1 ("สร้าง เริ่มที่กันใช้เงินเกินก่อน"); design: SomPong's
docs/reports/api-key-and-spend-guard-design-2026-10-14.md §3. Plan for phases 2-3 and the consumer table:
docs/plans/spend-guard-2026-10-14.md. Ops: docs/ops/spend-guard.md.

Every run reads the providers, appends one snapshot, and mails the CEO (email_ceo kind=alert, one mail per
run at most) when something NEW is wrong:
  - a cap: 50 / 80 / 100 % of an OpenRouter key's `limit`, of the prepaid balance the account had after its
    last top-up, or of a monthly cap the CFO sets in config/spend_guard.yaml;
  - a burn spike: the last hour's spend is >= 3x the hourly average of the last 7 days (and >= a floor);
  - runway: the balance lasts under 3 days at the 7-day average;
  - blind: a provider could not be read (API down, key refused, key missing). Never silent.
The same alert is not mailed again every 15 minutes: a cap fires once per crossing (100 % again after 24 h),
a spike and blind again after 6 h, runway again after 24 h. The hub refuses the same ref within 6 h too.

Pause. At 100 % of a key's limit or on a key's spike the guard disables that OpenRouter key through the
management API (PATCH /keys/{hash} disabled=true), verifies it, and raises a Run card on which the CEO types
1 = resume, 2 <USD> = new limit + resume, 3 revoke = delete for good. fal keys cannot be paused (revoke is
permanent), so fal is alert-only. config pause.mode `auto` keeps the guard alert-only for the first
`alert_only_hours` of live runs, logging "would pause <key>", then arms it; `alert_only` / `armed` force it.

Secrets: the unit runs this under `tools/infisical_setup.py run Agents-Core prod --path /spend-guard`, which
puts OPENROUTER_API_KEY_ADMIN (an OpenRouter management key) and FAL_BILLING_API_KEY_RO (fal preset BILLING)
into the environment. A value is never printed, logged, mailed or stored; neither is OpenRouter's `label`
field, which is a fragment of the key. Keys are named by their `name` on openrouter.ai and the first 8
characters of their hash (an id, not a credential).

Verbs:
    spend_guard.py timer                    # the unit: runs `check` under `infisical run`, no secret itself;
                                            #   mails "guard blind" when `check` never started
    spend_guard.py check [--dry-run]        # read, snapshot, alert, pause when armed (needs the keys in env)
    spend_guard.py keys                     # OpenRouter keys: name, hash8, limit, usage (consumer mapping)
    spend_guard.py status                   # offline: mode, open alerts, paused keys, last snapshot
    spend_guard.py test-alert [--dry-run]   # one alert mail marked ทดสอบ with the current readings
    spend_guard.py decide <hash>            # the pause card: reads 1 / 2 <USD> / 3 revoke from stdin
Exit: 0 ok · 1 a provider is blind (alerted) · 2 refused / bad input · 3 the alert could not be delivered.
"""
from __future__ import annotations

import argparse
import fcntl
import subprocess
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ask_run, email_ceo  # noqa: E402

# Data paths follow the live checkout (ORG_ROOT), not the pinned deploy worktree the code runs from.
DATA_ROOT = Path(os.environ.get("ORG_ROOT") or ROOT)
CONFIG = ROOT / "config" / "spend_guard.yaml"
UTC = timezone.utc
THAI = email_ceo.THAI

SESSION = "cto-spend-guard"   # the timer's own name in the hub's mail ledger (caps count per session)
ROLE = "cto"
OPENROUTER = "https://openrouter.ai/api/v1"
FAL = "https://api.fal.ai/v1"
# The legacy balance call. api.fal.ai answers a Vercel challenge (HTTP 403, HTML) from Contabo's IP
# even with no key (task-b1b251f0, 2026-10-14), so this one is read first.
FAL_REST = "https://rest.alpha.fal.ai"
LINKS = {"openrouter": "https://openrouter.ai/settings/credits",
         "openrouter-keys": "https://openrouter.ai/settings/keys",
         "fal": "https://fal.ai/dashboard/billing",
         "guard": "https://github.com/PASAKON/Agents-Core/blob/main/docs/ops/spend-guard.md"}
NAMES = {"openrouter": "OpenRouter", "fal": "fal.ai", "guard": "spend guard"}
# Where the keys live: `infisical_setup.py run` puts this folder's secrets in the check's environment.
INFISICAL = ("Agents-Core", "prod", "/spend-guard")
CHILD_TIMEOUT_S = 150
HTTP_TIMEOUT_S = 20
KEEP_DAYS = 35                # snapshots kept: 7 days of baseline + a month to date
EXIT_OK, EXIT_BLIND, EXIT_REFUSED, EXIT_UNDELIVERED = 0, 1, 2, 3

# Re-mail an alert that is still true after this long; None = once per crossing.
REPEAT = {"cap": None, "cap100": timedelta(hours=24), "spike": timedelta(hours=6),
          "runway": timedelta(hours=24), "blind": timedelta(hours=6), "pause": timedelta(hours=6),
          "paused": timedelta(hours=24)}
# Mail order, most urgent first: the title is the first line. pause = a pause that failed;
# paused = a key the guard paused that still waits for the CEO's answer.
PRIORITY = ("blind", "pause", "cap100", "spike", "paused", "runway", "cap")

DEFAULTS: dict[str, Any] = {
    "levels": [50, 80, 100],
    "spike": {"factor": 3.0, "min_usd_per_hour": 0.5, "window_min": [45, 90], "min_baseline_hours": 24},
    "runway": {"days": 3.0, "urgent_days": 1.0},
    "pause": {"mode": "auto", "alert_only_hours": 24, "resume_grace_hours": 24, "card_every_hours": 24,
              "unmapped_keys": "alert"},
    "providers": {
        "openrouter": {"key_env": "OPENROUTER_API_KEY_ADMIN", "account": "MoonieX",
                       "monthly_cap_usd": None, "keys": {}},
        "fal": {"key_env": "FAL_BILLING_API_KEY_RO", "account": "MoonieX", "monthly_cap_usd": None},
    },
}


# --------------------------------------------------------------------------- config + state

def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load_config(path: Path = CONFIG) -> dict:
    if not path.exists():
        return _merge(DEFAULTS, {})
    import yaml  # the venv has it; only the config read needs it
    return _merge(DEFAULTS, yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def data_dir() -> Path:
    return DATA_ROOT / "state" / "spend_guard"


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def thai_time(dt: datetime) -> str:
    return dt.astimezone(THAI).strftime("%d/%m %H:%M")


class Store:
    """state.json (alerts sent, cycles, paused keys) + snapshots.jsonl + events.jsonl, under state/spend_guard."""

    def __init__(self, root: Path):
        self.root = root
        self.state_path = root / "state.json"
        self.snap_path = root / "snapshots.jsonl"
        self.event_path = root / "events.jsonl"

    def load_state(self) -> dict:
        try:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            st = {}
        for k in ("alerts", "cycles", "paused", "resumed"):
            st.setdefault(k, {})
        return st

    def save_state(self, st: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def snapshots(self) -> list[dict]:
        rows = []
        try:
            with self.snap_path.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            pass
        return rows

    def append_snapshot(self, snap: dict, now: datetime) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        rows = self.snapshots()
        cut = now - timedelta(days=KEEP_DAYS)
        kept = [r for r in rows if (parse(r.get("at")) or now) >= cut]
        if len(kept) != len(rows):
            tmp = self.snap_path.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
            os.replace(tmp, self.snap_path)
        with self.snap_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")

    def event(self, now: datetime, what: str, **fields: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": iso(now), "what": what, **fields}, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- provider readers

class ProviderError(Exception):
    """A provider could not be read. The message never carries a key."""


Http = Callable[[str, str, dict, Any], tuple[int, Any]]


def urllib_http(method: str, url: str, headers: dict, body: Any = None) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={**headers, "Accept": "application/json",
                                          "User-Agent": "mooniex-spend-guard/1",
                                          **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            got = json.loads(e.read() or b"null")
        except ValueError:
            got = None
        return e.code, got
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ProviderError(f"network: {getattr(e, 'reason', e)}") from None


def _get_json(http: Http, url: str, headers: dict, what: str) -> Any:
    status, got = http("GET", url, headers, None)
    if status != 200 or not isinstance(got, dict):
        msg = ""
        if isinstance(got, dict):
            err = got.get("error")
            msg = (err.get("message") if isinstance(err, dict) else err) or got.get("detail") or ""
        raise ProviderError(f"{what} HTTP {status}{': ' + str(msg)[:120] if msg else ''}")
    return got


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def key_name(k: dict) -> str:
    """How a key is named everywhere the guard writes: its name on the provider page, never `label`."""
    name = str(k.get("name") or "").strip()
    return name or f"key-{str(k.get('hash', ''))[:8]}"


def read_openrouter(key: str, http: Http) -> dict:
    """Account credits + every key (incl. disabled). Needs a management key."""
    h = {"Authorization": f"Bearer {key}"}
    credits = (_get_json(http, f"{OPENROUTER}/credits", h, "credits") or {}).get("data") or {}
    total_credits, total_usage = _num(credits.get("total_credits")), _num(credits.get("total_usage"))
    if total_credits is None or total_usage is None:
        raise ProviderError("credits: no total_credits / total_usage in the answer")
    keys: dict[str, dict] = {}
    offset = 0
    for _ in range(50):
        page = (_get_json(http, f"{OPENROUTER}/keys?include_disabled=true&offset={offset}", h, "keys")
                or {}).get("data") or []
        if not page or all(str(k.get("hash") or "") in keys for k in page):
            break   # the end, or a provider that ignores offset
        for k in page:
            hsh = str(k.get("hash") or "")
            if not hsh:
                continue
            keys[hsh] = {"name": key_name(k), "disabled": bool(k.get("disabled")),
                         "limit": _num(k.get("limit")), "limit_remaining": _num(k.get("limit_remaining")),
                         "limit_reset": k.get("limit_reset"), "usage": _num(k.get("usage")) or 0.0,
                         "usage_daily": _num(k.get("usage_daily")), "usage_weekly": _num(k.get("usage_weekly")),
                         "usage_monthly": _num(k.get("usage_monthly")), "last_used_at": k.get("last_used_at")}
        offset += len(page)
    return {"ok": True, "total_credits": total_credits, "total_usage": total_usage,
            "balance": round(total_credits - total_usage, 6), "keys": keys}


def read_fal(key: str, http: Http) -> dict:
    """Prepaid balance. Needs a key with billing:usage:read (preset BILLING).

    `rest.alpha.fal.ai/billing/user_balance` answers a bare JSON number and is read first; the documented
    `api.fal.ai/v1/account/billing` is the fallback (challenged from Contabo, see FAL_REST)."""
    auth = {"Authorization": f"Key {key}"}
    try:
        status, got = http("GET", f"{FAL_REST}/billing/user_balance", auth, None)
        bal = _num(got) if status == 200 else None
        if bal is not None:
            return {"ok": True, "balance": bal, "currency": "USD", "account": ""}
        first = f"user_balance HTTP {status}" if status != 200 else "user_balance: not a number"
    except ProviderError as e:
        first = f"user_balance {e}"
    try:
        got = _get_json(http, f"{FAL}/account/billing?expand=credits", auth, "billing")
    except ProviderError as e:
        raise ProviderError(f"{first}; {e}") from None
    credits = got.get("credits") or {}
    bal = _num(credits.get("current_balance"))
    if bal is None:
        raise ProviderError("billing: no credits.current_balance in the answer")
    return {"ok": True, "balance": bal, "currency": credits.get("currency") or "USD",
            "account": got.get("username") or ""}


def set_key(key: str, hsh: str, body: dict, http: Http) -> dict:
    """PATCH one OpenRouter key; returns the key object the provider sent back."""
    status, got = http("PATCH", f"{OPENROUTER}/keys/{hsh}", {"Authorization": f"Bearer {key}"}, body)
    if status != 200 or not isinstance(got, dict):
        raise ProviderError(f"PATCH key {hsh[:8]} HTTP {status}")
    return got.get("data") or {}


def delete_key(key: str, hsh: str, http: Http) -> None:
    status, _ = http("DELETE", f"{OPENROUTER}/keys/{hsh}", {"Authorization": f"Bearer {key}"}, None)
    if status not in (200, 204):
        raise ProviderError(f"DELETE key {hsh[:8]} HTTP {status}")


def read_all(env: dict, cfg: dict, http: Http) -> dict:
    """{provider: reading}; a reading that failed is {"ok": False, "error": ...}."""
    out: dict[str, dict] = {}
    for prov, reader in (("openrouter", read_openrouter), ("fal", read_fal)):
        name = cfg["providers"][prov]["key_env"]
        key = (env.get(name) or "").strip()
        if not key:
            out[prov] = {"ok": False, "error": f"no {name} in the guard's environment (Infisical Agents-Core/prod/spend-guard)"}
            continue
        try:
            out[prov] = reader(key, http)
        except ProviderError as e:
            out[prov] = {"ok": False, "error": str(e).replace(key, "<redacted>")}
    return out


# --------------------------------------------------------------------------- the math (pure)

Series = list[tuple[datetime, float]]


def series(snaps: list[dict], prov: str, pick: Callable[[dict], float | None]) -> Series:
    out: Series = []
    for s in snaps:
        r = s.get(prov) or {}
        at = parse(s.get("at"))
        if at is None or not r.get("ok"):
            continue
        v = pick(r)
        if v is not None:
            out.append((at, v))
    return out


def hour_ago_point(s: Series, now: datetime, window_min: tuple[float, float]) -> tuple[datetime, float] | None:
    lo, hi = timedelta(minutes=window_min[0]), timedelta(minutes=window_min[1])
    cands = [(t, v) for t, v in s if lo <= now - t <= hi]
    return min(cands, key=lambda p: abs((now - p[0]) - timedelta(hours=1))) if cands else None


def last_hour_rate(s: Series, now: datetime, window_min=(45, 90)) -> float | None:
    """USD per hour over the last ~hour of a cumulative series whose last point is `now`."""
    if not s or s[-1][0] != now:
        return None
    old = hour_ago_point(s, now, window_min)
    if old is None:
        return None
    hours = (now - old[0]).total_seconds() / 3600
    spent = s[-1][1] - old[1]
    return spent / hours if spent >= 0 and hours > 0 else None   # < 0 = a reset or a new key: no rate


def baseline_rate(s: Series, now: datetime, window_min=(45, 90), min_hours: float = 24) -> tuple[float, str] | None:
    """Hourly average over up to the last 7 days, ending an hour ago so the spike is not in its own average."""
    end = hour_ago_point(s, now, window_min)
    if end is None:
        return None
    start_cut = now - timedelta(days=7, minutes=15)
    window = [(t, v) for t, v in s if start_cut <= t <= end[0]]
    if not window:
        return None
    start = window[0]
    hours = (end[0] - start[0]).total_seconds() / 3600
    if hours < min_hours or end[1] < start[1]:
        return None
    label = "เฉลี่ย 7 วัน" if hours >= 7 * 24 - 1 else f"เฉลี่ย {hours:.0f} ชม."
    return (end[1] - start[1]) / hours, label


def counter_baseline(now: datetime, weekly: float | None, monthly: float | None,
                     last_hour: float | None) -> tuple[float, str] | None:
    """Before the guard has 24 h of its own history: the provider's calendar-UTC counters, labelled estimate.
    This week's counter (Mon 00:00 UTC on, at most 7 days: the spec's window) when it spans >= 25 h,
    else this month's."""
    now = now.astimezone(UTC)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    for spent, start, word in ((weekly, week_start, "สัปดาห์"), (monthly, month_start(now), "เดือน")):
        hours = (now - start).total_seconds() / 3600
        if spent is None or hours < 25:
            continue
        return max(0.0, spent - (last_hour or 0.0)) / (hours - 1), f"ประมาณจากยอด{word}นี้"
    return None


def is_spike(rate: float | None, base: float | None, factor: float, floor: float) -> bool:
    return rate is not None and base is not None and rate >= floor and rate >= factor * base


def times(rate: float, base: float) -> str:
    return f"{rate / base:.1f} เท่าของ" if base > 0 else "จากเดิมเกือบ"


def runway_days(balance: float, per_hour: float | None) -> float | None:
    if per_hour is None or per_hour <= 0:
        return None
    return max(0.0, balance) / (per_hour * 24)


def level_reached(pct: float | None, levels: list[int]) -> int:
    return max([lv for lv in levels if pct is not None and pct >= lv], default=0)


def month_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# --------------------------------------------------------------------------- findings

@dataclass
class Finding:
    key: str            # dedup key, e.g. openrouter/key/<hash>/spike
    kind: str           # cap | cap100 | spike | runway | blind | pause
    level: int          # higher = worse: cap %, runway tier (1 = under 3 days, 2 = under 1 day), else 1
    line: str           # one Thai line for the mail; names the account and the key, never a value
    provider: str
    pause: str = ""     # an OpenRouter key hash to pause, when the finding asks for it
    link: str = ""


@dataclass
class Plan:
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def evaluate(readings: dict, snaps: list[dict], state: dict, cfg: dict, now: datetime) -> Plan:
    """Everything that is wrong right now. `snaps` already ends with this run's snapshot (at == now)."""
    plan = Plan()
    levels = sorted(int(x) for x in cfg["levels"])
    sp, rw = cfg["spike"], cfg["runway"]
    win = tuple(sp["window_min"])
    for prov in ("openrouter", "fal"):
        r = readings.get(prov) or {}
        pcfg = cfg["providers"][prov]
        acct = f"{NAMES[prov]} บัญชี {pcfg.get('account') or ''}".strip()
        if not r.get("ok"):
            plan.findings.append(Finding(f"{prov}/blind", "blind", 1,
                                         f"Spend guard มองไม่เห็น {NAMES[prov]}: {r.get('error', 'unknown')}",
                                         prov, link=LINKS[prov]))
            continue

        # account: cumulative spend series
        if prov == "openrouter":
            acc = series(snaps, prov, lambda x: _num(x.get("total_usage")))
        else:
            acc = series(snaps, prov, lambda x: _num(x.get("spend_cum")))
        hour = last_hour_rate(acc, now, win)
        base = baseline_rate(acc, now, win, sp["min_baseline_hours"])
        if base is None and prov == "openrouter":
            ks = r.get("keys", {}).values()
            weekly = sum(k.get("usage_weekly") or 0 for k in ks) if ks else None
            monthly = sum(k.get("usage_monthly") or 0 for k in ks) if ks else None
            base = counter_baseline(now, weekly, monthly, hour)
        bal = r["balance"]

        # cap: the prepaid balance since the last top-up
        cyc = state["cycles"].get(prov) or {}
        start_bal = _num(cyc.get("start_balance"))
        if start_bal and start_bal > 0:
            pct = (start_bal - bal) / start_bal * 100
            lv = level_reached(pct, levels)
            if lv:
                plan.findings.append(Finding(
                    f"{prov}/account/prepaid", "cap100" if lv >= 100 else "cap", lv,
                    f"{acct}: ใช้ไป {pct:.0f}% ของยอดตั้งต้น ${start_bal:.2f} (เหลือ ${bal:.2f})",
                    prov, link=LINKS[prov]))

        # cap: a monthly cap the CFO set
        cap = _num(pcfg.get("monthly_cap_usd"))
        if cap and cap > 0:
            mtd = None
            if prov == "openrouter":
                mtd = sum(k.get("usage_monthly") or 0 for k in r.get("keys", {}).values())
            else:
                first = [(t, v) for t, v in acc if t >= month_start(now)]
                if first and first[0][0] - month_start(now) <= timedelta(hours=1):
                    mtd = acc[-1][1] - first[0][1]
            if mtd is None:
                plan.notes.append(f"{prov}: monthly cap set but no month-to-date figure yet")
            else:
                pct = mtd / cap * 100
                lv = level_reached(pct, levels)
                if lv:
                    plan.findings.append(Finding(
                        f"{prov}/account/monthly", "cap100" if lv >= 100 else "cap", lv,
                        f"{acct}: เดือนนี้ใช้ ${mtd:.2f} = {pct:.0f}% ของเพดานเดือน ${cap:.2f}", prov,
                        link=LINKS[prov]))

        # spike: the whole account
        if is_spike(hour, base[0] if base else None, sp["factor"], sp["min_usd_per_hour"]):
            plan.findings.append(Finding(
                f"{prov}/account/spike", "spike", 1,
                f"{acct}: ใช้พุ่ง ${hour:.2f}/ชม. = {times(hour, base[0])} ${base[0]:.2f}/ชม. ({base[1]})",
                prov, link=LINKS[prov]))
        elif base is None:
            plan.notes.append(f"{prov}: spike baseline warming (under {sp['min_baseline_hours']} h of history)")

        # runway
        days = runway_days(bal, base[0] if base else None)
        if days is not None and days < rw["days"]:
            tier = 2 if days < rw["urgent_days"] else 1
            plan.findings.append(Finding(
                f"{prov}/account/runway", "runway", tier,
                f"{acct}: เหลือ ${bal:.2f} พอใช้อีก ~{days:.1f} วัน (ใช้ ~${base[0] * 24:.2f}/วัน, {base[1]})",
                prov, link=LINKS[prov]))

        if prov != "openrouter":
            continue

        # per OpenRouter key
        for hsh, k in sorted(r.get("keys", {}).items()):
            name = k["name"]
            tag = f"«{name}» ({hsh[:8]})"
            limit, rem = k.get("limit"), k.get("limit_remaining")
            if limit and limit > 0 and rem is not None:
                pct = (limit - rem) / limit * 100
                lv = level_reached(pct, levels)
                if lv:
                    plan.findings.append(Finding(
                        f"openrouter/key/{hsh}/cap", "cap100" if lv >= 100 else "cap", lv,
                        f"OpenRouter key {tag}: ใช้ไป {pct:.0f}% ของเพดาน ${limit:.2f} (เหลือ ${rem:.2f})",
                        prov, pause=hsh if lv >= 100 else "", link=LINKS["openrouter-keys"]))
            if k.get("disabled"):
                continue
            ks = series(snaps, prov, lambda x, h=hsh: _num(((x.get("keys") or {}).get(h) or {}).get("usage")))
            khour = last_hour_rate(ks, now, win)
            kbase = baseline_rate(ks, now, win, sp["min_baseline_hours"]) or counter_baseline(
                now, k.get("usage_weekly"), k.get("usage_monthly"), khour)
            if is_spike(khour, kbase[0] if kbase else None, sp["factor"], sp["min_usd_per_hour"]):
                plan.findings.append(Finding(
                    f"openrouter/key/{hsh}/spike", "spike", 1,
                    f"OpenRouter key {tag}: ใช้พุ่ง ${khour:.2f}/ชม. = {times(khour, kbase[0])} ${kbase[0]:.2f}/ชม. "
                    f"({kbase[1]})", prov, pause=hsh, link=LINKS["openrouter-keys"]))

        # a key the guard paused stays on the list until the CEO answers its card
        named = {f.pause for f in plan.findings if f.pause}
        for hsh, rec in sorted(state["paused"].items()):
            if hsh in named or hsh not in r.get("keys", {}):
                continue
            since = parse(rec.get("at"))
            plan.findings.append(Finding(
                f"openrouter/key/{hsh}/paused", "paused", 1,
                f"OpenRouter key «{rec.get('name') or hsh[:8]}» ({hsh[:8]}) ถูก spend guard พักไว้"
                f"{' ตั้งแต่ ' + thai_time(since) if since else ''}: รอ CEO ตัดสิน", prov, pause=hsh,
                link=LINKS["openrouter-keys"]))
    return plan


def reconcile_paused(readings: dict, state: dict, now: datetime, store: Store | None, dry_run: bool) -> None:
    """A key the guard paused that is enabled again (by hand on openrouter.ai) or gone is no longer paused."""
    r = readings.get("openrouter") or {}
    if not r.get("ok"):
        return
    for hsh, rec in list(state["paused"].items()):
        k = r["keys"].get(hsh)
        if k is not None and k.get("disabled"):
            continue
        state["paused"].pop(hsh)
        how = "deleted at the provider" if k is None else "enabled by hand on openrouter.ai"
        if k is not None:
            state["resumed"][hsh] = {"at": iso(now), "how": how}
        if store and not dry_run:
            store.event(now, "unpaused", key=rec.get("name"), hash8=hsh[:8], how=how)


def update_cycles(readings: dict, state: dict, now: datetime) -> None:
    """A new prepaid cycle starts at the first reading and after every top-up (credits up / balance up)."""
    for prov, r in readings.items():
        if not r.get("ok"):
            continue
        cyc = state["cycles"].get(prov)
        topped = False
        if cyc is None:
            topped = True
        elif prov == "openrouter":
            topped = (_num(cyc.get("total_credits")) or 0) < r["total_credits"] - 1e-9
        else:
            topped = r["balance"] > (_num(cyc.get("last_balance")) or 0) + 0.01
        if topped:
            state["cycles"][prov] = {"since": iso(now), "start_balance": r["balance"],
                                     "total_credits": r.get("total_credits"), "last_balance": r["balance"]}
        else:
            cyc["last_balance"] = r["balance"]


def snapshot(readings: dict, prev: list[dict], now: datetime) -> dict:
    """The row appended to snapshots.jsonl. fal has no spend counter, so spend_cum adds up balance drops."""
    snap: dict[str, Any] = {"at": iso(now)}
    for prov, r in readings.items():
        if not r.get("ok"):
            snap[prov] = {"ok": False, "error": r.get("error")}
            continue
        row = {k: v for k, v in r.items() if k != "account"}
        if prov == "fal":
            last = next((s["fal"] for s in reversed(prev) if (s.get("fal") or {}).get("ok")), None)
            cum = _num((last or {}).get("spend_cum")) or 0.0
            if last is not None:
                cum += max(0.0, (_num(last.get("balance")) or 0.0) - r["balance"])
            row["spend_cum"] = round(cum, 6)
        snap[prov] = row
    return snap


# --------------------------------------------------------------------------- dedup

def due(findings: list[Finding], state: dict, now: datetime) -> tuple[list[Finding], list[str]]:
    """(findings to mail now, alert keys that cleared). A finding is due when it is new, escalated, or old
    enough to repeat; everything else stays quiet."""
    alerts = state["alerts"]
    live = {f.key for f in findings}
    cleared = [k for k in alerts if k not in live]
    out = []
    for f in findings:
        rec = alerts.get(f.key)
        if rec is None or f.level > int(rec.get("level", 0)):
            out.append(f)
            continue
        if f.level < int(rec.get("level", 0)):
            rec["level"] = f.level          # a drop (a reset, a top-up) re-arms the higher level
            continue
        every = REPEAT.get(f.kind)
        last = parse(rec.get("last_sent"))
        if every and last and now - last >= every:
            out.append(f)
    return out, cleared


def mark_sent(findings: list[Finding], state: dict, now: datetime) -> None:
    for f in findings:
        state["alerts"][f.key] = {"level": f.level, "last_sent": iso(now), "kind": f.kind}


# --------------------------------------------------------------------------- pause

def pause_mode(cfg: dict, state: dict, now: datetime) -> tuple[bool, str]:
    """(armed?, why). auto = alert-only for the first alert_only_hours of live runs, then armed."""
    p = cfg["pause"]
    mode = str(p.get("mode") or "auto")
    if mode == "armed":
        return True, "armed (config)"
    if mode == "alert_only":
        return False, "alert-only (config)"
    first = parse(state.get("first_live_run"))
    if first is None:
        return False, "alert-only (first live run)"
    arm_at = first + timedelta(hours=float(p.get("alert_only_hours", 24)))
    if now >= arm_at:
        return True, f"armed since {iso(arm_at)}"
    return False, f"alert-only until {thai_time(arm_at)} TH"


def secrets_argv(*cmd: str) -> list[str]:
    """`infisical_setup.py run` over the guard's folder, then `cmd` with the keys in its environment."""
    project, env, path = INFISICAL
    return [sys.executable, str(ROOT / "tools" / "infisical_setup.py"), "run", project, env, "--path", path,
            "--", *cmd]


def card_command(hsh: str) -> str:
    """The exact bytes of the pause card: this same file, under the same Infisical folder, with ORG_ROOT."""
    return f"env ORG_ROOT={DATA_ROOT} " + " ".join(secrets_argv(sys.executable, str(Path(__file__).resolve()),
                                                               "decide", hsh))


def raise_pause_card(hsh: str, name: str, reason: str, consumers: list[str], env: dict,
                     create: Callable[[dict], dict]) -> dict:
    used = ", ".join(consumers) if consumers else "ยังไม่รู้ (ดู docs/plans/spend-guard-2026-10-14.md)"
    why = (f"Spend guard พักคีย์ OpenRouter «{name}» แล้ว: {reason}. ใช้โดย: {used}. "
           f"พิมพ์ 1 = เปิดคืน, 2 ตามด้วยจำนวนเงิน USD = ตั้งเพดานใหม่แล้วเปิด, 3 revoke = ลบถาวร. ไม่ทำอะไร = พักต่อ")
    return create({"host": "contabo", "command": card_command(hsh), "why": why[:430],
                   "expected": "resumed / limit set / revoked", "risk": "red", "timeout_s": 1800,
                   "expects_input": True, "session": SESSION, "role": ROLE})


def act_on_pauses(plan: Plan, readings: dict, state: dict, cfg: dict, env: dict, now: datetime,
                  armed: bool, http: Http, create: Callable[[dict], dict], store: Store | None,
                  dry_run: bool) -> list[Finding]:
    """Pause the keys the findings name (armed) or log 'would pause' (alert-only). Returns extra findings."""
    extra: list[Finding] = []
    keys = (readings.get("openrouter") or {}).get("keys") or {}
    policy = cfg["providers"]["openrouter"].get("keys") or {}
    grace = timedelta(hours=float(cfg["pause"].get("resume_grace_hours", 24)))
    card_every = timedelta(hours=float(cfg["pause"].get("card_every_hours", 12)))
    admin = (env.get(cfg["providers"]["openrouter"]["key_env"]) or "").strip()
    seen = set()
    for f in plan.findings:
        hsh = f.pause
        if not hsh or hsh in seen or hsh not in keys:
            continue
        seen.add(hsh)
        k = keys[hsh]
        name = k["name"]
        pol = policy.get(name) or {}
        consumers = list(pol.get("consumers") or [])
        if pol.get("pause") is False:
            f.line += " · คีย์นี้ตั้งไว้ว่าไม่พักอัตโนมัติ"
            continue
        resumed = parse((state["resumed"].get(hsh) or {}).get("at"))
        if resumed and now - resumed < grace:
            f.line += f" · CEO เพิ่งเปิดคืนเมื่อ {thai_time(resumed)} จึงยังไม่พักซ้ำ"
            continue
        paused = state["paused"].get(hsh)
        if paused:
            last_card = parse(paused.get("card_at"))
            if armed and not dry_run and (last_card is None or now - last_card >= card_every):
                try:
                    card = raise_pause_card(hsh, name, paused.get("reason", f.line), consumers, env, create)
                    paused.update(card=card.get("id"), card_url=card.get("url"), card_at=iso(now))
                except (ask_run.Refused, ask_run.HubError) as e:
                    paused["card_error"] = str(e)[:200]
            f.line += f" · พักอยู่ การ์ด {paused.get('card') or '-'}"
            f.link = paused.get("card_url") or f.link
            continue
        if k.get("disabled"):
            continue
        # A key nobody has mapped to its services is not paused: one value can serve LuNar, Option and
        # the autogen at once (docs/plans/spend-guard-2026-10-14.md §2). Map it, or set unmapped_keys: pause.
        mapped = bool(pol) or str(cfg["pause"].get("unmapped_keys") or "alert") == "pause"
        if not armed:
            tail = "" if mapped else " once its consumers are listed in config/spend_guard.yaml"
            print(f"would pause {name} ({hsh[:8]}): {f.kind}{tail}")
            if store and not dry_run:
                store.event(now, "would_pause", key=name, hash8=hsh[:8], kind=f.kind, mapped=mapped)
            f.line += " · จะพักคีย์นี้เมื่อเปิดใช้ (ตอนนี้โหมดเตือนอย่างเดียว)"
            continue
        if not mapped:
            f.line += " · ยังไม่ได้บันทึกว่าบริการไหนใช้คีย์นี้ จึงไม่พักอัตโนมัติ"
            continue
        if dry_run:
            print(f"[dry-run] would pause {name} ({hsh[:8]}): {f.kind}")
            continue
        try:
            got = set_key(admin, hsh, {"disabled": True}, http)
            if not got.get("disabled"):
                raise ProviderError("the provider did not confirm disabled=true")
        except ProviderError as e:
            extra.append(Finding(f"openrouter/key/{hsh}/pause", "pause", 1,
                                 f"พักคีย์ OpenRouter «{name}» ไม่สำเร็จ: {e}", "openrouter",
                                 link=LINKS["openrouter-keys"]))
            continue
        rec = {"name": name, "at": iso(now), "reason": f.line, "kind": f.kind}
        if store:
            store.event(now, "paused", key=name, hash8=hsh[:8], kind=f.kind)
        try:
            card = raise_pause_card(hsh, name, f.line, consumers, env, create)
            rec.update(card=card.get("id"), card_url=card.get("url"), card_at=iso(now))
            f.link = card.get("url") or f.link
        except (ask_run.Refused, ask_run.HubError) as e:
            rec["card_error"] = str(e)[:200]
        state["paused"][hsh] = rec
        f.line += f" · พักคีย์แล้ว การ์ด {rec.get('card') or 'ไม่ขึ้น: ' + rec.get('card_error', '')}"
    return extra


# --------------------------------------------------------------------------- delivery

def compose(findings: list[Finding], test: bool = False) -> dict:
    order = sorted(findings, key=lambda f: (PRIORITY.index(f.kind), -f.level))
    top = order[0]
    title = top.line if len(order) == 1 else f"{top.line} (+{len(order) - 1} เรื่อง)"
    if test:
        title = "ทดสอบ: " + title
    lines = [f"- {f.line}" for f in order]
    why = "\n".join(lines)
    if len(why) > 480:
        keep, n = [], 0
        for ln in lines:
            if n + len(ln) + 1 > 440:
                break
            keep.append(ln)
            n += len(ln) + 1
        why = "\n".join(keep) + f"\n(+{len(lines) - len(keep)} บรรทัด ใน state/spend_guard/events.jsonl)"
    if test:
        why = "นี่คืออีเมลทดสอบของ spend guard ไม่ต้องทำอะไร\n" + why
    need = ""
    if any(f.kind == "pause" or "การ์ด RUN-" in f.line for f in order):
        need = "เปิดการ์ด แล้วเลือก เปิดคืน / ตั้งเพดานใหม่ / ลบคีย์"
    elif top.kind == "runway":
        need = f"ตัดสินใจเติมเงิน {NAMES[top.provider]} หรือหยุดงานที่ใช้"
    elif top.kind == "blind":
        need = "ไม่ต้องทำอะไรตอนนี้ CTO ดูให้ ถ้ายังมองไม่เห็นนาน = ไม่มีใครเฝ้าเงินก้อนนี้"
    keyset = "|".join(sorted(f"{f.key}:{f.level}" for f in order))
    ref = "spend-" + ("test-" if test else "") + hashlib.sha1(keyset.encode()).hexdigest()[:10]
    card = next((f.link for f in order if "/run#" in f.link), "")      # a pause card beats a provider page
    out = {"title": title[:90], "why": why, "link": card or top.link or LINKS[top.provider], "ref": ref}
    if need:
        out["need"] = need
    return out


def deliver(fields: dict, env: dict, post: Callable[[dict], dict] | None, dry_run: bool,
            telegram: Callable[[str], dict] | None = None) -> dict:
    """email_ceo kind=alert (the hub buzzes his phone); Telegram too when the guard has a bot token.
    A hub "duplicate" (same ref within 6 h) counts as delivered: he has it. Any other refusal (a cap,
    a field) and HubError propagate, so the caller does not mark the alert sent and the next run retries."""
    body = email_ceo.build_payload(fields, kind="alert", session=SESSION, role=ROLE, env=env)
    post = post or (lambda b: email_ceo._post(b, dry_run=dry_run))
    result: dict[str, Any] = {"ref": body["ref"], "title": body["title"]}
    try:
        result["mail"] = post(body)
    except email_ceo.Refused as e:
        if "duplicate" not in str(e):
            raise
        result["mail"] = {"duplicate": str(e)}
    if telegram is not None and not dry_run:
        result["telegram"] = telegram(f"{body['title']}\n\n{fields['why']}\n{fields.get('link', '')}")
    else:
        result["telegram"] = {"ok": False, "reason": "off: no TELEGRAM_BOT_TOKEN / TELEGRAM_CEO_CHAT_ID in the guard env"}
    return result


def telegram_sender(env: dict) -> Callable[[str], dict] | None:
    if not (env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CEO_CHAT_ID")):
        return None
    from lib import telegram_out
    return telegram_out.send_to_ceo


# --------------------------------------------------------------------------- verbs

def check(*, env: dict, cfg: dict, store: Store, http: Http = urllib_http, now: datetime | None = None,
          dry_run: bool = False, post=None, create=None, telegram=None) -> tuple[int, dict]:
    now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    create = create or ask_run.mcp_ask
    state = store.load_state()
    prev = store.snapshots()
    readings = read_all(env, cfg, http)
    snap = snapshot(readings, prev, now)
    snaps = prev + [snap]
    if not dry_run and not state.get("first_live_run"):
        state["first_live_run"] = iso(now)
    update_cycles(readings, state, now)
    armed, mode = pause_mode(cfg, state, now)
    reconcile_paused(readings, state, now, store, dry_run)
    plan = evaluate(readings, snaps, state, cfg, now)
    plan.findings += act_on_pauses(plan, readings, state, cfg, env, now, armed, http, create,
                                   store, dry_run)
    send, cleared = due(plan.findings, state, now)
    blind = {p for p, r in readings.items() if not r.get("ok")}
    cleared = [k for k in cleared if k.split("/", 1)[0] not in blind]   # unseen is not fixed
    summary: dict[str, Any] = {
        "at": iso(now), "mode": mode, "dry_run": dry_run,
        "providers": {p: ({"balance": r.get("balance"), "keys": len(r.get("keys", {}))} if r.get("ok")
                          else {"blind": r.get("error")}) for p, r in readings.items()},
        "open": [f.line for f in plan.findings], "mail": [f.key for f in send], "notes": plan.notes}
    code = EXIT_BLIND if any(f.kind == "blind" for f in plan.findings) else EXIT_OK
    if send:
        try:
            summary["delivery"] = deliver(compose(send), env, post, dry_run,
                                          telegram if telegram is not None else telegram_sender(env))
            if not dry_run:
                mark_sent(send, state, now)
        except (email_ceo.Refused, email_ceo.HubError) as e:
            summary["delivery"] = {"error": str(e)}
            code = EXIT_UNDELIVERED   # not marked sent: the next run tries again
    for k in cleared:
        state["alerts"].pop(k, None)
    if not dry_run:
        store.append_snapshot(snap, now)
        store.save_state(state)
        store.event(now, "check", mode=mode, open=[f.key for f in plan.findings],
                    mailed=[f.key for f in send] if code != EXIT_UNDELIVERED else [], code=code)
    return code, summary


def decide(hsh: str, answer: str, *, env: dict, cfg: dict, store: Store, http: Http = urllib_http,
           now: datetime | None = None) -> str:
    """The pause card's answer: '1' resume · '2 <USD>' set limit + resume · '3 revoke' delete."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    state = store.load_state()
    rec = state["paused"].get(hsh)
    if rec is None:
        raise SystemExit(f"key {hsh[:8]} was not paused by the spend guard; nothing done")
    admin = (env.get(cfg["providers"]["openrouter"]["key_env"]) or "").strip()
    if not admin:
        raise SystemExit("no OpenRouter management key in the environment; nothing done")
    words = answer.strip().split()
    choice = words[0] if words else ""
    name = rec.get("name", hsh[:8])
    if choice == "1":
        set_key(admin, hsh, {"disabled": False}, http)
        msg = f"resumed {name}"
    elif choice == "2" and len(words) == 2:
        try:
            limit = float(words[1].lstrip("$"))
        except ValueError:
            raise SystemExit("2 needs an amount in USD, e.g. 2 15") from None
        if not 0 < limit <= 1000:
            raise SystemExit("the new limit must be between 0 and 1000 USD")
        set_key(admin, hsh, {"limit": limit, "disabled": False}, http)
        msg = f"limit of {name} set to ${limit:.2f} and resumed"
    elif choice == "3" and len(words) == 2 and words[1].lower() == "revoke":
        delete_key(admin, hsh, http)
        msg = f"revoked {name} for good"
    else:
        raise SystemExit("type 1, 2 <USD> or 3 revoke; nothing done")
    state["paused"].pop(hsh, None)
    if choice != "3":
        state["resumed"][hsh] = {"at": iso(now), "how": msg}
    store.save_state(state)
    store.event(now, "decided", key=name, hash8=hsh[:8], result=msg)
    return msg


def list_keys(env: dict, cfg: dict, http: Http = urllib_http) -> list[dict]:
    key = (env.get(cfg["providers"]["openrouter"]["key_env"]) or "").strip()
    if not key:
        raise SystemExit(f"no {cfg['providers']['openrouter']['key_env']} in the environment")
    r = read_openrouter(key, http)
    return [{"name": k["name"], "hash8": h[:8], "disabled": k["disabled"], "limit": k["limit"],
             "limit_remaining": k["limit_remaining"], "limit_reset": k["limit_reset"],
             "usage_daily": k["usage_daily"], "usage_weekly": k["usage_weekly"],
             "usage_monthly": k["usage_monthly"], "last_used_at": k["last_used_at"]}
            for h, k in sorted(r["keys"].items(), key=lambda kv: -(kv[1]["usage_monthly"] or 0))]


def test_alert(*, env: dict, cfg: dict, store: Store, http: Http = urllib_http, dry_run: bool = False,
               post=None, telegram=None, now: datetime | None = None) -> dict:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    readings = read_all(env, cfg, http)
    lines = []
    for prov, r in readings.items():
        if r.get("ok"):
            extra = f", {len(r.get('keys', {}))} keys" if prov == "openrouter" else ""
            lines.append(Finding(f"{prov}/test", "cap", 0, f"{NAMES[prov]}: อ่านได้ ยอดคงเหลือ ${r['balance']:.2f}{extra}",
                                 prov, link=LINKS[prov]))
        else:
            lines.append(Finding(f"{prov}/test", "blind", 1, f"{NAMES[prov]}: อ่านไม่ได้ ({r.get('error')})",
                                 prov, link=LINKS[prov]))
    fields = compose(lines, test=True)
    fields["ref"] = f"spend-test-{now:%Y%m%d%H%M}"
    return deliver(fields, env, post, dry_run, telegram if telegram is not None else telegram_sender(env))


def status(store: Store, cfg: dict, now: datetime | None = None) -> dict:
    now = (now or datetime.now(UTC)).astimezone(UTC)
    st = store.load_state()
    snaps = store.snapshots()
    armed, mode = pause_mode(cfg, st, now)
    last = snaps[-1] if snaps else {}
    return {"mode": mode, "first_live_run": st.get("first_live_run"), "open_alerts": st["alerts"],
            "paused": {h[:8]: {k: v for k, v in r.items() if k != "reason"} for h, r in st["paused"].items()},
            "cycles": st["cycles"], "snapshots": len(snaps), "last_at": last.get("at"),
            "last": {p: ({"balance": (last.get(p) or {}).get("balance")} if (last.get(p) or {}).get("ok")
                         else {"blind": (last.get(p) or {}).get("error")}) for p in ("openrouter", "fal") if p in last}}


def last_check_at(store: Store) -> datetime | None:
    try:
        with store.event_path.open(encoding="utf-8") as f:
            lines = f.readlines()[-50:]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("what") == "check":
            return parse(ev.get("at"))
    return None


def timer(*, store: Store, env: dict, run: Callable[[list[str]], int] | None = None, post=None,
          now: datetime | None = None) -> int:
    """What the systemd unit starts. This process holds no secret: it runs `check` under `infisical run`.
    When `check` never got to run (the Infisical folder is empty, Infisical refused or is down, the child
    crashed before reading anything) the guard is blind with nobody told, so this mails that itself."""
    start = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    run = run or (lambda argv: subprocess.run(argv, timeout=CHILD_TIMEOUT_S, check=False).returncode)
    argv = secrets_argv(sys.executable, str(Path(__file__).resolve()), "check")
    try:
        rc = run(argv)
    except (OSError, subprocess.SubprocessError) as e:
        rc, why = -1, f"{type(e).__name__}"
    else:
        why = f"exit {rc}"
    seen = last_check_at(store)
    if seen is not None and seen >= start:
        return rc
    store.root.mkdir(parents=True, exist_ok=True)
    with (store.root / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return rc   # a check is running after all
        state = store.load_state()
        hint = "โฟลเดอร์ Infisical ว่าง (ยังไม่มีกุญแจ)" if rc == 2 else "อ่านกุญแจจาก Infisical ไม่ได้ หรือตัวตรวจล้ม"
        f = Finding("guard/blind", "blind", 1,
                    f"Spend guard ไม่ได้เริ่มทำงาน ({why}): {hint} — ตอนนี้ไม่มีใครเฝ้า OpenRouter / fal",
                    "guard", link=LINKS["guard"])
        send, _ = due([f], state, start)
        code = EXIT_BLIND
        if send:
            try:
                deliver(compose(send), env, post, False, telegram_sender(env))
                mark_sent(send, state, start)
            except (email_ceo.Refused, email_ceo.HubError) as e:
                print(f"spend_guard: blind alert not delivered: {e}", file=sys.stderr)
                code = EXIT_UNDELIVERED
        store.save_state(state)
        store.event(start, "not_started", why=why, mailed=bool(send) and code == EXIT_BLIND)
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("timer")
    c = sub.add_parser("check")
    c.add_argument("--dry-run", action="store_true", help="read and print; no mail, no pause, no state")
    sub.add_parser("keys")
    sub.add_parser("status")
    t = sub.add_parser("test-alert")
    t.add_argument("--dry-run", action="store_true")
    d = sub.add_parser("decide")
    d.add_argument("hash")
    args = ap.parse_args(argv)
    cfg = load_config()
    store = Store(data_dir())
    env = dict(os.environ)
    if args.cmd == "timer":
        return timer(store=store, env=env)
    if args.cmd == "status":
        print(json.dumps(status(store, cfg), ensure_ascii=False, indent=1))
        return EXIT_OK
    if args.cmd == "keys":
        print(json.dumps(list_keys(env, cfg), ensure_ascii=False, indent=1))
        return EXIT_OK
    store.root.mkdir(parents=True, exist_ok=True)
    if args.cmd == "decide":
        print("1 = resume · 2 <USD> = new limit + resume · 3 revoke = delete for good", flush=True)
        line = sys.stdin.readline()
        with (store.root / ".lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)   # wait for a running check, then write state
            print(decide(args.hash, line, env=env, cfg=cfg, store=store))
        return EXIT_OK
    with (store.root / ".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("spend_guard: another run holds the lock; skipping")
            return EXIT_OK
        if args.cmd == "test-alert":
            try:
                print(json.dumps(test_alert(env=env, cfg=cfg, store=store, dry_run=args.dry_run),
                                 ensure_ascii=False, indent=1))
            except email_ceo.HubError as e:
                print(f"spend_guard: {e}", file=sys.stderr)
                return EXIT_UNDELIVERED
            except email_ceo.Refused as e:
                print(f"spend_guard: refused: {e}", file=sys.stderr)
                return EXIT_REFUSED
            return EXIT_OK
        code, summary = check(env=env, cfg=cfg, store=store, dry_run=args.dry_run)
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return code


if __name__ == "__main__":
    sys.exit(main())
