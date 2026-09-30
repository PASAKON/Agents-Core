"""Org Mesh W4.4 (task-49f70bc6): `probe` measures `provides` on the node.

`tools.node_dispatch.verb_probe` adds `provides_measured` (what this box can
do, found by looking) and `probe_errors` (detectors that failed). Every detector
is faked here: no real ffmpeg, node, nvidia-smi or Chrome is asked, `subprocess.run`
is a recorder that refuses any child it was not told about, and the platform is
faked at `node_dispatch._os_name` / `_is_windows`. HOME, CLAUDE_CONFIG_DIR,
CODEX_HOME and PLAYWRIGHT_BROWSERS_PATH point into tmp_path.

The credential pin is the one that matters: a signed-in runner is read off a
file's existence and size, and `open()` / `read_text()` / `read_bytes()` on those
paths explode in the test that proves it.

Run:  .venv/bin/python -m pytest tests/test_w44_probe_provides.py
"""
from __future__ import annotations

import ast
import builtins
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config as config_mod  # noqa: E402
from lib import db as db_mod  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

SECRET = "TOP-SECRET-credential-body-7f3a9c0d"
ALL_NAMES = ["chrome", "ffmpeg", "gpu", "node20", "playwright_chromium",
             "runner_claude", "runner_codex", "runner_agy"]


# ---------------------------------------------------------------------------
# a fake box
# ---------------------------------------------------------------------------

class Children:
    """subprocess.run, replaced. `table` maps argv[0] to (exit code, stdout) or to
    an exception to raise. A child that is not in the table is a test failure:
    nothing the test did not plan for may run."""

    def __init__(self) -> None:
        self.table: dict[str, object] = {}
        self.calls: list[tuple[list, dict]] = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        hit = self.table.get(argv[0])
        if hit is None:
            raise AssertionError(f"unplanned child process: {argv}")
        if isinstance(hit, BaseException):
            raise hit
        code, out = hit
        return subprocess.CompletedProcess(
            argv, code, out if kw.get("stdout") == subprocess.PIPE else None, None)


def _boom(*a, **kw):
    raise AssertionError("must not be reached")


class Box:
    def __init__(self, monkeypatch, tmp_path: Path) -> None:
        self.mp = monkeypatch
        self.tmp = tmp_path
        self.home = tmp_path / "home"
        self.home.mkdir()
        self.on_path: dict[str, str] = {}
        self.fake_files: set[str] = set()  # paths outside tmp_path that "exist"
        self.children = Children()
        monkeypatch.setenv("HOME", str(self.home))
        monkeypatch.setenv("USERPROFILE", str(self.home))
        for var in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "PLAYWRIGHT_BROWSERS_PATH",
                    "PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(nd.shutil, "which", lambda name, *a, **kw: self.on_path.get(name))
        monkeypatch.setattr(subprocess, "run", self.children)
        monkeypatch.setattr(subprocess, "Popen", _boom)
        # Only files under tmp_path or named in `fake_files` exist: this Mac's real
        # /Applications/Google Chrome.app must not leak into a faked-macOS test.
        monkeypatch.setattr(nd, "_is_file", lambda p: str(p) in self.fake_files or (
            str(p).startswith(str(tmp_path)) and Path.is_file(p)))
        self.os("linux")

    def os(self, name: str) -> None:
        """Fake the platform: 'macos' | 'linux' | 'windows'."""
        self.mp.setattr(nd, "_is_windows", lambda: name == "windows")
        self.mp.setattr(nd, "_os_name", lambda: {"macos": "darwin"}.get(name, name))

    def binary(self, name: str, code: int = 0, out: str = "") -> str:
        """`name` is on PATH and answers `code`/`out` when run."""
        path = f"/fake/bin/{name}"
        self.on_path[name] = path
        self.children.table[path] = (code, out)
        return path

    def file(self, path: Path, body: str = SECRET) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def measured(self) -> list[str]:
        return nd._measure_provides()[0]


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setenv("ORG_HOST", "mac")
    config_mod.self_host.cache_clear()
    monkeypatch.setattr(nd, "_git_version", lambda: "abc1234")
    monkeypatch.setattr(nd, "_ram_free_gb", lambda: 8.0)
    yield
    config_mod.self_host.cache_clear()


