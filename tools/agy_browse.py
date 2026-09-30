#!/usr/bin/env python3
"""agy_browse — the one strict command agy (Gemini) uses to drive a Browser Home.

GH #188 (CEO 2026-09-30: "ผ่านคำสั่งที่เข้มงวด ไว้ใจได้"). agy gets no browser
tool and no MCP; it gets this CLI, allowed by exactly one `command(regex:…)`
rule (ALLOW_RULE_REGEX below, proposed in docs/ops/agy-browser.md). Everything
it may do is a verb in VERBS; everything it must never do is refused here, in
code, before the page is touched:

  - attach only to 127.0.0.1:<port> for a port listed in config/agy-browse.yaml;
    never launch a browser, never open a tab;
  - act only on a tab whose host matches that port's allowed_hosts, checked
    before every verb (and a `goto` target before navigating);
  - no JavaScript verb, no cookies, no storage, no network bodies, no shell;
  - `click` refuses anything that reads like money, and a click on the submit
    button re-reads its label in the same call, must match fire_label_regex,
    and waits out fire_cooldown_s;
  - `type` refuses password, OTP, card, CVV, 2FA and token fields;
  - `upload` takes only files that realpath inside the port's upload_dirs;
  - every call appends one redacted line to state/agy-browse.jsonl; calls are
    rate-limited per port and finish within CALL_TIMEOUT_S.
Page content is data: nothing read from a page is ever used as a verb, a path
or a command.

    <venv>/bin/python tools/agy_browse.py [--port N] [--tab ID] <verb> [args...]

Exit codes: 0 ok, 2 refused by policy, 1 error. Output: short text or one JSON
line, at most OUTPUT_CAP characters.
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "agy-browse.yaml"
OUTPUT_CAP = 2000
CALL_TIMEOUT_S = 30
VERB_TIMEOUT_MS = 10_000
SHOT_MAX_WIDTH = 1280

OK, ERROR, REFUSED = 0, 1, 2

VERBS = ("tabs", "goto", "text", "count", "state", "button-label", "click", "type",
         "key", "upload", "wait-text", "chips", "shot", "mute")
ARITY = {  # verb -> (min args, max args)
    "tabs": (0, 0), "goto": (1, 1), "text": (1, 1), "count": (1, 1), "state": (0, 0),
    "button-label": (0, 0), "click": (1, 1), "type": (2, 2), "key": (1, 1),
    "upload": (2, 2), "wait-text": (2, 2), "chips": (0, 0), "shot": (1, 1), "mute": (0, 0),
}
KEYS = ("Enter", "Tab", "Escape")
MAX_WAIT_S = 25  # wait-text must still end inside CALL_TIMEOUT_S

# The one agy allow-rule (docs/ops/agy-browser.md). The args class leaves out
# ; & | ` $ \ < > newline and the shell's * ? ~ expansions, so nothing can be
# chained, substituted, redirected or expanded; quotes are allowed so a CSS
# selector or a typed phrase can carry spaces. ASCII only and no escapes
# beyond \. \[ \] \" : agy's regex engine is not ours to assume, so Thai text
# cannot be typed through this rule.
_CORE = r"(/Users/gob/MoonieXHQ/Agents/Core|/opt/MoonieXHQ/Agents/Core)"
_ARGS = r"""[A-Za-z0-9 _./:#=@%+,'"()\[\]-]"""
ALLOW_RULE_REGEX = (
    rf"^{_CORE}/\.venv/bin/python tools/agy_browse\.py"
    rf"( --port [0-9]{{4,5}})?( --tab [A-Za-z0-9]{{1,64}})?"
    rf" ({'|'.join(VERBS)})( {_ARGS}*)?$"
)

# Money: a click whose target (or the button/link around it) reads like any of
# these is refused, whatever the site.
MONEY_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:credits?\b|cr\b|฿|\$|usd\b|บาท|เครดิต)"
    r"|[฿$]\s*\d"
    r"|\b(?:buy|purchase|subscribe|upgrade|pay\w*|checkout|top ?up)\b"
    r"|ซื้อ|ชำระ|อัปเกรด|เติมเงิน|สมัครสมาชิก",
    re.IGNORECASE,
)
SECRET_FIELD_RE = re.compile(r"pass|otp|card|cvv|2fa|token", re.IGNORECASE)
_TOKEN_RES = (
    re.compile(r"ya29\.[\w-]+"),
    re.compile(r"eyJ[\w-]+(?:\.[\w-]+){0,2}"),
    re.compile(r"([A-Za-z0-9_]*_token)=[^&\s]+", re.IGNORECASE),
)
SHOT_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class Refused(Exception):
    """Policy said no. Exit 2."""


