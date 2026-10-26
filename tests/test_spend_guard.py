"""tools/spend_guard.py — the 15-minute OpenRouter + fal spend check.

What must hold: a cap alerts at 50 / 80 / 100 % and once per crossing; a spike is >= 3x the 7-day hourly
average and over a floor; runway under 3 days alerts and escalates under 1; the same alert is not mailed
every 15 minutes; a provider that cannot be read alerts "blind" (and so does a guard that never started);
alert-only logs "would pause" and touches nothing, armed pauses the key, verifies it and raises a card;
--dry-run writes and pauses nothing; no key value and no OpenRouter `label` lands in a mail, a card, a
file or stdout. Fakes stand in for OpenRouter, fal, the hub's mail API and the Run Inbox; nothing here
reaches the network. The CFO's 13 Oct reading (LungNote e3c6efab) is the first fixture.

Run: .venv/bin/python -m pytest tests/test_spend_guard.py
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import ceo_text
from tools import email_ceo
from tools import spend_guard as sg

UTC = timezone.utc
REPO = Path(__file__).resolve().parent.parent
OR_KEY = "test-mgmt-value-not-real-0000aaaa"     # stands in for the management key's value
FAL_KEY = "test-fal-value-not-real-1111bbbb"
LABEL = "LABEL-FRAGMENT-a1b...f9e"                # OpenRouter's `label` is a piece of the key
ENV = {"ORG_MACHINE": "contabo", "OPENROUTER_API_KEY_ADMIN": OR_KEY, "FAL_BILLING_API_KEY_RO": FAL_KEY}
H1 = "3f9c2a7be1d04c55" + "0" * 48               # key hashes: ids, not credentials
H2 = "77aa01c3d9e84f10" + "1" * 48
CFO_AT = datetime(2026, 10, 13, 17, 10, tzinfo=UTC)   # 2026-10-13T19:10:00+0200, balance.jsonl


def cfo_keys() -> dict:
    return {
        H1: {"hash": H1, "name": "jev-secretary", "label": LABEL, "disabled": False, "limit": 10,
             "limit_remaining": 6.928690891, "limit_reset": None, "usage": 162.771914565,
             "usage_daily": 3.071309109, "usage_weekly": 12.737050645, "usage_monthly": 28.940619116},
        H2: {"hash": H2, "name": "lunar-claudeflow", "label": "LABEL-FRAGMENT-2", "disabled": False,
             "limit": None, "limit_remaining": None, "limit_reset": None, "usage": 0.0, "usage_daily": 0.0,
             "usage_weekly": 0.0, "usage_monthly": 0.0},
    }


class Providers:
    """OpenRouter + fal over one fake `http(method, url, headers, body)`."""

    def __init__(self, *, credits=180.0, usage=173.254011928, keys=None, fal=20.0):
        self.credits, self.usage, self.fal = credits, usage, fal
        self.keys = cfo_keys() if keys is None else keys
        self.down: set[str] = set()
        self.patch_status = 200
        self.calls: list[tuple] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, body))
        if "openrouter.ai" in url:
            if "openrouter" in self.down:
                raise sg.ProviderError("network: timed out")
            assert headers["Authorization"] == f"Bearer {OR_KEY}"
            if url.endswith("/credits"):
                return 200, {"data": {"total_credits": self.credits, "total_usage": self.usage}}
            if "/keys?" in url:
                offset = int(url.rsplit("offset=", 1)[1])
                return 200, {"data": [dict(k) for k in self.keys.values()][offset:offset + 100]}
            hsh = url.rsplit("/", 1)[1]
            if method == "PATCH":
                if self.patch_status != 200:
                    return self.patch_status, {"error": {"message": "boom"}}
                self.keys[hsh].update(body)
                return 200, {"data": dict(self.keys[hsh])}
            if method == "DELETE":
                self.keys.pop(hsh)
                return 200, {"deleted": True}
        if "rest.alpha.fal.ai" in url:
            if "fal" in self.down or "fal-rest" in self.down:
                return 503, {"detail": "service unavailable"}
            assert headers["Authorization"] == f"Key {FAL_KEY}"
            return 200, self.fal                      # a bare JSON number
        if "api.fal.ai" in url:
            if "fal-challenge" in self.down:
                return 403, None                      # Vercel challenge page: HTML, no JSON
            if "fal" in self.down:
                return 503, {"detail": "service unavailable"}
            assert headers["Authorization"] == f"Key {FAL_KEY}"
            return 200, {"username": "mooniex", "credits": {"current_balance": self.fal, "currency": "USD"}}
        raise AssertionError(f"unexpected call {method} {url}")

    def writes(self):
        return [c for c in self.calls if c[0] in ("PATCH", "DELETE")]


class Hub:
    """The mail API and the Run Inbox."""

    def __init__(self):
        self.mails: list[dict] = []
        self.cards: list[dict] = []
        self.fail: Exception | None = None

    def post(self, body):
        if self.fail is not None:
            raise self.fail
        self.mails.append(body)
        return {"ok": True, "id": f"mail-{len(self.mails)}"}

    def create(self, args):
        self.cards.append(args)
        n = len(self.cards)
        return {"id": f"RUN-TEST-{n}", "url": f"https://example.invalid/run#RUN-TEST-{n}"}


MAPPED = {"providers": {"openrouter": {"keys": {"jev-secretary": {"consumers": ["SomPong route decision"]}}}}}


def config(**over) -> dict:
    cfg = copy.deepcopy(sg.load_config(REPO / "config" / "spend_guard.yaml"))
    return sg._merge(cfg, over)


@pytest.fixture
def store(tmp_path):
    return sg.Store(tmp_path / "spend_guard")


def check(store, fake, hub, now, cfg=None, dry_run=False, env=None):
    return sg.check(env=env or ENV, cfg=cfg or config(), store=store, http=fake, now=now, dry_run=dry_run,
                    post=hub.post, create=hub.create, telegram=None)


def seed(store, now, *, hours=8 * 24, rate=0.1, last_hour=None, credits=1000.0, step_min=15):
    """History every 15 min up to `now` (exclusive) at `rate` USD/h on key H1, `last_hour` in the last hour.
    Returns a Providers whose readings at `now` continue that history."""
    rows, t = [], now - timedelta(hours=hours)
    ku, au = 100.0, 150.0
    while t < now:
        rows.append({"at": sg.iso(t), "openrouter": {
            "ok": True, "total_credits": credits, "total_usage": au, "balance": credits - au,
            "keys": {H1: {"name": "jev-secretary", "usage": ku, "disabled": False}}},
            "fal": {"ok": True, "balance": 20.0, "spend_cum": 0.0}})
        r = last_hour if (last_hour is not None and now - t <= timedelta(hours=1)) else rate
        ku += r * step_min / 60
        au += r * step_min / 60
        t += timedelta(minutes=step_min)
    store.root.mkdir(parents=True, exist_ok=True)
    store.snap_path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    keys = {H1: {"hash": H1, "name": "jev-secretary", "label": LABEL, "disabled": False, "limit": None,
                 "limit_remaining": None, "limit_reset": None, "usage": ku, "usage_daily": None,
                 "usage_weekly": None, "usage_monthly": None}}
    return Providers(credits=credits, usage=au, keys=keys, fal=20.0)


# --------------------------------------------------------------------------- the CFO's reading

def test_cfo_fixture_runway_fires_and_the_key_cap_does_not(store, capsys):
    fake, hub = Providers(), Hub()
    code, summary = check(store, fake, hub, CFO_AT)
    assert code == sg.EXIT_OK
    assert summary["providers"]["openrouter"]["balance"] == pytest.approx(6.746, abs=0.001)
    # 30.7 % of the $10 key limit: under 50, so no cap line for the key
    assert not any("/cap" in k for k in summary["mail"])
    assert summary["mail"] == ["openrouter/account/runway"]
    [mail] = hub.mails
    assert mail["kind"] == "alert" and mail["session"] == sg.SESSION and mail["role"] == "cto"
    # this week's counter: $12.74 over 40 h = ~$7.6/day (the CFO measured ~$7.4) -> ~0.9 days
    assert "~0.9 วัน" in mail["title"] and "OpenRouter" in mail["title"] and "$6.75" in mail["title"]
    assert "จากยอดสัปดาห์นี้" in mail["why"]
    assert mail["need"].startswith("ตัดสินใจเติมเงิน OpenRouter")
    assert hub.cards == [] and fake.writes() == []


def test_counter_baseline_uses_this_week_then_the_month():
    per_hour, label = sg.counter_baseline(CFO_AT, 12.737050645, 28.940619116, None)
    assert per_hour * 24 == pytest.approx(7.61, abs=0.02) and "สัปดาห์" in label
    monday_morning = datetime(2026, 10, 12, 10, 0, tzinfo=UTC)      # 10 h into the week
    per_hour, label = sg.counter_baseline(monday_morning, 1.0, 20.0, None)
    assert "เดือน" in label and per_hour == pytest.approx(20.0 / (11 * 24 + 10 - 1))
    assert sg.counter_baseline(datetime(2026, 10, 1, 5, tzinfo=UTC), None, 1.0, None) is None


# --------------------------------------------------------------------------- thresholds

def test_level_reached():
    assert [sg.level_reached(p, [50, 80, 100]) for p in (None, 0, 49.9, 50, 79, 80, 99.9, 100, 140)] == \
        [0, 0, 0, 50, 50, 80, 80, 100, 100]


def key_with(remaining, limit=10.0):
    keys = cfo_keys()
    keys[H1].update(limit=limit, limit_remaining=remaining)
    return keys


def test_key_cap_alerts_once_per_level_and_100_would_pause(store, capsys):
    hub, now = Hub(), CFO_AT
    cfg = config(runway={"days": 0.0})            # runway out of the way: this test is about the cap
    steps = [(5.0, ["openrouter/key/%s/cap" % H1]),   # 50 %
             (4.0, []),                               # 60 %: same level, quiet
             (1.9, ["openrouter/key/%s/cap" % H1]),   # 81 %
             (1.5, []),
             (0.0, ["openrouter/key/%s/cap" % H1])]   # 100 %
    for remaining, mailed in steps:
        fake = Providers(keys=key_with(remaining))
        code, summary = check(store, fake, hub, now, cfg=cfg)
        assert summary["mail"] == mailed, remaining
        now += timedelta(minutes=15)
    assert [m["title"].split("ใช้ไป ")[1][:4] for m in hub.mails] == ["50% ", "81% ", "100%"]
    # first live day = alert-only: the 100 % key is named, logged, and not touched
    assert "would pause jev-secretary (3f9c2a7b)" in capsys.readouterr().out
    assert "จะพักคีย์นี้เมื่อเปิดใช้" in hub.mails[-1]["why"]
    assert fake.writes() == [] and hub.cards == []
    events = [json.loads(x) for x in store.event_path.read_text().splitlines()]
    assert {"what": "would_pause", "key": "jev-secretary", "hash8": "3f9c2a7b"}.items() <= \
        next(e for e in events if e["what"] == "would_pause").items()


def test_a_reset_rearms_the_cap_levels(store):
    hub, cfg = Hub(), config(runway={"days": 0.0})
    check(store, Providers(keys=key_with(4.0)), hub, CFO_AT, cfg=cfg)                 # 60 % -> mail
    check(store, Providers(keys=key_with(10.0)), hub, CFO_AT + timedelta(minutes=15), cfg=cfg)  # reset
    check(store, Providers(keys=key_with(4.5)), hub, CFO_AT + timedelta(minutes=30), cfg=cfg)   # 55 %
    assert len(hub.mails) == 2


def test_a_100_percent_key_reminds_after_24_hours(store):
    hub, cfg = Hub(), config(runway={"days": 0.0}, pause={"mode": "alert_only"})
    for minutes in (0, 15, 60 * 23, 60 * 24 + 5):
        check(store, Providers(keys=key_with(0.0)), hub, CFO_AT + timedelta(minutes=minutes), cfg=cfg)
    assert len(hub.mails) == 2


def test_prepaid_balance_cap_and_a_top_up_starts_a_new_cycle(store):
    hub, cfg = Hub(), config(runway={"days": 0.0})
    keys = cfo_keys()
    for k in keys.values():
        k.update(usage_weekly=0.0, usage_monthly=0.0)
    check(store, Providers(credits=100, usage=80, keys=keys), hub, CFO_AT, cfg=cfg)      # start $20
    assert hub.mails == []
    check(store, Providers(credits=100, usage=91, keys=keys), hub, CFO_AT + timedelta(minutes=15), cfg=cfg)
    assert "55% ของยอดตั้งต้น $20.00" in hub.mails[-1]["title"]
    check(store, Providers(credits=150, usage=91, keys=keys), hub, CFO_AT + timedelta(minutes=30), cfg=cfg)
    st = store.load_state()
    assert st["cycles"]["openrouter"]["start_balance"] == 59 and "openrouter/account/prepaid" not in st["alerts"]


def test_monthly_cap_from_config(store):
    hub = Hub()
    check(store, Providers(), hub, CFO_AT, cfg=config(runway={"days": 0.0},
                                                      providers={"openrouter": {"monthly_cap_usd": 50}}))
    assert "เดือนนี้ใช้ $28.94 = 58% ของเพดานเดือน $50.00" in hub.mails[0]["title"]


def test_fal_spend_is_the_sum_of_balance_drops_and_its_cap_counts_from_the_top_up(store):
    hub, cfg = Hub(), config(runway={"days": 0.0})
    for i, bal in enumerate((20.0, 18.0, 17.0, 50.0, 9.0)):
        check(store, Providers(fal=bal), hub, CFO_AT + timedelta(minutes=15 * i), cfg=cfg)
    cum = [s["fal"]["spend_cum"] for s in store.snapshots()]
    assert cum == [0.0, 2.0, 3.0, 3.0, 44.0]
    assert any("fal.ai" in m["title"] and "82% ของยอดตั้งต้น $50.00" in m["title"] for m in hub.mails)


# --------------------------------------------------------------------------- spike + runway math

def test_rate_and_baseline_math():
    now = CFO_AT
    s = [(now - timedelta(minutes=15 * i), 100.0 - 0.025 * i) for i in range(8 * 24 * 4, -1, -1)]  # $0.10/h
    assert sg.last_hour_rate(s, now) == pytest.approx(0.1)
    base, label = sg.baseline_rate(s, now)
    assert base == pytest.approx(0.1) and label == "เฉลี่ย 7 วัน"
    assert sg.last_hour_rate(s[:-1], now) is None                     # no reading at `now`
    assert sg.last_hour_rate([(now - timedelta(hours=1), 5.0), (now, 1.0)], now) is None   # a reset
    assert sg.baseline_rate(s[-60:], now) is None                     # 14 h of history: under 24
    short = s[-(30 * 4 + 1):]                                          # 30 h
    assert sg.baseline_rate(short, now)[1] == "เฉลี่ย 29 ชม."


@pytest.mark.parametrize("rate, base, spike", [
    (0.60, 0.10, True),     # 6x and over the floor
    (0.30, 0.10, False),    # 3x but under the $0.50/h floor
    (0.60, 0.25, False),    # over the floor but 2.4x
    (0.75, 0.25, True),     # exactly 3x
    (None, 0.10, False),
])
def test_spike_needs_3x_and_the_floor(rate, base, spike):
    assert sg.is_spike(rate, base, 3.0, 0.5) is spike


def test_runway_math():
    assert sg.runway_days(6.746, 7.4 / 24) == pytest.approx(0.912, abs=0.001)
    assert sg.runway_days(10, 0) is None and sg.runway_days(-1, 1) == 0


def test_runway_escalates_under_one_day(store):
    hub, cfg = Hub(), config()
    keys = cfo_keys()
    keys[H1]["usage_weekly"] = 2.0 / 24 * (41 + 10 / 60 - 1)    # exactly $2.00/day since Monday 00:00 UTC
    check(store, Providers(credits=180, usage=176, keys=keys), hub, CFO_AT, cfg=cfg)        # $4 = 2 days
    check(store, Providers(credits=180, usage=176.2, keys=keys), hub, CFO_AT + timedelta(minutes=15), cfg=cfg)
    check(store, Providers(credits=180, usage=178.5, keys=keys), hub, CFO_AT + timedelta(minutes=30), cfg=cfg)
    assert len(hub.mails) == 2                                   # 1.9 days is the same tier: quiet
    assert "~2.0 วัน" in hub.mails[0]["title"] and "~0.8 วัน" in hub.mails[1]["title"]


def test_a_key_spike_alert_only_on_the_first_day(store, capsys):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    hub = Hub()
    code, summary = check(store, fake, hub, CFO_AT)
    assert set(summary["mail"]) == {f"openrouter/key/{H1}/spike", "openrouter/account/spike"}
    [mail] = hub.mails
    assert "ใช้พุ่ง $0.60/ชม. = 6.0 เท่าของ $0.10/ชม. (เฉลี่ย 7 วัน)" in mail["why"]
    assert "would pause jev-secretary" in capsys.readouterr().out
    assert fake.writes() == [] and hub.cards == []


def test_no_spike_under_the_floor(store):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.4)
    hub = Hub()
    check(store, fake, hub, CFO_AT)
    assert hub.mails == []


# --------------------------------------------------------------------------- pause: armed, dry-run, policy

def test_armed_pauses_verifies_and_raises_the_card(store):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    hub = Hub()
    code, _ = check(store, fake, hub, CFO_AT, cfg=config(pause={"mode": "armed"}, **MAPPED))
    assert code == sg.EXIT_OK
    assert fake.writes() == [("PATCH", f"{sg.OPENROUTER}/keys/{H1}", {"disabled": True})]
    assert fake.keys[H1]["disabled"] is True
    [card] = hub.cards
    assert card["expects_input"] is True and card["risk"] == "red" and card["timeout_s"] == 1800
    assert card["command"].endswith(f"decide {H1}") and "--path /spend-guard" in card["command"]
    assert "ORG_ROOT=" in card["command"] and len(card["why"]) <= 430
    assert "1 เปิดคืน" in card["why"] and "jev-secretary" in card["why"]
    [mail] = hub.mails
    assert "พักคีย์แล้ว การ์ด RUN-TEST-1" in mail["why"] and mail["link"].endswith("#RUN-TEST-1")
    assert mail["need"].startswith("เปิดการ์ด")
    assert store.load_state()["paused"][H1]["card"] == "RUN-TEST-1"


def test_armed_never_pauses_a_key_nobody_mapped(store, capsys):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    hub = Hub()
    check(store, fake, hub, CFO_AT, cfg=config(pause={"mode": "armed"}))
    assert fake.writes() == [] and hub.cards == []
    assert "ไม่พัก: ยังไม่ระบุว่าใครใช้คีย์นี้" in hub.mails[0]["why"]
    fake2 = seed(sg.Store(store.root.parent / "b"), CFO_AT, rate=0.1, last_hour=0.6)
    check(sg.Store(store.root.parent / "b"), fake2, Hub(), CFO_AT)
    assert "would pause jev-secretary (3f9c2a7b): spike once its consumers are listed" in capsys.readouterr().out


def test_auto_mode_arms_after_the_first_live_day():
    cfg = config()
    st = {"first_live_run": sg.iso(CFO_AT)}
    assert sg.pause_mode(cfg, st, CFO_AT + timedelta(hours=23))[0] is False
    assert sg.pause_mode(cfg, st, CFO_AT + timedelta(hours=24))[0] is True
    assert sg.pause_mode(cfg, {}, CFO_AT)[0] is False
    assert sg.pause_mode(config(pause={"mode": "alert_only"}), st, CFO_AT + timedelta(days=30))[0] is False


def test_dry_run_reads_but_pauses_mails_nothing_and_writes_nothing(store, capsys):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    before = store.snap_path.read_text()
    hub = Hub()
    calls = []
    code, summary = sg.check(env=ENV, cfg=config(pause={"mode": "armed"}, **MAPPED), store=store, http=fake, now=CFO_AT,
                             dry_run=True, post=lambda b: calls.append(b) or {"dry_run": True},
                             create=hub.create, telegram=None)
    assert fake.writes() == [] and hub.cards == []
    assert "[dry-run] would pause jev-secretary" in capsys.readouterr().out
    assert store.snap_path.read_text() == before
    assert not store.state_path.exists() and not store.event_path.exists()
    assert summary["dry_run"] is True and len(calls) == 1      # the hub's own ?dry_run=1 check


def test_a_key_marked_no_pause_and_a_fresh_resume_are_left_alone(store):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    hub = Hub()
    cfg = config(pause={"mode": "armed"},
                 providers={"openrouter": {"keys": {"jev-secretary": {"pause": False, "consumers": ["SomPong"]}}}})
    check(store, fake, hub, CFO_AT, cfg=cfg)
    assert fake.writes() == [] and "ตั้งไว้ว่าไม่พักอัตโนมัติ" in hub.mails[0]["why"]

    st = store.load_state()
    st["alerts"].clear()
    st["resumed"][H1] = {"at": sg.iso(CFO_AT - timedelta(hours=2)), "how": "resumed jev-secretary"}
    store.save_state(st)
    check(store, fake, hub, CFO_AT + timedelta(minutes=1), cfg=config(pause={"mode": "armed"}))
    assert fake.writes() == [] and "เพิ่งเปิดคืน" in hub.mails[-1]["why"]


def test_a_failed_pause_is_its_own_alert(store):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    fake.patch_status = 500
    hub = Hub()
    check(store, fake, hub, CFO_AT, cfg=config(pause={"mode": "armed"}, **MAPPED))
    assert hub.mails[0]["title"].startswith('พักคีย์ OpenRouter "jev-secretary" ไม่สำเร็จ: PATCH key 3f9c2a7b HTTP 500')
    assert hub.cards == [] and store.load_state()["paused"] == {}


def test_a_paused_key_is_reminded_and_re_carded_daily_until_answered(store):
    hub = Hub()
    keys = cfo_keys()
    keys[H1]["disabled"] = True
    st = store.load_state()
    st["paused"][H1] = {"name": "jev-secretary", "at": sg.iso(CFO_AT - timedelta(hours=25)), "reason": "spike",
                        "card": "RUN-OLD", "card_at": sg.iso(CFO_AT - timedelta(hours=25))}
    st["first_live_run"] = sg.iso(CFO_AT - timedelta(days=3))
    store.save_state(st)
    cfg = config(runway={"days": 0.0})
    check(store, Providers(keys=keys), hub, CFO_AT, cfg=cfg)
    assert [c["command"].split()[-1] for c in hub.cards] == [H1]
    assert "ถูกพักไว้" in hub.mails[0]["title"] and "RUN-TEST-1" in hub.mails[0]["why"]
    check(store, Providers(keys=keys), hub, CFO_AT + timedelta(minutes=15), cfg=cfg)
    assert len(hub.cards) == 1 and len(hub.mails) == 1


def test_a_key_enabled_by_hand_is_no_longer_paused(store):
    st = store.load_state()
    st["paused"][H1] = {"name": "jev-secretary", "at": sg.iso(CFO_AT), "card_at": sg.iso(CFO_AT)}
    store.save_state(st)
    check(store, Providers(), Hub(), CFO_AT + timedelta(minutes=15), cfg=config(runway={"days": 0.0}))
    st = store.load_state()
    assert st["paused"] == {} and st["resumed"][H1]["how"] == "enabled by hand on openrouter.ai"


# --------------------------------------------------------------------------- decide (the card's answer)

@pytest.mark.parametrize("answer, write", [
    ("1\n", ("PATCH", {"disabled": False})),
    ("2 15\n", ("PATCH", {"limit": 15.0, "disabled": False})),
    ("2 $7.5\n", ("PATCH", {"limit": 7.5, "disabled": False})),
    ("3 revoke\n", ("DELETE", None)),
])
def test_decide(store, answer, write):
    fake = Providers()
    st = store.load_state()
    st["paused"][H1] = {"name": "jev-secretary", "at": sg.iso(CFO_AT)}
    store.save_state(st)
    msg = sg.decide(H1, answer, env=ENV, cfg=config(), store=store, http=fake, now=CFO_AT)
    assert [(m, b) for m, _, b in fake.writes()] == [write]
    st = store.load_state()
    assert st["paused"] == {} and ("jev-secretary" in msg)
    assert (H1 in st["resumed"]) is (write[0] == "PATCH")


@pytest.mark.parametrize("answer", ["", "4", "2", "2 abc", "2 5000", "3", "3 yes", "revoke"])
def test_decide_refuses_anything_else_and_does_nothing(store, answer):
    fake = Providers()
    st = store.load_state()
    st["paused"][H1] = {"name": "jev-secretary", "at": sg.iso(CFO_AT)}
    store.save_state(st)
    with pytest.raises(SystemExit):
        sg.decide(H1, answer, env=ENV, cfg=config(), store=store, http=fake, now=CFO_AT)
    assert fake.writes() == [] and H1 in store.load_state()["paused"]


def test_decide_only_touches_keys_the_guard_paused(store):
    fake = Providers()
    with pytest.raises(SystemExit, match="not paused by the spend guard"):
        sg.decide(H2, "1", env=ENV, cfg=config(), store=store, http=fake, now=CFO_AT)
    assert fake.writes() == []


# --------------------------------------------------------------------------- blind: never silent

def test_a_provider_that_is_down_alerts_blind_and_repeats_after_6_hours(store):
    fake, hub = Providers(), Hub()
    fake.down.add("openrouter")
    cfg = config()
    code, summary = check(store, fake, hub, CFO_AT, cfg=cfg)
    assert code == sg.EXIT_BLIND
    assert hub.mails[0]["title"].startswith("Spend guard มองไม่เห็น OpenRouter: network: timed out")
    assert summary["providers"]["fal"]["balance"] == 20.0          # fal still read
    check(store, fake, hub, CFO_AT + timedelta(minutes=15), cfg=cfg)
    assert len(hub.mails) == 1
    check(store, fake, hub, CFO_AT + timedelta(hours=6, minutes=1), cfg=cfg)
    assert len(hub.mails) == 2


def test_fal_http_error_and_a_missing_key_are_blind(store):
    fake, hub = Providers(), Hub()
    fake.down.add("fal")
    env = {k: v for k, v in ENV.items() if k != "OPENROUTER_API_KEY_ADMIN"}
    code, summary = check(store, fake, hub, CFO_AT, env=env)
    assert code == sg.EXIT_BLIND
    assert "no OPENROUTER_API_KEY_ADMIN" in summary["providers"]["openrouter"]["blind"]
    assert summary["providers"]["fal"]["blind"] == ("fal balance unknown: user_balance HTTP 503; "
                                                    "billing HTTP 503: service unavailable")
    assert {"openrouter/blind", "fal/blind"} <= set(summary["mail"])


def test_a_blind_run_does_not_clear_the_other_alerts(store):
    fake, hub = Providers(), Hub()
    check(store, fake, hub, CFO_AT)                                    # runway mailed
    fake.down.add("openrouter")
    check(store, fake, hub, CFO_AT + timedelta(minutes=15))           # blind mailed
    fake.down.clear()
    check(store, fake, hub, CFO_AT + timedelta(minutes=30))           # back: runway is not news
    alerts = store.load_state()["alerts"]
    assert len(hub.mails) == 2 and "openrouter/blind" not in alerts and "openrouter/account/runway" in alerts


def test_the_timer_mails_blind_when_check_never_started(store):
    hub = Hub()
    argvs = []

    def infisical_refused(argv):
        argvs.append(argv)
        return 2                                                       # empty folder: check never ran

    code = sg.timer(store=store, env={"ORG_MACHINE": "contabo"}, run=infisical_refused, post=hub.post, now=CFO_AT)
    assert code == sg.EXIT_BLIND
    assert argvs[0][2:9] == ["run", "Agents-Core", "prod", "--path", "/spend-guard", "--", argvs[0][0]]
    assert argvs[0][-1] == "check"
    assert hub.mails[0]["title"].startswith("Spend guard ไม่ได้เริ่มทำงาน (exit 2): โฟลเดอร์ Infisical ว่าง")
    sg.timer(store=store, env={"ORG_MACHINE": "contabo"}, run=infisical_refused, post=hub.post,
             now=CFO_AT + timedelta(minutes=15))
    assert len(hub.mails) == 1                                         # not every 15 minutes


def test_the_timer_stays_quiet_when_check_ran(store):
    hub, fake = Hub(), Providers()

    def ran(argv):
        check(store, fake, hub, CFO_AT + timedelta(seconds=5))
        return 0

    assert sg.timer(store=store, env=ENV, run=ran, post=hub.post, now=CFO_AT) == 0
    assert all("ไม่ได้เริ่ม" not in m["title"] for m in hub.mails)


# --------------------------------------------------------------------------- delivery

def test_hub_down_is_retried_next_run(store):
    fake, hub = Providers(), Hub()
    hub.fail = email_ceo.HubError("hub unreachable", transient=True)
    code, _ = check(store, fake, hub, CFO_AT)
    assert code == sg.EXIT_UNDELIVERED and store.load_state()["alerts"] == {}
    hub.fail = None
    check(store, fake, hub, CFO_AT + timedelta(minutes=15))
    assert len(hub.mails) == 1


def test_a_hub_duplicate_counts_as_delivered_another_refusal_does_not(store, tmp_path):
    fake, hub = Providers(), Hub()
    hub.fail = email_ceo.Refused("hub refused (409: duplicate; kind=alert)")
    code, _ = check(store, fake, hub, CFO_AT)
    assert code == sg.EXIT_OK and "openrouter/account/runway" in store.load_state()["alerts"]

    other = sg.Store(tmp_path / "other")
    hub.fail = email_ceo.Refused("hub refused (429: cap; cap=20)")
    code, _ = check(other, fake, hub, CFO_AT)
    assert code == sg.EXIT_UNDELIVERED and other.load_state()["alerts"] == {}


def test_compose_orders_by_urgency_and_the_ref_follows_the_alert_set():
    a = sg.Finding("fal/account/runway", "runway", 3, "fal runway", "fal")
    b = sg.Finding("openrouter/blind", "blind", 1, "openrouter blind", "openrouter", link=sg.LINKS["openrouter"])
    c = sg.Finding("x/cap", "cap", 50, "cap 50", "openrouter")
    got = sg.compose([a, c, b])
    assert got["title"] == "openrouter blind (+2 เรื่อง)"
    # blind needs no action yet, so `need` takes a line: the list leaves out the one the title names
    assert got["why"].splitlines() == ["- fal runway", "- cap 50"]
    assert sg.compose([c, b, a])["ref"] == got["ref"]
    assert sg.compose([a, b, sg.Finding("x/cap", "cap", 80, "cap 80", "openrouter")])["ref"] != got["ref"]
    many = [sg.Finding(f"k{i}", "cap", 50, "x" * 60, "fal") for i in range(12)]
    assert len(sg.compose(many)["why"]) <= 500


def test_telegram_is_off_without_a_token_in_the_guard_env():
    assert sg.telegram_sender(ENV) is None
    assert sg.telegram_sender({**ENV, "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CEO_CHAT_ID": "1"}) is not None


# --------------------------------------------------------------------------- secrets

def test_no_key_value_and_no_label_anywhere(store, capsys):
    fake = seed(store, CFO_AT, rate=0.1, last_hour=0.6)
    hub = Hub()
    check(store, fake, hub, CFO_AT, cfg=config(pause={"mode": "armed"}, **MAPPED))
    sg.decide(H1, "2 15", env=ENV, cfg=config(), store=store, http=fake, now=CFO_AT + timedelta(minutes=5))
    check(store, fake, hub, CFO_AT + timedelta(minutes=15))
    out = capsys.readouterr()
    blobs = [json.dumps(hub.mails, ensure_ascii=False), json.dumps(hub.cards, ensure_ascii=False),
             out.out, out.err] + [p.read_text(encoding="utf-8") for p in store.root.iterdir() if p.is_file()]
    for blob in blobs:
        for secret in (OR_KEY, FAL_KEY, LABEL, "LABEL-FRAGMENT"):
            assert secret not in blob
    assert hub.mails and hub.cards


def test_a_provider_error_never_echoes_the_key(store):
    def leaky(method, url, headers, body):
        raise sg.ProviderError(f"bad auth header {headers['Authorization']}")
    got = sg.read_all(ENV, config(), leaky)
    assert OR_KEY not in got["openrouter"]["error"] and FAL_KEY not in got["fal"]["error"]
    assert "<redacted>" in got["openrouter"]["error"]


def test_keys_listing_stops_when_the_provider_ignores_offset():
    fake = Providers()
    calls = []

    def same_page(method, url, headers, body):
        calls.append(url)
        if url.endswith("/credits"):
            return 200, {"data": {"total_credits": 1, "total_usage": 0}}
        return 200, {"data": list(fake.keys.values())}
    got = sg.read_openrouter(OR_KEY, same_page)
    assert len(got["keys"]) == 2 and len(calls) == 3
    assert all("label" not in k for k in got["keys"].values())


# --------------------------------------------------------------------------- the unit files

def test_the_units():
    svc = (REPO / "deploy/systemd/spend-guard.service").read_text(encoding="utf-8")
    tmr = (REPO / "deploy/systemd/spend-guard.timer").read_text(encoding="utf-8")
    exec_start = re.search(r"^ExecStart=(.+)$", svc, re.M).group(1).split()
    assert exec_start[1].endswith("/worktrees/spend-guard-deploy/tools/spend_guard.py") and exec_start[2] == "timer"
    assert "Environment=ORG_ROOT=/opt/MoonieXHQ/Agents/Core" in svc and re.search(r"^MemoryMax=\d+M$", svc, re.M)
    assert re.search(r"^OnCalendar=\*:0/15$", tmr, re.M) and "Unit=spend-guard.service" in tmr
    for text in (svc, tmr):
        assert not re.search(r"\b100\.\d+\.\d+\.\d+\b", text)          # no tailnet address in a public repo


def test_fal_reads_the_legacy_balance_and_never_touches_the_challenged_host():
    fake = Providers(fal=5.0)
    fake.down.add("fal-challenge")
    got = sg.read_fal(FAL_KEY, fake)
    assert got["ok"] is True
    assert got["balance"] == fake.fal
    assert not [c for c in fake.calls if "api.fal.ai" in c[1]]


def test_fal_falls_back_to_v1_billing_when_the_legacy_call_fails():
    fake = Providers()
    fake.down.add("fal-rest")
    assert sg.read_fal(FAL_KEY, fake)["balance"] == fake.fal
    assert [c for c in fake.calls if "api.fal.ai" in c[1]]


def test_fal_challenged_and_legacy_down_is_blind_with_both_reasons():
    fake = Providers()
    fake.down |= {"fal-rest", "fal-challenge"}
    with pytest.raises(sg.ProviderError) as e:
        sg.read_fal(FAL_KEY, fake)
    assert str(e.value) == "fal balance unknown: user_balance HTTP 503; billing HTTP 403"
    assert FAL_KEY not in str(e.value)


@pytest.mark.parametrize("legacy", [0, -1])
@pytest.mark.parametrize("balance", [8.97, 0])
def test_fal_nonpositive_legacy_uses_documented_balance(legacy, balance):
    calls = []

    def http(method, url, headers, body):
        calls.append(url)
        if url == f"{sg.FAL_REST}/billing/user_balance":
            return 200, legacy
        assert url == f"{sg.FAL}/account/billing?expand=credits"
        return 200, {"credits": {"current_balance": balance}}

    got = sg.read_fal(FAL_KEY, http)
    assert got["ok"] is True and got["balance"] == balance
    assert len(calls) == 2


@pytest.mark.parametrize("legacy", [0, -1])
def test_fal_untrusted_balance_and_challenge_are_failed_readings(legacy):
    fake = Providers(fal=legacy)
    fake.down.add("fal-challenge")
    got = sg.read_all(ENV, config(), fake)["fal"]
    assert got == {"ok": False, "error": (
        f"fal balance unknown: user_balance answered {legacy} (not trusted); billing HTTP 403")}


@pytest.mark.parametrize("credits", [None, {}, "invalid"])
def test_fal_missing_documented_balance_names_both_sources(credits):
    def http(method, url, headers, body):
        if "rest.alpha.fal.ai" in url:
            return 200, 0
        return 200, {"credits": credits}

    got = sg.read_all({"FAL_BILLING_API_KEY_RO": FAL_KEY}, config(), http)["fal"]
    assert got["ok"] is False
    assert got["error"] == ("fal balance unknown: user_balance answered 0 (not trusted); "
                            "billing: no credits.current_balance in the answer")


def test_fal_unknown_is_reported_to_ceo_without_balance_or_pause(store):
    fake, hub = Providers(credits=100, usage=0, keys={}, fal=0), Hub()
    fake.down.add("fal-challenge")
    cfg = config(pause={"mode": "armed"})
    code, summary = check(store, fake, hub, CFO_AT, cfg=cfg)
    assert code == sg.EXIT_BLIND
    assert summary["mail"] == ["fal/blind"]
    assert "balance" not in summary["providers"]["fal"]
    assert "unknown" in hub.mails[0]["title"]
    assert "$0" not in json.dumps(hub.mails, ensure_ascii=False)
    assert fake.writes() == [] and hub.cards == []
    assert store.snapshots()[-1]["fal"]["ok"] is False
    assert "spend_cum" not in store.snapshots()[-1]["fal"]
    assert "fal" not in store.load_state()["cycles"]
    assert "blind" in sg.status(store, cfg, CFO_AT)["last"]["fal"]
    sg.test_alert(env=ENV, cfg=cfg, store=store, http=fake, post=hub.post, now=CFO_AT)
    assert "อ่านไม่ได้" in hub.mails[-1]["title"]
    assert "$0" not in json.dumps(hub.mails[-1], ensure_ascii=False)


def test_shipped_config_never_auto_pauses_the_shared_moonie_x_key():
    """config/spend_guard.yaml: MoonieX serves the customer chatbot, so it is mapped and pause: false
    until the phase-2 broker gives each service its own key (docs/plans/spend-guard-2026-10-14.md §2)."""
    cfg = sg.load_config(REPO / "config" / "spend_guard.yaml")
    keys = cfg["providers"]["openrouter"]["keys"]
    assert keys["MoonieX"]["pause"] is False
    assert any("claudeflow-webhook" in c for c in keys["MoonieX"]["consumers"])
    assert cfg["pause"]["unmapped_keys"] == "alert"


# ------------------------------------------------------------------ CEO 2026-10-14: ≤5 lines of ≤90
def _worst_findings() -> list[list[sg.Finding]]:
    long_name = "k" * 120
    kinds = ["pause", "cap100", "runway", "blind", "spike", "cap", "paused"]
    one_each = [sg.Finding(f"x/{k}", k, 1, f'OpenRouter key "{long_name}" ({k}): ' + "ใช้ไป 100% " * 12
                           + " · พักคีย์แล้ว การ์ด RUN-20261014-0900-abcd", "openrouter",
                           link="https://terminal.mooniex.com/run#RUN-20261014-0900-abcd") for k in kinds]
    return [one_each[:1], one_each[:2], one_each[:3], one_each, one_each * 3,
            [sg.Finding("fal/blind", "blind", 1, "fal อ่านไม่ได้", "fal")],
            [sg.Finding(f"k{i}", "cap", 50, "x" * 200, "fal") for i in range(12)]]


@pytest.mark.parametrize("test_mail", [False, True])
def test_every_mail_fits_the_ceo_five_line_rule(test_mail):
    for findings in _worst_findings():
        got = sg.compose(findings, test=test_mail)
        ceo_text.check_ceo_text([(k, got.get(k)) for k in email_ceo.CEO_READS])
        assert got["title"] and got["why"]


def test_every_pause_card_fits_the_ceo_five_line_rule():
    made = []
    for name, reason, consumers in [("jev-secretary", "short", ["a"]), ("n" * 150, "ใช้พุ่ง " * 40, []),
                                    ("MoonieX", "x" * 500 + " · พักคีย์แล้ว", ["a", "b", "c"] * 20)]:
        sg.raise_pause_card("3f9c2a7b" * 8, name, reason, consumers, ENV, lambda b: made.append(b) or {})
    for card in made:
        ceo_text.check_ceo_text([("why", card["why"]), ("expected", card["expected"])])
        assert "1 เปิดคืน" in card["why"]


def test_the_full_lines_go_to_the_events_file(store):
    fake, hub = Providers(), Hub()
    check(store, fake, hub, CFO_AT)
    rows = [json.loads(x) for x in store.event_path.read_text(encoding="utf-8").splitlines()]
    mails = [r for r in rows if r["what"] == "mail"]
    assert mails and mails[0]["ref"] == hub.mails[0]["ref"] and mails[0]["lines"]