@pytest.fixture
def box(monkeypatch, tmp_path) -> Box:
    return Box(monkeypatch, tmp_path)


# ---------------------------------------------------------------------------
# the shape of the answer
# ---------------------------------------------------------------------------

def test_a_bare_box_measures_only_its_os_and_reports_no_error(box):
    assert nd._measure_provides() == (["linux"], [])


@pytest.mark.parametrize("fake, family", [("macos", "macos"), ("linux", "linux"),
                                          ("windows", "windows")])
def test_the_os_family_comes_first(box, fake, family):
    box.os(fake)
    assert box.measured() == [family]


def test_probe_reports_provides_measured_and_probe_errors_as_json(box):
    box.binary("ffmpeg")
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    r = out["result"]
    assert r["provides_measured"] == ["linux", "ffmpeg"]
    assert r["probe_errors"] == []
    json.dumps(out)  # the reply is one JSON line


def test_probe_keeps_every_earlier_field(box):
    r = nd.dispatch("probe", [])["result"]
    for key in ("host", "os", "agents_root", "free_gb", "ram_free_gb", "running",
                "version", "cpus", "load_per_core", "runners"):
        assert key in r, key


def test_measured_provides_is_reported_not_stored_on_the_host_row(box):
    db_mod.upsert_host("mac", os="darwin", provides=["declared_only"], status="online")
    box.binary("ffmpeg")
    nd.dispatch("probe", [])
    row = db_mod.get_host("mac")
    assert json.loads(row["provides"]) == ["declared_only"]  # the router's merge is not here
    assert "provides_measured" not in row


# ---------------------------------------------------------------------------
# chrome
# ---------------------------------------------------------------------------

def test_chrome_on_macos_is_found_under_applications(box):
    box.os("macos")
    want = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    assert want in [str(p) for p in nd._chrome_candidates()]
    assert "chrome" not in box.measured()
    box.fake_files.add(want)
    assert "chrome" in box.measured()


def test_chrome_on_macos_is_found_under_the_users_applications(box):
    box.os("macos")
    box.file(box.home / "Applications" / "Chromium.app" / "Contents" / "MacOS" / "Chromium", "x")
    assert "chrome" in box.measured()


def test_chrome_on_linux_is_the_binary_on_path(box):
    chromium = box.file(box.tmp / "usr" / "bin" / "chromium", "x")
    box.on_path["chromium"] = str(chromium)
    assert "chrome" in box.measured()


def test_no_chrome_on_linux_means_absent_without_a_child_process(box):
    assert "chrome" not in box.measured()
    assert box.children.calls == []  # existence is a stat, never a run


def test_chrome_on_windows_uses_the_program_files_dirs(box, monkeypatch):
    box.os("windows")
    pf = box.tmp / "Program Files"
    monkeypatch.setenv("PROGRAMFILES", str(pf))
    box.file(pf / "Google" / "Chrome" / "Application" / "chrome.exe", "x")
    assert "chrome" in box.measured()


def test_windows_with_no_program_dirs_in_env_builds_no_relative_candidate(box):
    box.os("windows")
    assert nd._chrome_candidates() == []
    assert box.measured() == ["windows"]


def test_a_chrome_directory_is_not_a_chrome_binary(box, monkeypatch):
    box.os("windows")
    pf = box.tmp / "pf"
    monkeypatch.setenv("PROGRAMFILES", str(pf))
    (pf / "Google" / "Chrome" / "Application" / "chrome.exe").mkdir(parents=True)
    assert "chrome" not in box.measured()


# ---------------------------------------------------------------------------
# ffmpeg, gpu, node20
# ---------------------------------------------------------------------------

def test_ffmpeg_needs_the_binary_and_an_exit_zero(box):
    assert "ffmpeg" not in box.measured()
    assert box.children.calls == []  # not on PATH: nothing is run
    path = box.binary("ffmpeg", code=0)
    assert "ffmpeg" in box.measured()
    assert box.children.calls[-1][0] == [path, "-version"]


def test_ffmpeg_that_exits_non_zero_is_absent_and_is_not_an_error(box):
    box.binary("ffmpeg", code=1)
    assert nd._measure_provides() == (["linux"], [])