# --------------------------------------------------------------------------
# policy
# --------------------------------------------------------------------------

@dataclass
class PortPolicy:
    port: int
    label: str
    allowed_hosts: list[str]
    upload_dirs: list[str] = field(default_factory=list)
    max_calls_per_min: int = 30
    fire_cooldown_s: int = 120
    fire_label_regex: str | None = None
    submit_selector: str = "button[type=submit]"
    chip_selector: str | None = None


def load_policy(path: Path = POLICY_PATH) -> dict[int, PortPolicy]:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise Refused(f"policy unreadable: {path.name}: {e}")
    out: dict[int, PortPolicy] = {}
    for port, row in (raw.get("ports") or {}).items():
        if not isinstance(row, dict) or not row.get("allowed_hosts"):
            raise Refused(f"policy row {port} has no allowed_hosts")
        out[int(port)] = PortPolicy(
            port=int(port),
            label=str(row.get("label") or port),
            allowed_hosts=[str(h).lower() for h in row["allowed_hosts"]],
            upload_dirs=[str(d) for d in (row.get("upload_dirs") or [])],
            max_calls_per_min=int(row.get("max_calls_per_min", 30)),
            fire_cooldown_s=int(row.get("fire_cooldown_s", 120)),
            fire_label_regex=row.get("fire_label_regex"),
            submit_selector=str(row.get("submit_selector") or "button[type=submit]"),
            chip_selector=row.get("chip_selector"),
        )
    if not out:
        raise Refused("policy lists no ports")
    return out


def pick_port(policy: dict[int, PortPolicy], port: int | None) -> PortPolicy:
    if port is None:
        env = os.environ.get("AGY_BROWSE_PORT")
        port = int(env) if env and env.isdigit() else None
    if port is None:
        if len(policy) != 1:
            raise Refused(f"--port is required (config lists {sorted(policy)})")
        return next(iter(policy.values()))
    if port not in policy:
        raise Refused(f"port {port} is not in config/agy-browse.yaml")
    return policy[port]


def host_allowed(host: str, patterns: list[str]) -> bool:
    host = (host or "").lower().rstrip(".")
    if not host:
        return False
    for pat in patterns:
        if pat.startswith("*."):
            if host.endswith(pat[1:]) and host != pat[2:]:
                return True
        elif host == pat:
            return True
    return False


def url_host(url: str) -> str:
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https"):
        return ""
    return (parts.hostname or "").lower()


# --------------------------------------------------------------------------
# guards (pure, one test each in tests/test_agy_browse.py)
# --------------------------------------------------------------------------

def money_hit(*texts: str) -> str | None:
    for t in texts:
        m = MONEY_RE.search(t or "")
        if m:
            return m.group(0)
    return None


def secret_field(info: dict) -> str | None:
    if (info.get("type") or "").lower() == "password":
        return "input[type=password]"
    for key in ("name", "id", "autocomplete", "label", "placeholder", "aria"):
        val = info.get(key) or ""
        if SECRET_FIELD_RE.search(val):
            return f"{key}={val[:40]!r}"
    return None


def expand_dirs(dirs: list[str], env=None) -> list[Path]:
    env = os.environ if env is None else env
    out = []
    for d in dirs:
        unset = [v for v in re.findall(r"\$\{(\w+)\}", d) if not env.get(v)]
        if unset:
            continue  # an unset ${VAR} drops the entry, never widens it
        expanded = re.sub(r"\$\{(\w+)\}", lambda m: env[m.group(1)], d)
        out.append(Path(os.path.realpath(os.path.expanduser(expanded))))
    return out


