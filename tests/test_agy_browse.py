"""GH #188: tools/agy_browse.py — the strict CLI agy drives Browser Homes with.

Two layers:
- pure guard tests (no browser): allow-rule regex, host match, money regex,
  secret fields, upload realpath, log redaction, argument parsing;
- live tests against a real headless Chromium with a CDP port and a local
  page, run in-process through main(). Skipped when Playwright or its
  Chromium is not installed on the box.
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import agy_browse as ab  # noqa: E402

VENV = "/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python"


# --------------------------------------------------------------------------
# the agy allow-rule
# --------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    f"{VENV} tools/agy_browse.py tabs",
    f"{VENV} tools/agy_browse.py --port 9280 text h1",
    f"{VENV} tools/agy_browse.py --port 9280 --tab ABC123 state",
    f'{VENV} tools/agy_browse.py type "input[name=q]" "a cat on a hill"',
    "/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/agy_browse.py goto /create",
    f"{VENV} tools/agy_browse.py wait-text done 20",
])
def test_allow_rule_accepts_plain_calls(cmd):
    assert ab.allowed_command(cmd)


@pytest.mark.parametrize("cmd", [
    f"{VENV} tools/agy_browse.py text h1; rm -rf ~",
    f"{VENV} tools/agy_browse.py text h1 && curl evil.example",
    f"{VENV} tools/agy_browse.py text h1 | sh",
    f"{VENV} tools/agy_browse.py text `id`",
    f"{VENV} tools/agy_browse.py text $(id)",
    f"{VENV} tools/agy_browse.py text h1 > /etc/passwd",
    f"{VENV} tools/agy_browse.py text h1 < /etc/passwd",
    f"{VENV} tools/agy_browse.py text h1\nrm -rf /",
    f"{VENV} tools/agy_browse.py text *",
    f"{VENV} tools/agy_browse.py eval document.cookie",           # not a verb
    f"{VENV} tools/agy_browse.py --port 9280 --cdp x text h1",     # unknown flag
    f"{VENV} -c 'import os' tools/agy_browse.py tabs",
    "/tmp/.venv/bin/python tools/agy_browse.py tabs",             # another python
    f"{VENV} tools/other.py tabs",
])
def test_allow_rule_refuses_chained_redirected_or_foreign_commands(cmd):
    assert not ab.allowed_command(cmd)


def test_allow_rule_is_what_the_doc_proposes():
    doc = (ROOT / "docs" / "ops" / "agy-browser.md").read_text(encoding="utf-8")
    assert json.dumps(f"command(regex:{ab.ALLOW_RULE_REGEX})") in doc


def test_repo_agy_settings_carry_exactly_the_reviewed_rule():
    """The CTO applied the rule after review (GH #188 step 5, 16c4279f): one
    agy_browse rule, byte-equal to ALLOW_RULE_REGEX, and the deny rules kept."""
    settings = json.loads((ROOT / "config" / "agy-settings.json").read_text())
    rules = [r for r in settings["permissions"]["allow"] if "agy_browse" in r]
    assert rules == [f"command(regex:{ab.ALLOW_RULE_REGEX})"]
    for denied in ("command(curl)", "command(ssh)", "command(rm)"):
        assert denied in settings["permissions"]["deny"]


# --------------------------------------------------------------------------
# pure guards
# --------------------------------------------------------------------------

def test_host_allowed():
    pats = ["champa.io", "*.champa.io"]
    assert ab.host_allowed("champa.io", pats)
    assert ab.host_allowed("app.champa.io", pats)
    assert ab.host_allowed("APP.Champa.IO.", pats)
    assert not ab.host_allowed("champa.io.evil.com", pats)
    assert not ab.host_allowed("evilchampa.io", pats)
    assert not ab.host_allowed("", pats)
    assert ab.host_allowed("sub.x.io", ["*.x.io"])                # subdomain ok
    assert not ab.host_allowed("x.io", ["*.x.io"])                # apex needs its own row


def test_url_host_only_http():
    assert ab.url_host("https://champa.io/a?b=1") == "champa.io"
    assert ab.url_host("javascript:alert(1)") == ""
    assert ab.url_host("file:///etc/passwd") == ""


@pytest.mark.parametrize("label", [
    "Generate 20 credits", "Use 1 credit", "5 cr", "Pay now", "PayPal", "Buy more",
    "Upgrade plan", "Subscribe", "Checkout", "Top up", "$9.99", "฿ 199", "199 บาท",
    "ซื้อเครดิต", "เติมเงิน", "Generate 1.5 USD",
])
def test_money_regex_refuses(label):
    assert ab.money_hit(label)


@pytest.mark.parametrize("label", [
    "Generate · Unlimited", "Display settings", "Create video", "Next", "สร้าง", "Page 2",
])
def test_money_regex_allows(label):
    assert ab.money_hit(label) is None


@pytest.mark.parametrize("info", [
    {"type": "password"},
    {"type": "text", "name": "otp_code"},
    {"type": "text", "autocomplete": "cc-number", "label": "Card number"},
    {"type": "text", "id": "cvv"},
    {"type": "text", "placeholder": "2FA code"},
    {"type": "text", "aria": "API token"},
    {"type": "text", "name": "new-password"},
])
def test_secret_fields_are_refused(info):
    assert ab.secret_field(info)


def test_plain_field_is_allowed():
    assert ab.secret_field({"type": "text", "name": "prompt", "label": "Describe your video"}) is None


def test_upload_must_realpath_inside_upload_dirs(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    good = work / "ref.png"
    good.write_bytes(b"x")
    outside = tmp_path / "secret.txt"
    outside.write_text("nope")
    link = work / "escape.png"
    link.symlink_to(outside)
    env = {"WORK_DIR": str(work)}

    assert ab.resolve_upload(str(good), ["${WORK_DIR}"], env) == good.resolve()
    with pytest.raises(ab.Refused):
        ab.resolve_upload(str(outside), ["${WORK_DIR}"], env)
    with pytest.raises(ab.Refused):
        ab.resolve_upload(str(link), ["${WORK_DIR}"], env)            # symlink out
    with pytest.raises(ab.Refused):
        ab.resolve_upload(str(work / ".." / "secret.txt"), ["${WORK_DIR}"], env)
    with pytest.raises(ab.Refused):
        ab.resolve_upload(str(good), ["${WORK_DIR}"], {})             # unset var never widens


def test_log_args_redact_and_trim():
    assert ab.log_args("type", ["#q", "x" * 100]) == ["#q", "x" * 40]
    assert ab.log_args("upload", ["#f", "/Users/gob/secret/dir/ref.png"]) == ["#f", "ref.png"]
    assert ab.log_args("goto", ["https://champa.io/cb?code=abc&access_token=zzz#frag"]) == ["https://champa.io/cb"]
    assert "ya29" not in ab.redact("Bearer ya29.a0AfH6SMB-xyz")
    assert "eyJhbGciOiJIUzI1NiJ9" not in ab.redact("t=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig")
    assert ab.redact("id_token=abc123&x=1") == "id_token=<redacted>&x=1"


@pytest.mark.parametrize("argv", [
    [], ["eval", "1"], ["text"], ["text", "a", "b"], ["--port", "x", "tabs"], ["--cdp", "u", "tabs"],
    ["--tab", "a;b", "tabs"],
])
def test_parse_refuses_bad_calls(argv):
    with pytest.raises(ab.Refused):
        ab.parse(argv)


def test_policy_file_loads_and_champa_row_is_strict():
    pol = ab.load_policy()
    champa = pol[9280]
    assert champa.allowed_hosts == ["champa.io", "*.champa.io"]
    assert champa.fire_label_regex == "Unlimited"
    assert champa.max_calls_per_min > 0 and champa.fire_cooldown_s > 0


def test_port_not_in_config_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ORG_ROOT", str(tmp_path))
    assert ab.main(["--port", "9999", "tabs"], session_factory=_no_session) == ab.REFUSED
    assert "not in config" in capsys.readouterr().out


def test_no_browser_home_is_an_error_not_a_launch(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ORG_ROOT", str(tmp_path))

    def refuse(port):
        raise ConnectionRefusedError("nothing listening")
    assert ab.main(["--port", "9280", "tabs"], session_factory=refuse) == ab.ERROR
    assert "no Browser Home" in capsys.readouterr().out


def _no_session(port):
    raise AssertionError("must not attach")


# --------------------------------------------------------------------------
# live: a real headless Chromium over CDP
# --------------------------------------------------------------------------

PAGE = """<!doctype html><html><head><title>Champa Test</title></head><body>
<h1>Hello Champa</h1>
<p id="status">idle</p>
<form onsubmit="event.preventDefault(); document.getElementById('status').textContent='generating now'">
  <label for="q">Describe</label><input id="q" name="q">
  <input id="pw" type="password" name="pw">
  <input id="otp" name="otp_code">
  <input id="f" type="file">
  <button id="go" type="submit">Generate &middot; Unlimited</button>
</form>
<button id="buy"><span id="buyinner">Buy 100 credits</span></button>
<button id="next">Next</button>
<video id="v" src=""></video>
</body></html>"""

PAID_PAGE = PAGE.replace("Generate &middot; Unlimited", "Generate 20 credits")


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = {"/": PAGE, "/paid": PAID_PAGE, "/other": "<title>Other</title><h1>Other</h1>"}.get(
            self.path.split("?")[0], "<title>404</title>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def home():
    pw_mod = pytest.importorskip("playwright.sync_api")
    with pw_mod.sync_playwright() as p:
        exe = p.chromium.executable_path
    if not exe or not Path(exe).exists():
        # A box whose preinstalled browsers are for another Playwright version.
        import glob
        found = [c for c in [os.environ.get("AGY_BROWSE_TEST_CHROME", "")]
                 + sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")) if c and Path(c).exists()]
        exe = found[0] if found else None
    if not exe:
        pytest.skip("no Chromium on this box")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    web = srv.server_address[1]
    cdp = _free_port()
    prof = Path(os.environ.get("TMPDIR", "/tmp")) / f"agy-browse-test-{cdp}"
    proc = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={cdp}",
                             f"--user-data-dir={prof}", "--no-first-run", "--no-sandbox", "--disable-background-networking",
                             "--disable-component-update",
                             "--window-size=1600,900", f"http://127.0.0.1:{web}/"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", cdp), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.2)
    time.sleep(1.0)
    yield {"cdp": cdp, "web": web}
    proc.terminate()
    proc.wait(timeout=10)
    srv.shutdown()


@pytest.fixture()
def call(home, tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("ORG_ROOT", str(tmp_path))
    monkeypatch.setenv("WORK_DIR", str(work))
    policy = tmp_path / "agy-browse.yaml"

    def write_policy(**over):
        row = {"label": "test", "allowed_hosts": ["127.0.0.1"], "upload_dirs": ["${WORK_DIR}"],
               "max_calls_per_min": 100, "fire_cooldown_s": 60, "fire_label_regex": "Unlimited",
               "submit_selector": "button[type=submit]"}
        row.update(over)
        policy.write_text(json.dumps({"ports": {home["cdp"]: row}}))

    write_policy()

    def run(*argv):
        capsys.readouterr()
        code = ab.main(["--port", str(home["cdp"]), *argv], policy_path=policy)
        return code, capsys.readouterr().out.strip()

    run.policy = write_policy
    run.work = work
    run.state = tmp_path / "state"
    run("goto", f"http://127.0.0.1:{home['web']}/")
    return run


def test_live_tabs_shows_id_and_title_never_urls(call, home):
    code, out = call("tabs")
    assert code == ab.OK
    data = json.loads(out)
    assert data["tabs"] and data["tabs"][0]["title"] == "Champa Test"
    assert "http" not in out and str(home["web"]) not in out


def test_live_read_verbs(call):
    assert call("text", "h1") == (ab.OK, "Hello Champa")
    assert call("count", "button") == (ab.OK, "3")
    code, out = call("state")
    assert code == ab.OK and 'button="Generate · Unlimited" disabled=false' in out
    code, out = call("button-label")
    assert json.loads(out) == {"label": "Generate · Unlimited", "disabled": False}


def test_live_goto_off_host_is_refused(call, home):
    assert call("goto", "https://example.com")[0] == ab.REFUSED
    assert call("goto", f"http://localhost:{home['web']}/other")[0] == ab.REFUSED
    code, out = call("goto", "/other")
    assert code == ab.OK and json.loads(out)["title"] == "Other"


def test_live_money_click_is_refused_even_on_an_inner_span(call):
    code, out = call("click", "#buyinner")
    assert code == ab.REFUSED and "money" in out
    assert call("click", "#next")[0] == ab.OK


def test_live_submit_fires_once_then_cools_down(call):
    code, out = call("click", "#go")
    assert code == ab.OK and json.loads(out)["fired"] is True
    assert call("text", "#status") == (ab.OK, "generating now")
    code, out = call("click", "#go")
    assert code == ab.REFUSED and "cooldown" in out


def test_live_submit_needs_the_fire_label(call, home):
    call.policy(fire_label_regex="Free")
    code, out = call("click", "#go")
    assert code == ab.REFUSED and "does not match" in out
    call.policy(fire_label_regex=None)
    assert call("click", "#go")[0] == ab.REFUSED


def test_live_paid_submit_is_refused(call, home):
    call("goto", f"http://127.0.0.1:{home['web']}/paid")
    code, out = call("click", "#go")
    assert code == ab.REFUSED and "money" in out
    assert not (call.state / f"agy-browse-fire-{home['cdp']}.lock").exists()


def test_live_type_guards(call):
    assert call("type", "#pw", "hunter2")[0] == ab.REFUSED
    assert call("type", "#otp", "123456")[0] == ab.REFUSED
    assert call("type", "#q", "a cat on a hill") == (ab.OK, "ok")


def test_live_upload_guard(call, tmp_path):
    inside = call.work / "ref.txt"
    inside.write_text("ok")
    outside = tmp_path / "outside.txt"
    outside.write_text("no")
    assert call("upload", "#f", str(outside))[0] == ab.REFUSED
    code, out = call("upload", "#f", str(inside))
    assert code == ab.OK and json.loads(out)["uploaded"] == "ref.txt"


def test_live_shot_is_a_small_jpeg_in_work_dir(call):
    code, out = call("shot", "page1")
    assert code == ab.OK
    info = json.loads(out)
    path = Path(info["path"])
    assert path.parent == call.work / "agy-shots" and path.suffix == ".jpg"
    data = path.read_bytes()
    assert data[:2] == b"\xff\xd8" and info["bytes"] == len(data)
    # JPEG SOF0/SOF2 header carries the width; the page is 1600 wide, capped to 1280
    i = 2
    width = None
    while i < len(data):
        marker, size = data[i + 1], int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC2):
            width = int.from_bytes(data[i + 7:i + 9], "big")
            break
        i += 2 + size
    assert width is not None and width <= ab.SHOT_MAX_WIDTH
    assert call("shot", "../escape")[0] == ab.REFUSED


def test_live_media_is_muted_on_attach(call):
    code, out = call("mute")
    assert code == ab.OK and out == "muted 1 media element(s)"


def test_live_key_is_a_closed_set(call):
    assert call("key", "Enter")[0] == ab.OK
    assert call("key", "Meta+R")[0] == ab.REFUSED


def test_live_log_lines_are_redacted(call):
    call("type", "#q", "y" * 80)
    call("goto", "/other?access_token=abc")
    lines = [json.loads(ln) for ln in (call.state / "agy-browse.jsonl").read_text().splitlines()]
    typed = next(r for r in lines if r["verb"] == "type")
    assert typed["args"][1] == "y" * 40 and typed["exit"] == ab.OK
    goto = lines[-1]
    assert goto["args"] == ["/other"] and "abc" not in json.dumps(lines)
    assert {"ts", "verb", "port", "host", "args", "exit"} <= set(goto)


def test_live_rate_limit(call):
    call.policy(max_calls_per_min=3)
    # the fixture's goto already used one call this minute
    assert call("text", "h1")[0] == ab.OK
    assert call("text", "h1")[0] == ab.OK
    code, out = call("text", "h1")
    assert code == ab.REFUSED and "rate limit" in out