def test_gpu_is_nvidia_smi_listing_a_device(box):
    box.binary("nvidia-smi", 0, "GPU 0: NVIDIA RTX 4090 (UUID: GPU-xxxx)\n")
    assert "gpu" in box.measured()
    assert box.children.calls[-1][0][1:] == ["-L"]


@pytest.mark.parametrize("code, out", [
    (0, ""), (0, "No devices were found\n"), (9, "GPU 0: x\n"), (1, "")])
def test_gpu_is_absent_when_nvidia_smi_fails_or_lists_nothing(box, code, out):
    box.binary("nvidia-smi", code, out)
    assert nd._measure_provides() == (["linux"], [])


def test_macos_without_nvidia_smi_reports_no_gpu_and_no_metal(box):
    box.os("macos")
    box.children.table["/usr/bin/security"] = (44, "")  # runner_claude: no Keychain item
    assert "gpu" not in box.measured()
    assert [c[0][0] for c in box.children.calls] == ["/usr/bin/security"]  # nvidia-smi never runs


@pytest.mark.parametrize("version, ok", [
    ("v20.0.0", True), ("v20.11.1\n", True), ("v22.3.0", True), ("v100.0.0", True),
    ("v19.9.0", False), ("v18.20.4", False), ("v8.17.0", False),
    ("", False), ("node", False), ("20.1.0", False), ("vX.1.0", False),
])
def test_node20_is_a_major_of_twenty_or_more(box, version, ok):
    box.binary("node", 0, version)
    assert ("node20" in box.measured()) is ok


def test_node_that_exits_non_zero_is_absent_even_with_a_good_looking_version(box):
    box.binary("node", 1, "v22.0.0")
    assert "node20" not in box.measured()


# ---------------------------------------------------------------------------
# playwright_chromium
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fake, tail", [
    ("macos", ("Library", "Caches", "ms-playwright")),
    ("linux", (".cache", "ms-playwright")),
])
def test_playwright_default_folder_per_os(box, fake, tail):
    box.os(fake)
    assert nd._playwright_browsers_dir() == box.home.joinpath(*tail)


def test_playwright_chromium_needs_a_chromium_build_in_the_folder(box):
    folder = box.home / ".cache" / "ms-playwright"
    (folder / "firefox-1490").mkdir(parents=True)
    assert "playwright_chromium" not in box.measured()  # the folder exists; chromium is not in it
    (folder / "chromium-1129").mkdir()
    assert "playwright_chromium" in box.measured()


def test_playwright_with_no_folder_is_absent(box):
    assert "playwright_chromium" not in box.measured()


def test_playwright_browsers_path_override_is_used(box, monkeypatch):
    other = box.tmp / "pw"
    (other / "chromium_headless_shell-1129").mkdir(parents=True)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(other))
    assert "playwright_chromium" in box.measured()


def test_playwright_browsers_path_zero_means_no_shared_folder(box, monkeypatch):
    (box.home / ".cache" / "ms-playwright" / "chromium-1").mkdir(parents=True)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "0")
    assert "playwright_chromium" not in box.measured()


def test_playwright_on_windows_reads_localappdata_and_survives_its_absence(box, monkeypatch):
    box.os("windows")
    assert "playwright_chromium" not in box.measured()  # LOCALAPPDATA unset: no crash
    local = box.tmp / "Local"
    (local / "ms-playwright" / "chromium-1129").mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    assert "playwright_chromium" in box.measured()


# ---------------------------------------------------------------------------
# signed-in runners: a file's existence and size, nothing else
# ---------------------------------------------------------------------------

def _claude(box) -> Path:
    return box.home / ".claude" / ".credentials.json"


def _codex(box) -> Path:
    return box.home / ".codex" / "auth.json"


def _agy(box) -> Path:
    return box.home / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"


@pytest.mark.parametrize("name, where", [
    ("runner_claude", _claude), ("runner_codex", _codex), ("runner_agy", _agy)])
def test_a_runner_is_signed_in_when_its_credential_file_has_bytes(box, name, where):
    assert name not in box.measured()
    box.file(where(box), "")
    assert name not in box.measured()  # empty file: not signed in
    box.file(where(box), SECRET)
    assert name in box.measured()


@pytest.mark.parametrize("where", [_claude, _codex, _agy])
def test_a_directory_at_the_credential_path_is_not_a_login(box, where):
    where(box).mkdir(parents=True)
    assert not [n for n in box.measured() if n.startswith("runner_")]