def resolve_upload(path: str, dirs: list[str], env=None) -> Path:
    allowed = expand_dirs(dirs, env)
    if not allowed:
        raise Refused("no upload_dirs for this port")
    real = Path(os.path.realpath(path))
    if not real.is_file():
        raise Refused(f"upload is not a file: {Path(path).name}")
    for base in allowed:
        if real == base or base in real.parents:
            return real
    raise Refused(f"upload outside upload_dirs: {Path(path).name}")


def redact(text: str) -> str:
    for rx in _TOKEN_RES:
        text = rx.sub(lambda m: (m.group(1) + "=<redacted>") if m.lastindex else "<redacted>", text)
    return text


def log_args(verb: str, args: list[str]) -> list[str]:
    """What the log may keep of the args: typed text cut to 40 chars, uploads
    as a basename, URLs without their query or fragment, tokens redacted."""
    out = []
    for i, a in enumerate(args):
        if verb == "type" and i == 1:
            a = a[:40]
        elif verb == "upload" and i == 1:
            a = Path(a).name
        elif verb == "goto":
            p = urlsplit(a)
            a = f"{p.scheme + '://' if p.scheme else ''}{p.netloc}{p.path}"
        out.append(redact(a))
    return out


def allowed_command(cmd: str) -> bool:
    return re.fullmatch(ALLOW_RULE_REGEX, cmd) is not None


# --------------------------------------------------------------------------
# log, rate limit, fire cooldown
# --------------------------------------------------------------------------

def _state_dir() -> Path:
    # A worker runs from its worktree; ORG_ROOT (set at spawn) is the hub
    # checkout, so every worktree shares one log and one rate limit.
    base = os.environ.get("ORG_ROOT") or str(ROOT)
    return Path(base) / "state"


def log_path() -> Path:
    return _state_dir() / "agy-browse.jsonl"


def append_log(verb: str, port: int | None, host: str, args: list[str], code: int) -> None:
    rec = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
           "verb": verb, "port": port, "host": host,
           "args": log_args(verb, args), "exit": code}
    try:
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass  # a log failure never turns a refusal into a success or vice versa


def calls_in_last_minute(port: int, now: float) -> int:
    p = log_path()
    if not p.exists():
        return 0
    n = 0
    try:
        lines = p.read_text(encoding="utf-8").splitlines()[-500:]
    except OSError:
        return 0
    for ln in lines:
        try:
            rec = json.loads(ln)
            ts = datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except (ValueError, KeyError, TypeError):
            continue
        if rec.get("port") == port and now - ts.timestamp() < 60:
            n += 1
    return n


def fire_lock(port: int) -> Path:
    return _state_dir() / f"agy-browse-fire-{port}.lock"


def check_fire_cooldown(pol: PortPolicy, now: float) -> None:
    lock = fire_lock(pol.port)
    if lock.exists():
        age = now - lock.stat().st_mtime
        if age < pol.fire_cooldown_s:
            raise Refused(f"submit fired {int(age)}s ago; cooldown is {pol.fire_cooldown_s}s")


def mark_fired(port: int) -> None:
    lock = fire_lock(port)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(str(time.time()), encoding="utf-8")


# --------------------------------------------------------------------------
# page snippets: fixed strings, never built from page content
# --------------------------------------------------------------------------

MUTE_JS = """() => {
  const m = () => document.querySelectorAll('video,audio').forEach(v => { v.muted = true; v.volume = 0; });
  m();
  if (!window.__agyBrowseMute) {
    window.__agyBrowseMute = new MutationObserver(m);
    window.__agyBrowseMute.observe(document.documentElement, {childList: true, subtree: true});
  }
  return document.querySelectorAll('video,audio').length;
}"""

# BROWSER_OPERATOR_Protocol_Playbook "The snippet", with the button selector
# from the port's policy.
STATE_JS = r"""(sel) => {
  const clip = (s, n) => (s || '').replace(/\s+/g, ' ').trim().slice(0, n);
  const body = document.body ? (document.body.innerText || '') : '';
  const parts = [];
  const btn = document.querySelector(sel);
  if (btn) parts.push('button="' + clip(btn.innerText || btn.value, 60) + '" disabled=' + !!btn.disabled);
  const markers = [
    /(rights verification required|confirm rights)[^\n]{0,80}/i,
    /(sign in|log in|accounts\.google\.com\/ServiceLogin)[^\n]{0,80}/i,
    /(429|too many requests|rate limit|slot.?busy|1 unlimited generation at a time)[^\n]{0,80}/i,
    /(generating|processing|queued|rendering|in progress)[^\n]{0,40}/i,
    /(something went wrong|failed to generate|\bfailed\b|prompt is required)[^\n]{0,80}/i,
    /ล้มเหลว[^\n]*\n?[^\n]*/,
  ];
  for (const re of markers) { const m = body.match(re); if (m) parts.push(clip(m[0], 200)); }
  return parts.join(' | ').slice(0, 1500);
}"""

BUTTON_JS = r"""(sel) => {
  const b = document.querySelector(sel);
  if (!b) return null;
  return {label: (b.innerText || b.value || b.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 120),
          disabled: !!b.disabled || b.getAttribute('aria-disabled') === 'true'};
}"""

# What a click target says about itself and the control around it.
LABEL_JS = r"""(el) => {
  const t = (e) => e ? [e.innerText, e.value, e.getAttribute && e.getAttribute('aria-label'),
                        e.getAttribute && e.getAttribute('title')].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim().slice(0, 300) : '';
  const around = el.closest('button,[role=button],a,input[type=submit],input[type=button]');
  return {own: t(el), around: around && around !== el ? t(around) : ''};
}"""

FIELD_JS = r"""(el) => {
  const a = (k) => (el.getAttribute(k) || '');
  let label = '';
  if (el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (l) label = l.innerText; }
  if (!label) { const l = el.closest('label'); if (l) label = l.innerText; }
  return {tag: el.tagName.toLowerCase(), type: (el.type || a('type') || ''), name: a('name'), id: el.id || '',
          autocomplete: a('autocomplete'), placeholder: a('placeholder'), aria: a('aria-label'),
          label: (label || '').slice(0, 120), editable: el.isContentEditable};
}"""

# BROWSER_OPERATOR_Protocol_Playbook "Count the reference chips": a bound chip
# is a leaf span in the composer whose text starts with '@'.
CHIPS_JS = r"""(sel) => {
  const nodes = sel ? [...document.querySelectorAll(sel)]
    : [...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]
        .filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'));
  return nodes.length;
}"""


# --------------------------------------------------------------------------
# browser
# --------------------------------------------------------------------------

class Session:
    """A CDP attachment to one Browser Home. Never launches or closes Chrome."""

    def __init__(self, port: int):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        try:
            self.browser = self._pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=8000)
        except Exception:
            self._pw.stop()
            raise

    def pages(self):
        return [pg for ctx in self.browser.contexts for pg in ctx.pages]

    def target_id(self, page) -> str:
        cdp = page.context.new_cdp_session(page)
        try:
            return cdp.send("Target.getTargetInfo")["targetInfo"]["targetId"]
        finally:
            cdp.detach()

    def close(self) -> None:
        # Stop the driver only: browser.close() on a CDP attachment can close
        # the Home's own contexts, and the Home belongs to the Console.
        try:
            self._pw.stop()
        except Exception:
            pass


def _out(obj) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= OUTPUT_CAP else s[:OUTPUT_CAP - 3] + "..."


def _one(page, css: str):
    loc = page.locator(css)
    n = loc.count()
    if n == 0:
        raise Refused(f"no element matches {css!r}")
    return loc.first


def shot_dir(env=None) -> Path:
    env = os.environ if env is None else env
    base = env.get("AGY_BROWSE_SHOT_DIR") or env.get("WORK_DIR")
    return (Path(base) if base else Path.cwd()) / "agy-shots"