def test_claude_and_codex_follow_their_config_dir_variables(box, monkeypatch):
    cfg, codex_home = box.tmp / "cfg", box.tmp / "codex-home"
    box.file(cfg / ".credentials.json")
    box.file(codex_home / "auth.json")
    assert [n for n in box.measured() if n.startswith("runner_")] == []  # HOME has none
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    assert [n for n in box.measured() if n.startswith("runner_")] == ["runner_claude", "runner_codex"]


class Tripwire:
    """`hits` is every attempt to open a credential file while `armed`."""

    def __init__(self) -> None:
        self.armed = False
        self.hits: list[str] = []


@pytest.fixture
def credential_paths_explode(monkeypatch, box) -> Tripwire:
    """open(), io.open(), os.open(), Path.open/read_text/read_bytes raise for the
    three credential paths and record the attempt, once `.armed` is set (a test
    writes its fake credential files first). Other files open normally."""
    guarded = {str(p) for p in (_claude(box), _codex(box), _agy(box))}
    trip = Tripwire()
    hits = trip.hits

    def is_guarded(target) -> bool:
        try:
            return trip.armed and os.fspath(target) in guarded
        except TypeError:
            return False

    def wrap(real):
        def inner(target, *a, **kw):
            if is_guarded(target):
                hits.append(os.fspath(target))
                raise AssertionError(f"credential file was opened: {target}")
            return real(target, *a, **kw)
        return inner

    monkeypatch.setattr(builtins, "open", wrap(builtins.open))
    monkeypatch.setattr(io, "open", wrap(io.open))
    monkeypatch.setattr(os, "open", wrap(os.open))
    for meth in ("open", "read_text", "read_bytes"):
        real = getattr(Path, meth)

        def guard(self, *a, _real=real, _meth=meth, **kw):
            if is_guarded(self):
                hits.append(str(self))
                raise AssertionError(f"credential file was read via Path.{_meth}: {self}")
            return _real(self, *a, **kw)

        monkeypatch.setattr(Path, meth, guard)
    return trip


def test_no_credential_file_is_opened_read_or_echoed(box, credential_paths_explode):
    for where in (_claude, _codex, _agy):
        box.file(where(box), SECRET)
    credential_paths_explode.armed = True  # the files are written; from here none may be opened
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert {"runner_claude", "runner_codex", "runner_agy"} <= set(out["result"]["provides_measured"])
    assert credential_paths_explode.hits == []  # the tripwire was never touched
    assert SECRET not in json.dumps(out)
    assert out["result"]["probe_errors"] == []


def test_the_credential_tripwire_itself_fires(box, credential_paths_explode):
    target = box.file(_claude(box), SECRET)
    credential_paths_explode.armed = True
    with pytest.raises(AssertionError):
        target.read_text()
    with pytest.raises(AssertionError):
        open(target)
    assert len(credential_paths_explode.hits) == 2


def test_the_detector_source_never_opens_or_reads_a_file():
    tree = ast.parse((ROOT / "tools" / "node_dispatch.py").read_text(encoding="utf-8"))
    names = {"_file_has_content", "_claude_credentials", "_codex_credentials",
             "_agy_credentials", "_measure_provides"}
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {f.name for f in funcs} == names
    table = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", "") == "_PROVIDES_DETECTORS" for t in n.targets))
    bad = []
    for node in [*funcs, table]:
        for call in (c for c in ast.walk(node) if isinstance(c, ast.Call)):
            f = call.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if name in ("open", "read_text", "read_bytes", "file_digest", "sha256", "md5", "sha1"):
                bad.append(name)
    assert bad == []


# ---------------------------------------------------------------------------
# a detector that fails, raises or hangs
# ---------------------------------------------------------------------------

def test_a_child_that_hangs_is_bounded_and_named_once(box):
    path = box.binary("ffmpeg")
    box.children.table[path] = subprocess.TimeoutExpired([path, "-version"], 5)
    box.binary("node", 0, "v22.0.0")
    measured, errors = nd._measure_provides()
    assert measured == ["linux", "node20"]  # ffmpeg left out, the rest still measured
    assert errors == ["ffmpeg: TimeoutExpired"]
    for argv, kw in box.children.calls:
        assert 0 < kw["timeout"] <= 5
        assert kw["timeout"] == nd.PROBE_CHILD_TIMEOUT_S