def run_verb(sess: Session, pol: PortPolicy, page, verb: str, args: list[str]) -> str:
    page.set_default_timeout(VERB_TIMEOUT_MS)
    if verb == "goto":
        target = urljoin(page.url, args[0])
        host = url_host(target)
        if not host_allowed(host, pol.allowed_hosts):
            raise Refused(f"goto host {host or '?'} is not allowed on port {pol.port}")
        page.goto(target, wait_until="domcontentloaded")
        page.evaluate(MUTE_JS)
        landed = url_host(page.url)
        if not host_allowed(landed, pol.allowed_hosts):
            raise Refused(f"navigation left the allowed hosts (now {landed or '?'})")
        return _out({"title": page.title()[:200], "path": urlsplit(page.url).path})
    if verb == "text":
        return _out(_one(page, args[0]).inner_text())
    if verb == "count":
        return str(page.locator(args[0]).count())
    if verb == "state":
        return _out(page.evaluate(STATE_JS, pol.submit_selector) or "(no markers)")
    if verb == "button-label":
        return _out(page.evaluate(BUTTON_JS, pol.submit_selector) or {"label": None})
    if verb == "chips":
        return str(page.evaluate(CHIPS_JS, pol.chip_selector))
    if verb == "mute":
        return f"muted {page.evaluate(MUTE_JS)} media element(s)"
    if verb == "key":
        if args[0] not in KEYS:
            raise Refused(f"key must be one of {', '.join(KEYS)}")
        page.keyboard.press(args[0])
        return "ok"
    if verb == "wait-text":
        try:
            rx = re.compile(args[0], re.IGNORECASE)
            max_s = float(args[1])
        except (re.error, ValueError) as e:
            raise Refused(f"wait-text needs <regex> <max_s>: {e}")
        max_s = max(0.0, min(max_s, MAX_WAIT_S))
        end = time.monotonic() + max_s
        while True:
            body = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
            m = rx.search(body)
            if m:
                return _out({"found": True, "match": m.group(0)[:200]})
            if time.monotonic() >= end:
                return _out({"found": False, "waited_s": max_s})
            time.sleep(0.5)
    if verb == "click":
        return _click(pol, page, args[0])
    if verb == "type":
        el = _one(page, args[0])
        info = el.evaluate(FIELD_JS)
        why = secret_field(info)
        if why:
            raise Refused(f"type refused on a secret field ({why})")
        if info.get("tag") not in ("input", "textarea") and not info.get("editable"):
            raise Refused("type target is not a text field")
        el.fill(args[1])
        return "ok"
    if verb == "upload":
        real = resolve_upload(args[1], pol.upload_dirs)
        el = _one(page, args[0])
        if el.evaluate("(e) => e.tagName.toLowerCase() === 'input' && e.type === 'file'") is not True:
            raise Refused("upload target is not an input[type=file]")
        el.set_input_files(str(real))
        return _out({"uploaded": real.name, "bytes": real.stat().st_size})
    if verb == "shot":
        return _shot(page, args[0])
    raise Refused(f"unknown verb {verb!r}")


def _click(pol: PortPolicy, page, css: str) -> str:
    el = _one(page, css)
    lab = el.evaluate(LABEL_JS)
    hit = money_hit(lab.get("own", ""), lab.get("around", ""))
    if hit:
        raise Refused(f"click refused: the control reads like money ({hit!r})")
    is_submit = el.evaluate(
        "(e, sel) => { const s = document.querySelector(sel); return !!s && (s === e || s.contains(e)); }",
        pol.submit_selector)
    if is_submit:
        if not pol.fire_label_regex:
            raise Refused("this port has no fire_label_regex: the submit button is never clicked")
        check_fire_cooldown(pol, time.time())
        # Re-read the label right before the click, in this same call.
        now_label = (page.evaluate(BUTTON_JS, pol.submit_selector) or {}).get("label") or ""
        if money_hit(now_label):
            raise Refused(f"submit label reads like money: {now_label[:60]!r}")
        if not re.search(pol.fire_label_regex, now_label):
            raise Refused(f"submit label {now_label[:60]!r} does not match {pol.fire_label_regex!r}")
        mark_fired(pol.port)  # before the click: a failed click still starts the cooldown
        el.click()
        return _out({"fired": True, "label": now_label[:60]})
    el.click()
    return "ok"


def _shot(page, name: str) -> str:
    if not SHOT_NAME_RE.match(name):
        raise Refused("shot name must be 1-40 of [A-Za-z0-9_-]")
    out_dir = shot_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.jpg"
    width = page.evaluate("() => window.innerWidth") or SHOT_MAX_WIDTH
    height = page.evaluate("() => window.innerHeight") or 800
    scale = min(1.0, SHOT_MAX_WIDTH / float(width))
    cdp = page.context.new_cdp_session(page)
    try:
        import base64
        res = cdp.send("Page.captureScreenshot", {
            "format": "jpeg", "quality": 70, "fromSurface": True,
            "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": scale},
        })
    finally:
        cdp.detach()
    path.write_bytes(base64.b64decode(res["data"]))
    return _out({"path": str(path), "bytes": path.stat().st_size})


# --------------------------------------------------------------------------
# entry
# --------------------------------------------------------------------------

def parse(argv: list[str]) -> tuple[int | None, str | None, str, list[str]]:
    port = tab = None
    i = 0
    while i < len(argv) and argv[i].startswith("--"):
        flag = argv[i]
        if flag not in ("--port", "--tab") or i + 1 >= len(argv):
            raise Refused(f"unknown option {flag}")
        if flag == "--port":
            if not argv[i + 1].isdigit():
                raise Refused("--port takes a number")
            port = int(argv[i + 1])
        else:
            if not re.fullmatch(r"[A-Za-z0-9]{1,64}", argv[i + 1]):
                raise Refused("--tab takes a tab id from `tabs`")
            tab = argv[i + 1]
        i += 2
    if i >= len(argv):
        raise Refused(f"no verb; one of: {' '.join(VERBS)}")
    verb, args = argv[i], argv[i + 1:]
    if verb not in VERBS:
        raise Refused(f"unknown verb {verb!r}; one of: {' '.join(VERBS)}")
    lo, hi = ARITY[verb]
    if not lo <= len(args) <= hi:
        raise Refused(f"{verb} takes {lo if lo == hi else f'{lo}-{hi}'} argument(s)")
    return port, tab, verb, args


def main(argv: list[str] | None = None, *, session_factory=Session,
         policy_path: Path = POLICY_PATH) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    verb, port_no, host, args = "?", None, "", []
    code = ERROR
    sess = None
    try:
        port_arg, tab, verb, args = parse(argv)
        pol = pick_port(load_policy(policy_path), port_arg)
        port_no = pol.port
        if calls_in_last_minute(pol.port, time.time()) >= pol.max_calls_per_min:
            raise Refused(f"rate limit: {pol.max_calls_per_min} calls/min on port {pol.port}")
        try:
            sess = session_factory(pol.port)
        except Exception as e:
            print(_out(f"error: no Browser Home on 127.0.0.1:{pol.port} ({type(e).__name__})"))
            return ERROR
        allowed = [pg for pg in sess.pages() if host_allowed(url_host(pg.url), pol.allowed_hosts)]
        others = len(sess.pages()) - len(allowed)
        if verb == "tabs":
            rows = [{"id": sess.target_id(pg), "title": (pg.title() or "")[:120]} for pg in allowed]
            print(_out({"tabs": rows, "other_hosts": others}))
            code = OK
            return code
        if tab:
            page = next((pg for pg in allowed if sess.target_id(pg) == tab), None)
            if page is None:
                raise Refused(f"tab {tab} is not an open tab on an allowed host")
        else:
            if not allowed:
                raise Refused(f"no tab on an allowed host ({', '.join(pol.allowed_hosts)})")
            page = allowed[0]
        host = url_host(page.url)
        if not host_allowed(host, pol.allowed_hosts):  # checked again right before the verb
            raise Refused(f"tab host {host or '?'} is not allowed")
        page.evaluate(MUTE_JS)  # every attach
        print(run_verb(sess, pol, page, verb, args))
        code = OK
    except Refused as e:
        print(_out(f"refused: {e}"))
        code = REFUSED
    except Exception as e:  # page errors, timeouts, a Home that went away
        print(_out(f"error: {type(e).__name__}: {redact(str(e))[:300]}"))
        code = ERROR
    finally:
        if sess is not None:
            sess.close()
        append_log(verb, port_no, host, args, code)
    return code


def _timeout(_sig, _frm):
    raise TimeoutError(f"call exceeded {CALL_TIMEOUT_S}s")


if __name__ == "__main__":
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(CALL_TIMEOUT_S)
    sys.exit(main())