def test_a_child_that_cannot_start_is_one_error_entry(box):
    path = box.binary("nvidia-smi")
    box.children.table[path] = PermissionError(13, "denied", path)
    assert nd._measure_provides() == (["linux"], ["gpu: PermissionError"])


def test_a_detector_that_raises_is_absent_and_the_probe_still_answers(box, monkeypatch):
    def explode():
        raise RuntimeError("secret detail /home/x/.claude")

    monkeypatch.setattr(nd, "_PROVIDES_DETECTORS", (
        ("chrome", explode), ("ffmpeg", lambda: True), ("gpu", explode)))
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert out["result"]["provides_measured"] == ["linux", "ffmpeg"]
    assert out["result"]["probe_errors"] == ["chrome: RuntimeError", "gpu: RuntimeError"]
    assert "secret detail" not in json.dumps(out)  # the type name only, never the message


def test_every_detector_failing_still_leaves_a_working_probe(box, monkeypatch):
    def explode():
        raise OSError("disk gone")

    monkeypatch.setattr(nd, "_PROVIDES_DETECTORS", tuple((n, explode) for n in ALL_NAMES))
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert out["result"]["provides_measured"] == ["linux"]
    assert out["result"]["probe_errors"] == [f"{n}: OSError" for n in ALL_NAMES]


def test_the_probe_never_raises_when_every_child_is_unplanned(box):
    # On PATH but with no table entry: the recorder raises AssertionError on the
    # first child. A detector must turn that into one error entry, not a crash.
    box.on_path.update({"ffmpeg": "/x/ffmpeg", "nvidia-smi": "/x/nvidia-smi", "node": "/x/node"})
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert out["result"]["provides_measured"] == ["linux"]
    assert out["result"]["probe_errors"] == [
        "ffmpeg: AssertionError", "gpu: AssertionError", "node20: AssertionError"]


def test_no_child_is_run_through_a_shell_or_with_stdin(box):
    box.binary("ffmpeg")
    box.binary("nvidia-smi", 0, "GPU 0: x\n")
    box.binary("node", 0, "v22.0.0")
    box.measured()
    assert len(box.children.calls) == 3
    for argv, kw in box.children.calls:
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        assert not kw.get("shell")
        assert kw["stdin"] == subprocess.DEVNULL
        assert kw["stderr"] == subprocess.DEVNULL


def test_ffmpeg_keeps_no_stdout_pipe_open(box):
    box.binary("ffmpeg")
    box.measured()
    assert box.children.calls[-1][1]["stdout"] == subprocess.DEVNULL


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def test_probe_on_windows_measures_with_windows_paths_and_does_not_crash(box, monkeypatch):
    box.os("windows")
    monkeypatch.delattr(nd.os, "getloadavg", raising=False)  # absent on Windows
    pf = box.tmp / "Program Files"
    local = box.tmp / "Local"
    monkeypatch.setenv("PROGRAMFILES", str(pf))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    box.file(pf / "Google" / "Chrome" / "Application" / "chrome.exe", "x")
    (local / "ms-playwright" / "chromium-1129").mkdir(parents=True)
    box.file(box.home / ".claude" / ".credentials.json")
    box.binary("ffmpeg")
    box.binary("node", 0, "v20.18.0")
    box.binary("nvidia-smi", 0, "GPU 0: NVIDIA GeForce RTX 3060\n")

    out = nd.dispatch("probe", [])

    assert out["ok"] is True, out
    r = out["result"]
    assert r["os"] == "windows"
    assert r["provides_measured"] == [
        "windows", "chrome", "ffmpeg", "gpu", "node20", "playwright_chromium", "runner_claude"]
    assert r["probe_errors"] == []


def test_probe_on_a_bare_windows_box_reports_only_windows(box, monkeypatch):
    box.os("windows")
    monkeypatch.delattr(nd.os, "getloadavg", raising=False)
    out = nd.dispatch("probe", [])
    assert out["ok"] is True, out
    assert out["result"]["provides_measured"] == ["windows"]
    assert out["result"]["probe_errors"] == []
