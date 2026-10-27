"""Media choice cards on the requester side: `ask_run.py ask --media/--caption/--pick`, the MCP
`ask_ceo(media, pick)` and the `picked:` line of `wait` (docs/design/run-inbox/QUESTIONS.md §11).

What these tests hold the requester to:
  - every local refusal happens BEFORE any HTTP call (the hub saw 0 requests) and before any
    upload: a wrong type (read from the bytes, never the name), a symlink/FIFO/directory, 13
    items, a missing or wrong --pick, a caption or file name that is command-shaped, money or a
    secret, a file over its cap after the shrink, no ffmpeg;
  - every item is staged and checked before the FIRST upload, uploads come before the create,
    a video's poster is uploaded too and sent as poster_id, the temp dir is gone afterwards;
  - the hub's answer to an upload must agree with what was sent, and its 507 text is printed as is;
  - `wait` prints the picked: line for every answer shape and refuses a picks list that does not
    fit the card (fail closed, QUESTIONS.md §1.3).

ffmpeg and ffprobe are replaced by a recorder for most cases (no CPU, no RAM on a shared box); one
test runs the real tools on tiny generated files and is skipped when they are not installed.
Token-shaped fixtures are assembled at runtime (_val / _shape) so gitleaks never sees one.

Run: .venv/bin/python -m pytest tests/test_ask_run_media.py
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.ask_run as ask_run  # noqa: E402
from test_ask_run import FakeHub, _Handler, _sealed, _shape, _val  # noqa: E402, F401  (_sealed is autouse)
from test_ask_run_questions import ANSWER, CREATED, QID, QPATH, SHA, _record  # noqa: E402

CREATE_PATH = "/api/run/questions"
MEDIA_PATH = "/api/run/question-media"

HEADS = {
    "jpeg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00",
    "png": b"\x89PNG\r\n\x1a\n",
    "gif": b"GIF89a",
    "webp": b"RIFF\x00\x00\x00\x00WEBPVP8 ",
    "wav": b"RIFF\x00\x00\x00\x00WAVEfmt ",
    "mp4": b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00",
    "mov": b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00",
    "m4a": b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00",
    "webm": b"\x1a\x45\xdf\xa3\x9f",
    "ogg": b"OggS\x00\x02",
    "mp3": b"ID3\x04\x00",
    "aac": b"\xff\xf1\x50\x80",
}


def blob(fmt: str, size: int = 64) -> bytes:
    head = HEADS[fmt]
    return head + b"\x00" * max(0, size - len(head))


def put(tmp_path: Path, name: str, data: bytes) -> str:
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


# ------------------------------------------------------------- fake ffmpeg / ffprobe
class FakeTools:
    """Stands in for ask_run._run_tool: ffprobe answers from `probe` (by file name, else from the
    file's own type), ffmpeg writes a file of the right type at the last argument. Every command is
    recorded. `out_size` sets how many bytes an output of that type has (default 200)."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.probe: dict[str, dict] = {}
        self.out_size: dict[str, int] = {}
        self.fail: set[str] = set()

    @staticmethod
    def _default_info(path: str) -> dict:
        with open(path, "rb") as f:
            fmt = ask_run.sniff_media(f.read(64))
        kind = ask_run.MEDIA_FORMATS[fmt][0] if fmt else "image"
        if kind == "image":
            return {"streams": [{"codec_type": "video", "codec_name": "mjpeg", "width": 100, "height": 100}]}
        if kind == "video":
            return {"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"}]}
        return {"streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}]}

    def __call__(self, cmd, timeout):
        self.calls.append(list(cmd))
        tool = os.path.basename(cmd[0])
        if tool in self.fail:
            return subprocess.CompletedProcess(cmd, 1, b"", b"Invalid data found when processing input")
        if tool == "ffprobe":
            path = cmd[cmd.index("-i") + 1].removeprefix("file:")
            info = self.probe.get(os.path.basename(path)) or self._default_info(path)
            return subprocess.CompletedProcess(cmd, 0, json.dumps(info).encode(), b"")
        out = Path(cmd[-1])
        if out.name.endswith((".jpg", ".jpeg")):
            fmt = "jpeg"
        elif out.suffix == ".webp":
            fmt = "webp"
        elif out.suffix == ".mp4":
            fmt = "mp4"
        else:
            fmt = "m4a"
        out.write_bytes(blob(fmt, self.out_size.get(fmt, 200)))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    def ffmpeg_calls(self) -> list[list[str]]:
        return [c for c in self.calls if os.path.basename(c[0]) == "ffmpeg"]

    def probe_calls(self) -> list[list[str]]:
        return [c for c in self.calls if os.path.basename(c[0]) == "ffprobe"]


@pytest.fixture
def tools(monkeypatch):
    fake = FakeTools()
    monkeypatch.setattr(ask_run, "find_ffmpeg", lambda: ("ffmpeg", "ffprobe"))
    monkeypatch.setattr(ask_run, "_run_tool", fake)
    return fake


@pytest.fixture
def stage(monkeypatch, tmp_path):
    """The temp dir the tool stages into; after a run it must be empty again."""
    base = tmp_path / "stage"
    base.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(base))
    return base


# ------------------------------------------------------------- fake hub that takes raw uploads
class _MediaHandler(_Handler):
    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if path != MEDIA_PATH:
            self._handle(json.loads(raw) if raw else None)
            return
        hub = self.server.hub  # type: ignore[attr-defined]
        auth = self.headers.get("Authorization")
        session = self.headers.get("X-Run-Session")
        hub.requests.append({"method": "POST", "path": path, "query": {}, "auth": auth, "body": None,
                             "ctype": self.headers.get("Content-Type"), "name": self.headers.get("X-Media-Name"),
                             "length": self.headers.get("Content-Length"), "session": session, "data": raw})
        if auth != f"Bearer {hub.token}":
            self._reply(401, b'{"error":"unauthorized"}', "application/json")
            return
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", session or ""):   # the Console's SEGMENT
            self._reply(400, b'{"error":"invalid_requester_session"}', "application/json")
            return
        if ("POST", path) in hub.routes:                    # a test scripted this answer
            status, payload = hub.answer("POST", path)
            self._reply(status, json.dumps(payload).encode(), "application/json")
            return
        hub.count += 1
        fmt = ask_run.sniff_media(raw[:64])
        reply = {"media_id": "M-%024x" % hub.count, "kind": ask_run.MEDIA_FORMATS[fmt][0] if fmt else "image",
                 "mime": "application/octet-stream", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        hub.uploads[reply["media_id"]] = raw
        self._reply(201, json.dumps(reply).encode(), "application/json")


@pytest.fixture
def mhub(monkeypatch):
    fake = FakeHub()
    fake.count = 0                                          # type: ignore[attr-defined]
    fake.uploads = {}                                       # type: ignore[attr-defined]
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MediaHandler)
    server.hub = fake  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    fake.url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("RUN_INBOX_URL", fake.url)
    monkeypatch.setenv("RUN_INBOX_TOKEN", fake.token)
    fake.on("POST", CREATE_PATH, (201, CREATED))
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def uploads(hub: FakeHub) -> list[dict]:
    return [r for r in hub.requests if r["path"] == MEDIA_PATH]


# ------------------------------------------------------------- argv helpers
def ask(*extra: str, question: str = "Which cover?", why: str = "Pick the cover for episode 3") -> list[str]:
    return ["ask", "--question", question, "--why", why, *extra,
            "--session", "cto-t", "--role", "cto", "--host", "contabo"]


def media_args(paths, captions=(), pick: str | None = None) -> list[str]:
    argv: list[str] = []
    for p in paths:
        argv += ["--media", p]
    for c in captions:
        argv += ["--caption", c]
    if pick:
        argv += ["--pick", pick]
    return argv


def refused(capsys) -> str:
    err = capsys.readouterr().err
    lines = [ln for ln in err.strip().splitlines() if ln.startswith("ask_run: refused: ")]
    assert len(lines) == 1, err
    return lines[0].removeprefix("ask_run: refused: ")


def code_of(message: str) -> str:
    return message.split(":", 1)[0]


# ================================================================== the type comes from the bytes
@pytest.mark.parametrize("fmt, expected", [
    ("jpeg", "jpeg"), ("png", "png"), ("gif", "gif"), ("webp", "webp"), ("wav", "wav"), ("mp4", "mp4"),
    ("mov", "mov"), ("m4a", "m4a"), ("webm", "webm"), ("ogg", "ogg"), ("mp3", "mp3"), ("aac", "aac"),
])
def test_sniff_accepts_every_listed_type(fmt, expected):
    assert ask_run.sniff_media(blob(fmt)) == expected


def test_sniff_reads_a_bare_mp3_frame_and_tells_adts_from_it():
    assert ask_run.sniff_media(b"\xff\xfb\x90\x00" + b"\0" * 20) == "mp3"
    assert ask_run.sniff_media(b"\xff\xf1\x50\x80" + b"\0" * 20) == "aac"


@pytest.mark.parametrize("data", [
    b"<!DOCTYPE html><html><body>hi</body></html>",
    b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>',
    b"<svg xmlns='http://www.w3.org/2000/svg' onload='x()'/>",
    b"%PDF-1.7\n",
    b"PK\x03\x04" + b"\0" * 30,
    b"\x00\x00\x00\x18ftypheic" + b"\0" * 20,        # a brand outside the two lists
    b"RIFF\x00\x00\x00\x00AVI LIST",
    b"", b"\x00", b"MZ\x90\x00",
])
def test_sniff_refuses_everything_else(data):
    assert ask_run.sniff_media(data) is None


# ================================================================== local refusals, before any call
def _symlink(tmp_path):
    real = put(tmp_path, "real.png", blob("png"))
    link = tmp_path / "link.png"
    link.symlink_to(real)
    return str(link)


def _fifo(tmp_path):
    path = tmp_path / "pipe.png"
    os.mkfifo(path)
    return str(path)


FILE_REFUSALS = [
    ("html named jpg", lambda t: put(t, "cover.jpg", b"<!DOCTYPE html><html></html>"), "unsupported_media", "cover.jpg"),
    ("svg named png", lambda t: put(t, "logo.png", b'<?xml version="1.0"?><svg/>'), "unsupported_media", "logo.png"),
    ("pdf named mp4", lambda t: put(t, "clip.mp4", b"%PDF-1.4\n"), "unsupported_media", "clip.mp4"),
    ("empty file", lambda t: put(t, "empty.png", b""), "invalid_media", "empty"),
    ("a directory", lambda t: str(t), "invalid_media", "not a regular file"),
    ("missing file", lambda t: str(t / "nope.png"), "invalid_media", "does not exist"),
    ("a symlink", _symlink, "invalid_media", "symlink"),
    ("a fifo", _fifo, "invalid_media", "not a regular file"),
]


@pytest.mark.parametrize("label, make, code, snippet", FILE_REFUSALS, ids=[r[0] for r in FILE_REFUSALS])
def test_a_bad_file_is_refused_before_anything_is_sent(mhub, tools, stage, tmp_path, capsys, label, make, code, snippet):
    good = put(tmp_path, "good.png", blob("png"))
    bad = make(tmp_path)
    assert ask_run.main(ask(*media_args([good, bad], pick="one"))) == 2
    message = refused(capsys)
    assert code_of(message) == code and snippet in message and "media[1]" in message
    assert mhub.requests == []                       # no upload of the good one either
    assert list(stage.iterdir()) == []


def test_a_wrong_type_is_decided_by_the_first_bytes_not_the_name(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "photo.html", blob("png"))   # a PNG with a web-page name is fine
    assert ask_run.main(ask(*media_args([path]), "--dry-run")) == 0
    assert "image" in capsys.readouterr().err


def test_thirteen_items_are_refused_and_nothing_is_probed(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, f"p{i}.png", blob("png")) for i in range(13)]
    assert ask_run.main(ask(*media_args(paths, pick="one"))) == 2
    assert code_of(refused(capsys)) == "too_many_media"
    assert mhub.requests == [] and tools.calls == []


def test_twelve_items_are_fine(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, f"p{i}.png", blob("png")) for i in range(12)]
    assert ask_run.main(ask(*media_args(paths, pick="many"), "--dry-run")) == 0
    body = json.loads(capsys.readouterr().out)
    assert len(body["media"]) == 12 and body["pick"] == "many"


PICK_RULES = [
    ("two items need --pick", 2, [], "pick_required"),
    ("three items need --pick", 3, [], "pick_required"),
    ("--pick many on one item", 1, ["--pick", "many"], "invalid_pick"),
    ("--pick bogus", 2, ["--pick", "all"], "invalid_pick"),
    ("--option with a set", 2, ["--pick", "one", "--option", "A", "--option", "B"], "options_not_allowed"),
    ("--recommended with a set", 2, ["--pick", "one", "--recommended", "1"], "invalid_options"),
    ("--no-free-text on a media card", 2, ["--pick", "one", "--no-free-text"], "invalid_free_text"),
    ("--pick without media", 0, ["--pick", "one", "--option", "A", "--option", "B"], "invalid_media"),
    ("--caption without media", 0, ["--caption", "x", "--option", "A", "--option", "B"], "invalid_media"),
]


@pytest.mark.parametrize("label, n, extra, code", PICK_RULES, ids=[r[0] for r in PICK_RULES])
def test_pick_and_option_rules(mhub, tools, stage, tmp_path, capsys, label, n, extra, code):
    paths = [put(tmp_path, f"p{i}.png", blob("png")) for i in range(n)]
    assert ask_run.main(ask(*media_args(paths), *extra)) == 2
    assert code_of(refused(capsys)) == code
    assert mhub.requests == []


def test_one_item_needs_no_pick_and_takes_the_hub_default_options(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "cover.png", blob("png"))
    assert ask_run.main(ask(*media_args([path], ["the cover"]), "--dry-run")) == 0
    body = json.loads(capsys.readouterr().out)
    assert "options" not in body and "pick" not in body
    assert body["free_text"] is True and body["media"] == [{"id": ask_run.PENDING_MEDIA_ID, "caption": "the cover"}]


def test_one_item_may_bring_its_own_options_and_pick_one(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "cover.png", blob("png"))
    assert ask_run.main(ask(*media_args([path], pick="one"), "--option", "Ship it", "--option", "Redo it",
                            "--recommended", "1", "--dry-run")) == 0
    body = json.loads(capsys.readouterr().out)
    assert [o["label"] for o in body["options"]] == ["Ship it", "Redo it"] and body["pick"] == "one"


def test_a_plain_card_still_needs_its_options(mhub, capsys):
    with pytest.raises(SystemExit) as exc:                 # argparse's own usage error, as before
        ask_run.main(ask())
    assert exc.value.code == 2 and "--option" in capsys.readouterr().err
    assert mhub.requests == []


def test_body_key_order_of_a_set_card(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, "a.png", blob("png")), put(tmp_path, "b.mp4", blob("mp4"))]
    assert ask_run.main(ask(*media_args(paths, ["", "clip"], "one"), "--dry-run")) == 0
    body = json.loads(capsys.readouterr().out)
    assert list(body) == ["question", "why", "free_text", "expires_in_s", "requester", "media", "pick"]
    assert body["media"] == [{"id": ask_run.PENDING_MEDIA_ID},
                             {"id": ask_run.PENDING_MEDIA_ID, "caption": "clip", "poster_id": ask_run.PENDING_MEDIA_ID}]


CAPTION_RULES = [
    ("too long", ["x" * 61], "invalid_caption"),
    ("two lines", ["one\ntwo"], "invalid_caption"),
    ("zero-width", ["a​b"], "invalid_caption"),
    ("bidi mark", ["a‮b"], "invalid_caption"),
    ("command", ["sudo systemctl restart nginx"], "command_shaped"),
    ("flag", ["use git push --force"], "command_shaped"),
    ("money", ["pay $50 for this one"], "money_needs_command_card"),
    ("more captions than items", ["a", "b", "c"], "invalid_media"),
]


@pytest.mark.parametrize("label, captions, code", CAPTION_RULES, ids=[r[0] for r in CAPTION_RULES])
def test_caption_rules(mhub, tools, stage, tmp_path, capsys, label, captions, code):
    paths = [put(tmp_path, "a.png", blob("png")), put(tmp_path, "b.png", blob("png"))]
    assert ask_run.main(ask(*media_args(paths, captions, "one"))) == 2
    assert code_of(refused(capsys)) == code
    assert mhub.requests == []


def test_a_caption_of_exactly_sixty_characters_passes(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, "a.png", blob("png")), put(tmp_path, "b.png", blob("png"))]
    assert ask_run.main(ask(*media_args(paths, ["x" * 60], "one"), "--dry-run")) == 0
    assert json.loads(capsys.readouterr().out)["media"][0]["caption"] == "x" * 60


def test_a_secret_shaped_caption_is_refused_and_not_echoed(mhub, tools, stage, tmp_path, capsys):
    secret = _shape(("gh", "p_"), _val(36))
    paths = [put(tmp_path, "a.png", blob("png")), put(tmp_path, "b.png", blob("png"))]
    assert ask_run.main(ask(*media_args(paths, [secret], "one"))) == 2
    err = capsys.readouterr().err
    assert "secret_shaped_value" in err and secret not in err
    assert mhub.requests == []


def test_a_secret_shaped_file_name_is_refused_and_not_echoed(mhub, tools, stage, tmp_path, capsys):
    secret = _shape(("gh", "p_"), _val(36))
    path = put(tmp_path, secret + ".png", blob("png"))
    assert ask_run.main(ask(*media_args([path]))) == 2
    err = capsys.readouterr().err
    assert "secret_shaped_value" in err and secret not in err
    assert mhub.requests == []


def test_a_command_shaped_file_name_is_refused(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "sudo reboot now.png", blob("png"))
    assert ask_run.main(ask(*media_args([path]))) == 2
    message = refused(capsys)
    assert code_of(message) == "command_shaped" and "file name" in message and "rename the file" in message
    assert mhub.requests == []


def test_the_question_and_why_keep_their_own_checks_on_a_media_card(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "a.png", blob("png"))
    assert ask_run.main(ask(*media_args([path]), question="Run `rm -rf /` now?")) == 2
    assert code_of(refused(capsys)) == "command_shaped"
    assert ask_run.main(ask(*media_args([path]), why="")) == 2
    assert code_of(refused(capsys)) == "why_required"


def test_a_worker_cannot_post_a_media_card(mhub, tools, stage, tmp_path, monkeypatch, capsys):
    path = put(tmp_path, "a.png", blob("png"))
    argv = ask(*media_args([path]))
    argv[argv.index("--role") + 1] = "dev"
    assert ask_run.main(argv) == 2
    assert code_of(refused(capsys)) == "question_needs_c_level"
    assert mhub.requests == []


def test_batch_cannot_carry_media(mhub, tmp_path, capsys):
    batch = tmp_path / "b.json"
    batch.write_text(json.dumps([{"question": "q", "why": "w", "options": ["a", "b"]}]))
    for flag in (["--media", str(tmp_path / "x.png")], ["--caption", "x"], ["--pick", "one"]):
        with pytest.raises(SystemExit) as exc:
            ask_run.main(["ask", "--batch", str(batch), *flag, "--session", "cto-t", "--role", "cto",
                          "--host", "contabo"])
        err = capsys.readouterr().err
        assert exc.value.code == 2 and "--batch" in err and flag[0] in err
    assert mhub.requests == []


# ================================================================== the shrink (§11.2) and the caps
def _dry(tmp_path, capsys, paths, pick="many"):
    rc = ask_run.main(ask(*media_args(paths, pick=pick), "--dry-run"))
    return rc, capsys.readouterr()


def test_caps_are_the_contract_numbers():
    assert ask_run.MEDIA_CAPS == {"image": 10 * 1024 * 1024, "video": 50 * 1024 * 1024, "audio": 20 * 1024 * 1024}
    assert (ask_run.MEDIA_MAX, ask_run.CAPTION_MAX, ask_run.IMAGE_EDGE, ask_run.VIDEO_HEIGHT) == (12, 60, 2048, 720)


def test_a_big_picture_is_shrunk_to_2048_and_a_small_one_is_left_alone(mhub, tools, stage, tmp_path, capsys):
    big = put(tmp_path, "big.png", blob("png", 400))
    small = put(tmp_path, "small.jpg", blob("jpeg", 400))
    tools.probe["big.png"] = {"streams": [{"codec_type": "video", "width": 3000, "height": 2000}]}
    rc, out = _dry(tmp_path, capsys, [big, small])
    assert rc == 0
    cmds = tools.ffmpeg_calls()
    assert len(cmds) == 1                              # only the big one is converted
    cmd = cmds[0]
    assert "scale=w=2048:h=2048:force_original_aspect_ratio=decrease" in cmd
    assert cmd[cmd.index("-c:v") + 1] == "mjpeg" and cmd[-1].endswith(".jpg")
    assert "3000x2000 shrunk to 2048 px" in out.err


def test_a_webp_stays_a_webp_when_shrunk(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "wide.webp", blob("webp", 400))
    tools.probe["wide.webp"] = {"streams": [{"codec_type": "video", "width": 4000, "height": 3000}]}
    assert _dry(tmp_path, capsys, [path], pick="one")[0] == 0
    cmd = tools.ffmpeg_calls()[0]
    assert cmd[cmd.index("-c:v") + 1] == "libwebp" and cmd[-1].endswith(".webp")


def test_a_picture_over_100_megapixels_is_refused(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "bomb.png", blob("png", 400))
    tools.probe["bomb.png"] = {"streams": [{"codec_type": "video", "width": 20000, "height": 10000}]}
    assert ask_run.main(ask(*media_args([path]))) == 2
    assert "megapixels" in refused(capsys) and tools.ffmpeg_calls() == []


def test_a_1080p_video_becomes_720p_h264_with_faststart_and_a_poster(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "clip.mp4", blob("mp4", 400))
    assert _dry(tmp_path, capsys, [path], pick="one")[0] == 0
    convert, poster = tools.ffmpeg_calls()
    joined = " ".join(convert)
    assert "scale=-2:'min(720,ih)'" in joined and "libx264" in joined and "-movflags +faststart" in joined
    assert convert[convert.index("-c:a") + 1] == "aac"
    assert "-ss 0.5" in " ".join(poster) and poster[-1].endswith(".poster.jpg")
    assert poster[poster.index("-c:v") + 1] == "mjpeg"


def test_a_compliant_720p_mp4_is_only_rewrapped(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "ok.mp4", blob("mp4", 400))
    tools.probe["ok.mp4"] = {"streams": [
        {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1280, "height": 720},
        {"codec_type": "audio", "codec_name": "aac"}]}
    assert _dry(tmp_path, capsys, [path], pick="one")[0] == 0
    convert = tools.ffmpeg_calls()[0]
    assert convert[convert.index("-c") + 1] == "copy" and "+faststart" in convert
    assert "libx264" not in " ".join(convert)


@pytest.mark.parametrize("fmt, streams", [
    ("webm", [{"codec_type": "video", "codec_name": "vp9", "width": 640, "height": 360}]),
    ("mov", [{"codec_type": "video", "codec_name": "prores", "pix_fmt": "yuv422p10le", "width": 640, "height": 360}]),
    ("mp4", [{"codec_type": "video", "codec_name": "hevc", "pix_fmt": "yuv420p", "width": 640, "height": 360}]),
    ("mp4", [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 640, "height": 360},
             {"codec_type": "audio", "codec_name": "mp3"}]),
])
def test_a_video_that_is_not_h264_aac_mp4_is_transcoded(mhub, tools, stage, tmp_path, capsys, fmt, streams):
    path = put(tmp_path, f"v.{fmt}", blob(fmt, 400))
    tools.probe[f"v.{fmt}"] = {"streams": streams}
    assert _dry(tmp_path, capsys, [path], pick="one")[0] == 0
    assert "libx264" in " ".join(tools.ffmpeg_calls()[0])


def test_wav_and_ogg_become_m4a_and_mp3_aac_m4a_pass_through(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, "voice.wav", blob("wav", 400)), put(tmp_path, "take.ogg", blob("ogg", 400)),
             put(tmp_path, "song.mp3", blob("mp3", 400)), put(tmp_path, "a.aac", blob("aac", 400)),
             put(tmp_path, "b.m4a", blob("m4a", 400))]
    assert _dry(tmp_path, capsys, paths)[0] == 0
    converts = tools.ffmpeg_calls()
    assert len(converts) == 2
    for cmd in converts:
        assert cmd[cmd.index("-c:a") + 1] == "aac" and cmd[cmd.index("-b:a") + 1] == "128k"
        assert cmd[-1].endswith(".m4a") and "-vn" in cmd


def test_every_tool_call_is_locked_to_the_file_protocol_and_two_threads(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, "a.png", blob("png", 400)), put(tmp_path, "v.mp4", blob("mp4", 400)),
             put(tmp_path, "w.wav", blob("wav", 400))]
    tools.probe["a.png"] = {"streams": [{"codec_type": "video", "width": 3000, "height": 2000}]}
    assert _dry(tmp_path, capsys, paths)[0] == 0
    assert len(tools.probe_calls()) == 3 and len(tools.ffmpeg_calls()) == 4   # a, v + poster, w
    for cmd in tools.calls:
        assert cmd[cmd.index("-protocol_whitelist") + 1] == "file"
        assert any(a.startswith("file:") for a in cmd)
    for cmd in tools.probe_calls():
        assert cmd[cmd.index("-f") + 1] in {"png_pipe", "mov", "wav"}          # the sniffed type, forced
    for cmd in tools.ffmpeg_calls():
        assert cmd[cmd.index("-threads") + 1] == "2" and "-nostdin" in cmd and "-fs" in cmd


def test_caps_hold_for_what_is_uploaded_not_for_the_source(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setitem(ask_run.MEDIA_CAPS, "image", 1000)
    path = put(tmp_path, "huge.png", blob("png", 4000))               # over the cap as it is ...
    tools.probe["huge.png"] = {"streams": [{"codec_type": "video", "width": 3000, "height": 2000}]}
    tools.out_size["jpeg"] = 500                                      # ... but 500 bytes after the shrink
    assert _dry(tmp_path, capsys, [path], pick="one")[0] == 0


def test_a_picture_over_its_cap_after_the_shrink_is_refused(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setitem(ask_run.MEDIA_CAPS, "image", 1000)
    path = put(tmp_path, "huge.png", blob("png", 4000))
    tools.probe["huge.png"] = {"streams": [{"codec_type": "video", "width": 3000, "height": 2000}]}
    tools.out_size["jpeg"] = 5000
    assert ask_run.main(ask(*media_args([path]))) == 2
    message = refused(capsys)
    assert code_of(message) == "too_large" and "after the shrink" in message and "media[0] huge.png" in message
    assert mhub.requests == [] and list(stage.iterdir()) == []


def test_a_small_picture_over_its_cap_as_it_is_is_refused(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setitem(ask_run.MEDIA_CAPS, "image", 1000)
    path = put(tmp_path, "fat.jpg", blob("jpeg", 3000))
    assert ask_run.main(ask(*media_args([path]))) == 2
    message = refused(capsys)
    assert code_of(message) == "too_large" and "as it is" in message
    assert mhub.requests == []


def test_a_video_over_its_cap_after_transcoding_says_how_to_cut_it(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setitem(ask_run.MEDIA_CAPS, "video", 1000)
    path = put(tmp_path, "long.mp4", blob("mp4", 400))
    tools.out_size["mp4"] = 5000
    assert ask_run.main(ask(*media_args([path]))) == 2
    message = refused(capsys)
    assert code_of(message) == "too_large" and "ffmpeg -i" in message
    assert mhub.requests == []


def test_a_sound_over_its_cap_is_refused(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setitem(ask_run.MEDIA_CAPS, "audio", 1000)
    path = put(tmp_path, "long.mp3", blob("mp3", 5000))
    assert ask_run.main(ask(*media_args([path]))) == 2
    assert code_of(refused(capsys)) == "too_large"


def test_a_video_without_a_picture_and_a_sound_without_audio_are_refused(mhub, tools, stage, tmp_path, capsys):
    v = put(tmp_path, "v.mp4", blob("mp4", 400))
    tools.probe["v.mp4"] = {"streams": [{"codec_type": "audio", "codec_name": "aac"}]}
    assert ask_run.main(ask(*media_args([v]))) == 2
    assert "no picture track" in refused(capsys)
    a = put(tmp_path, "a.wav", blob("wav", 400))
    tools.probe["a.wav"] = {"streams": [{"codec_type": "video", "width": 10, "height": 10}]}
    assert ask_run.main(ask(*media_args([a]))) == 2
    assert "no sound track" in refused(capsys)


def test_an_ffmpeg_failure_is_a_refusal_and_cleans_up(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "v.mp4", blob("mp4", 400))
    tools.fail.add("ffmpeg")
    assert ask_run.main(ask(*media_args([path]))) == 2
    assert code_of(refused(capsys)) == "invalid_media"
    assert mhub.requests == [] and list(stage.iterdir()) == []


def test_ffprobe_failure_means_the_file_is_not_that_type(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "broken.png", blob("png", 400))
    tools.fail.add("ffprobe")
    assert ask_run.main(ask(*media_args([path]))) == 2
    assert "not a readable image" in refused(capsys)


def test_no_ffmpeg_is_refused_with_an_install_hint(monkeypatch, mhub, stage, tmp_path, capsys):
    monkeypatch.setattr(ask_run.shutil, "which", lambda name: None)
    path = put(tmp_path, "a.png", blob("png", 400))
    assert ask_run.main(ask(*media_args([path]))) == 2
    message = refused(capsys)
    assert code_of(message) == "ffmpeg_missing" and "apt-get install ffmpeg" in message and "brew install ffmpeg" in message
    assert mhub.requests == [] and list(stage.iterdir()) == []


def test_ffmpeg_missing_beats_every_other_file_problem(monkeypatch, mhub, stage, tmp_path, capsys):
    monkeypatch.setattr(ask_run.shutil, "which", lambda name: None)
    path = put(tmp_path, "page.jpg", b"<html></html>")
    assert ask_run.main(ask(*media_args([path]))) == 2
    assert code_of(refused(capsys)) == "ffmpeg_missing"


# ================================================================== upload, then create
def test_uploads_come_first_then_the_create_with_the_ids(mhub, tools, stage, tmp_path, capsys):
    pic = put(tmp_path, "cover_a.jpg", blob("jpeg", 300))
    big = put(tmp_path, "cover_b.png", blob("png", 400))
    vid = put(tmp_path, "teaser.mp4", blob("mp4", 500))
    tools.probe["cover_b.png"] = {"streams": [{"codec_type": "video", "width": 3000, "height": 2000}]}
    argv = ask(*media_args([pic, big, vid], ["warm", "", "teaser"], "one"))
    assert ask_run.main(argv) == 0
    out, err = capsys.readouterr()
    assert QID in out
    assert [(r["method"], r["path"]) for r in mhub.requests] == [("POST", MEDIA_PATH)] * 4 + [("POST", CREATE_PATH)]
    ups = uploads(mhub)
    assert [u["name"] for u in ups] == ["cover_a.jpg", "cover_b.png", "teaser.mp4", "teaser.mp4.poster.jpg"]
    assert all(u["ctype"] == "application/octet-stream" and u["auth"] == f"Bearer {mhub.token}" for u in ups)
    assert all(int(u["length"]) == len(u["data"]) for u in ups)
    # the bytes on the wire are the staged files, not the sources
    assert ups[0]["data"] == blob("jpeg", 300)                         # small: sent as it is
    assert ups[1]["data"] == blob("jpeg", 200)                         # the shrunk copy, not the PNG
    assert ask_run.sniff_media(ups[2]["data"]) == "mp4" and ask_run.sniff_media(ups[3]["data"]) == "jpeg"
    body = mhub.requests[-1]["body"]
    # every upload is filed under the card's own session (the live hub refuses one without it)
    assert body["requester"]["session"] and all(u["session"] == body["requester"]["session"] for u in ups)
    ids = list(mhub.uploads)
    assert body["media"] == [{"id": ids[0], "caption": "warm"}, {"id": ids[1]},
                             {"id": ids[2], "caption": "teaser", "poster_id": ids[3]}]
    assert body["pick"] == "one" and "options" not in body and body["free_text"] is True
    assert "media[1] cover_b.png: image" in err and "(3000x2000 shrunk to 2048 px)" in err
    assert list(stage.iterdir()) == []


def test_nothing_is_uploaded_when_a_later_file_is_bad(mhub, tools, stage, tmp_path, capsys):
    good = put(tmp_path, "good.png", blob("png", 300))
    bad = put(tmp_path, "bad.jpg", b"<html></html>")
    assert ask_run.main(ask(*media_args([good, bad], pick="one"))) == 2
    assert code_of(refused(capsys)) == "unsupported_media"
    assert mhub.requests == []


def test_a_thai_or_percent_file_name_travels_percent_encoded_and_a_plain_one_as_is(mhub, tools, stage, tmp_path, capsys):
    thai = put(tmp_path, "ปกตอน 3.png", blob("png", 300))
    plain = put(tmp_path, "cover b (final).png", blob("png", 300))
    pct = put(tmp_path, "100%.png", blob("png", 300))
    assert ask_run.main(ask(*media_args([thai, plain, pct], pick="many"))) == 0
    names = [u["name"] for u in uploads(mhub)]
    assert names == [quote("ปกตอน 3.png", safe=""), "cover b (final).png", "100%25.png"]


def test_the_name_sent_is_the_base_name_without_hidden_characters(mhub, tools, stage, tmp_path, capsys):
    sub = tmp_path / "deep" / "dir"
    sub.mkdir(parents=True)
    path = put(sub, "a‮b​c.png", blob("png", 300))
    assert ask_run.main(ask(*media_args([path]))) == 0
    assert uploads(mhub)[0]["name"] == "abc.png"


def test_upload_responses_must_agree_with_what_was_sent(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "a.png", blob("png", 300))
    mhub.on("POST", MEDIA_PATH, (201, {"media_id": "M-" + "a" * 24, "kind": "image", "bytes": 300,
                                       "sha256": "0" * 64}))
    assert ask_run.main(ask(*media_args([path]))) == 3
    assert "sha256" in capsys.readouterr().err
    assert CREATE_PATH not in mhub.paths()


@pytest.mark.parametrize("bad_id", ["../etc/passwd", "M-123", "M-" + "A" * 24, "", None, 7])
def test_a_media_id_that_is_not_the_contract_shape_is_not_used(mhub, tools, stage, tmp_path, capsys, bad_id):
    path = put(tmp_path, "a.png", blob("png", 300))
    mhub.on("POST", MEDIA_PATH, (201, {"media_id": bad_id, "bytes": 300}))
    assert ask_run.main(ask(*media_args([path]))) == 3
    assert "media id" in capsys.readouterr().err and CREATE_PATH not in mhub.paths()


@pytest.mark.parametrize("code, text", [
    ("store_full", "The media store is full (2 GB). Ask the CEO to answer open cards, then try again."),
    ("disk_low", "Less than 6 GB of disk is free on the hub; uploads are paused."),
])
def test_a_507_message_is_printed_as_the_hub_wrote_it(mhub, tools, stage, tmp_path, capsys, code, text):
    path = put(tmp_path, "a.png", blob("png", 300))
    mhub.on("POST", MEDIA_PATH, (507, {"error": code, "message": text}))
    assert ask_run.main(ask(*media_args([path]))) == 3
    err = capsys.readouterr().err
    assert "507" in err and code in err and text in err
    assert CREATE_PATH not in mhub.paths() and list(stage.iterdir()) == []


@pytest.mark.parametrize("status, code", [(415, "unsupported_media"), (413, "too_large"), (429, "rate_limited")])
def test_other_upload_refusals_carry_their_hint(mhub, tools, stage, tmp_path, capsys, status, code):
    path = put(tmp_path, "a.png", blob("png", 300))
    mhub.on("POST", MEDIA_PATH, (status, {"error": code}))
    assert ask_run.main(ask(*media_args([path]))) == 3
    err = capsys.readouterr().err
    assert code in err and ask_run._HINTS[code] in err


def test_a_create_refusal_after_the_uploads_is_reported_with_its_code(mhub, tools, stage, tmp_path, capsys):
    path = put(tmp_path, "a.png", blob("png", 300))
    mhub.on("POST", CREATE_PATH, (400, {"error": "invalid_media", "message": "media id is not yours"}))
    assert ask_run.main(ask(*media_args([path]))) == 3
    err = capsys.readouterr().err
    assert "invalid_media" in err and "media id is not yours" in err
    assert len(uploads(mhub)) == 1                                       # no retry loop


def test_dry_run_stages_and_checks_but_sends_nothing(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    def _no_network(*a, **k):
        raise AssertionError("--dry-run opened a connection")
    monkeypatch.setattr(ask_run._OPENER, "open", _no_network)
    paths = [put(tmp_path, "a.png", blob("png", 300)), put(tmp_path, "v.mp4", blob("mp4", 300))]
    assert ask_run.main(ask(*media_args(paths, pick="one"), "--dry-run")) == 0
    out, err = capsys.readouterr()
    body = json.loads(out)
    assert body["media"][1]["poster_id"] == ask_run.PENDING_MEDIA_ID and body["pick"] == "one"
    assert "nothing sent" in err and "would upload 2 item(s)" in err
    assert mhub.requests == [] and list(stage.iterdir()) == []


def test_dry_run_still_refuses_a_bad_file(mhub, tools, stage, tmp_path, capsys):
    bad = put(tmp_path, "bad.jpg", b"<html></html>")
    assert ask_run.main(ask(*media_args([bad]), "--dry-run")) == 2
    assert code_of(refused(capsys)) == "unsupported_media"


def test_the_upload_is_a_question_call_with_the_strict_address_check(monkeypatch, mhub, tools, stage, tmp_path, capsys):
    monkeypatch.setenv("RUN_INBOX_URL", "http://example.com")           # plain http to a non-loopback host
    path = put(tmp_path, "a.png", blob("png", 300))
    assert ask_run.main(ask(*media_args([path]))) in (2, 3)
    assert mhub.requests == []
    assert ask_run._is_question_path(MEDIA_PATH)


# ================================================================== MCP: the same code path
def _mcp(media, **extra):
    return {"question": "Which cover?", "options": None, "why": "Pick the cover for episode 3", "recommended": 0,
            "free_text": True, "expires_h": 24, "session": "cto-t", "role": "cto", "host": "contabo",
            "dry_run": True, "media": media, **extra}


def test_mcp_media_dry_run_body_equals_the_cli_body(mhub, tools, stage, tmp_path, capsys):
    paths = [put(tmp_path, "a.png", blob("png", 300)), put(tmp_path, "v.mp4", blob("mp4", 300))]
    assert ask_run.main(ask(*media_args(paths, ["one", "two"], "many"), "--dry-run")) == 0
    cli = json.loads(capsys.readouterr().out)
    out = ask_run.mcp_ask_ceo(_mcp([{"path": paths[0], "caption": "one"}, {"path": paths[1], "caption": "two"}],
                                   pick="many"))
    assert out["dry_run"] is True and out["payload"] == cli
    assert out["media"] and mhub.requests == []


def test_mcp_media_sends_through_the_same_upload_path(mhub, tools, stage, tmp_path):
    path = put(tmp_path, "a.png", blob("png", 300))
    out = ask_run.mcp_ask_ceo(_mcp([{"path": path}], dry_run=False))
    assert out["id"] == QID and out["media"]
    assert [r["path"] for r in mhub.requests] == [MEDIA_PATH, CREATE_PATH]


@pytest.mark.parametrize("media, extra, code", [
    ("nope", {}, "invalid_media"),
    ([{"caption": "x"}], {}, "invalid_media"),
    ([{"path": "a.png", "caption": 5}], {}, "invalid_media"),
    ([{"path": "a.png", "url": "http://x"}], {}, "invalid_media"),
    ([{"path": "a.png"}] * 2, {}, "pick_required"),
    ([{"path": "a.png"}], {"pick": "many"}, "invalid_pick"),
    ([{"path": "a.png"}] * 2, {"pick": "one", "options": ["a", "b"]}, "options_not_allowed"),
    ([{"path": "a.png"}], {"questions": [{"question": "q", "why": "w", "options": ["a", "b"]}]}, "media_not_in_groups"),
])
def test_mcp_media_refusals(mhub, tools, stage, tmp_path, media, extra, code):
    if isinstance(media, list):
        real = put(tmp_path, "a.png", blob("png", 300))
        media = [{**m, "path": real} if m.get("path") == "a.png" else m for m in media]
    with pytest.raises(ask_run.Refused) as exc:
        ask_run.mcp_ask_ceo(_mcp(media, **extra))
    assert code in str(exc.value)
    assert mhub.requests == []


def test_the_coo_ask_ceo_tool_takes_media_and_pick():
    tree = ast.parse((ROOT / "runners" / "coo_mcp_server.py").read_text(encoding="utf-8"))
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_ask_ceo"]
    assert len(fns) == 1
    names = [a.arg for a in fns[0].args.args]
    assert "media" in names and "pick" in names
    assert "media=media" in ast.get_source_segment((ROOT / "runners" / "coo_mcp_server.py").read_text(encoding="utf-8"), fns[0])


# ================================================================== wait: the picked: line
def _media_record(n_items: int, answer, **extra):
    media = [{"n": i, "label": chr(65 + i), "kind": "image", "mime": "image/png", "bytes": 10, "caption": ""}
             for i in range(n_items)]
    base = {"via": "operator_passkey_session", "answered_by": "CEO", "answered_at": "2026-10-27T05:00:00Z"}
    return _record("answered", options=[], media=media, pick="one" if n_items > 1 else None,
                   answer={**base, **answer}, finished_at="2026-10-27T05:00:00Z", **extra)


def _wait(mhub, capsys, rec, *flags):
    mhub.on("GET", QPATH, rec)
    rc = ask_run.main(["wait", QID, "--interval", "0.01", *flags])
    return rc, capsys.readouterr().out


HEADER = f"{QID}  answered  by CEO  at 2026-10-27T05:00:00Z"


def test_wait_prints_one_pick_with_its_name_and_the_note(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(3, {"picks": [1], "picked": ["B"], "picked_names": ["cover_b.png"],
                                                    "text": "warmer please"}))
    assert rc == 0
    assert out.splitlines() == [HEADER, "question: Ship the Console fix tonight or tomorrow morning?",
                                "picked: B (cover_b.png) · note: warmer please", f"sha256: {SHA}"]


def test_wait_prints_many_picks_without_a_note(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(4, {"picks": [0, 2], "picked": ["A", "C"],
                                                    "picked_names": ["a.jpg", "c.jpg"], "text": None}))
    assert rc == 0 and "picked: A (a.jpg), C (c.jpg)\n" in out and "note" not in out


def test_wait_prints_none_for_an_empty_many_and_for_a_redo(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(3, {"picks": [], "picked": [], "picked_names": [],
                                                    "text": "nothing fits"}))
    assert rc == 0 and "picked: none · note: nothing fits\n" in out
    rc, out = _wait(mhub, capsys, _media_record(3, {"redo": True, "picks": [], "picked": [], "text": "try warmer light"}))
    assert rc == 0 and "picked: none · note: try warmer light\n" in out
    rc, out = _wait(mhub, capsys, _media_record(3, {"picks": [], "text": None}))
    assert rc == 0 and "picked: none\n" in out


def test_wait_reads_redo_from_the_record_too(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(2, {"picks": [], "text": "again"}, redo=True))
    assert rc == 0 and "picked: none · note: again\n" in out


def test_wait_prints_a_one_item_card_answer_as_picked(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(1, {"choice": 0, "label": "ใช้ได้", "text": "เยี่ยม"}))
    assert rc == 0 and "picked: ใช้ได้ · note: เยี่ยม\n" in out and "answer: option" not in out
    rc, out = _wait(mhub, capsys, _media_record(1, {"choice": 1, "label": "แก้", "text": None}))
    assert rc == 0 and "picked: แก้\n" in out


def test_wait_falls_back_to_letters_when_the_hub_sends_no_names(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(3, {"picks": [2], "text": None}))
    assert rc == 0 and "picked: C\n" in out


def test_wait_strips_hidden_characters_from_names_and_notes(mhub, capsys):
    rc, out = _wait(mhub, capsys, _media_record(2, {"picks": [0], "picked": ["A"], "picked_names": ["a‮b.png"],
                                                    "text": "x​y"}))
    assert rc == 0 and "picked: A (ab.png) · note: xy\n" in out


def test_wait_json_keeps_picks_picked_names_and_redo(mhub, capsys):
    rec = _media_record(3, {"picks": [1], "picked": ["B"], "picked_names": ["b.png"], "redo": False, "text": None})
    rc, out = _wait(mhub, capsys, rec, "--json")
    assert rc == 0
    answer = json.loads(out)["answer"]
    assert (answer["picks"], answer["picked"], answer["picked_names"], answer["redo"]) == ([1], ["B"], ["b.png"], False)


@pytest.mark.parametrize("answer, why", [
    ({"picks": [5], "picked": ["F"]}, "outside the card"),
    ({"picks": [0, 0], "picked": ["A", "A"]}, "repeats an item"),
    ({"picks": [-1]}, "negative"),
    ({"picks": [True]}, "a bool is not an index"),
    ({"picks": "B"}, "not a list"),
    ({"picks": [1], "picked": ["A"]}, "letters disagree with picks"),
])
def test_wait_refuses_a_picks_list_that_does_not_fit_the_card(mhub, capsys, answer, why):
    mhub.on("GET", QPATH, _media_record(3, answer))
    assert ask_run.main(["wait", QID, "--interval", "0.01"]) == 3, why
    out, err = capsys.readouterr()
    assert "picked:" not in out and "not trusting it" in err and "answer.picks" in err


def test_a_plain_card_prints_exactly_as_before(mhub, capsys):
    mhub.on("GET", QPATH, _record("answered", answer={**ANSWER, "text": "go"}, finished_at="x"))
    assert ask_run.main(["wait", QID]) == 0
    out = capsys.readouterr().out
    assert 'answer: option 1 "Tonight"' in out and "note: go" in out and "picked:" not in out


# ================================================================== the files that must exist
def test_the_run_media_row_is_in_the_machine_contract_as_disposable():
    data = yaml.safe_load((ROOT / "config" / "machine-contract.yaml").read_text(encoding="utf-8"))
    rows = [r for r in data["entries"] if "run-media" in r["path"]]
    assert len(rows) == 1
    row = rows[0]
    assert row["machine"] == "contabo" and row["path"].startswith("<hq>/Assets/MoonieX/Console/run-media")
    assert row["class"] == "DISPOSABLE" and row["owner"] == "MoonieX-Console" and not row["discovered"]
    assert "7 d" in row["restore"] and "2 GB" in row["restore"]


def test_the_storage_policy_carries_the_2gb_cap_and_still_loads():
    from tools import storage_policy
    path = ROOT / "config" / "storage-policy.yaml"
    storage_policy.load(str(path))                                       # the validator still accepts the file
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))["run_media"]
    assert cfg["max_bytes"] == 2 * 1024 ** 3 and cfg["min_free_gb"] == 6
    assert cfg["close_ttl_days"] == 7 and cfg["pending_ttl_hours"] == 1


def test_the_docs_and_the_skill_describe_the_media_form():
    doc = (ROOT / "docs" / "design" / "run-inbox" / "QUESTIONS.md").read_text(encoding="utf-8")
    assert "## 11. Media" in doc and "picked: B (cover_b.png)" in doc and "operatorOnly" in doc
    skill = (ROOT / ".claude" / "skills" / "ALL_Protocol_RunInbox" / "SKILL.md").read_text(encoding="utf-8")
    assert "--media PATH" in skill and "--pick one|many" in skill


# ================================================================== the real tools, tiny files
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg and ffprobe are not installed")


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-threads", "2", *args],
                   check=True, timeout=120, stdin=subprocess.DEVNULL)


def _probe(data: bytes, tmp_path: Path) -> dict:
    path = tmp_path / "probe.bin"
    path.write_bytes(data)
    cp = subprocess.run(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format", "json",
                         "-show_streams", "-show_format", str(path)], capture_output=True, timeout=60, check=True)
    return json.loads(cp.stdout)


@needs_ffmpeg
def test_real_ffmpeg_end_to_end_on_tiny_files(mhub, stage, tmp_path, capsys):
    big = str(tmp_path / "big.png")
    vid = str(tmp_path / "clip.webm")
    snd = str(tmp_path / "voice.wav")
    _ff("-f", "lavfi", "-i", "color=c=orange:s=3000x2000", "-frames:v", "1", big)
    _ff("-f", "lavfi", "-i", "testsrc2=s=1280x1080:r=10:d=1", "-f", "lavfi", "-i", "sine=d=1",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
        "-f", "matroska", vid)                                          # Matroska is what a .webm starts with
    _ff("-f", "lavfi", "-i", "sine=d=1", snd)
    assert ask_run.main(ask(*media_args([big, vid, snd], ["pic", "vid", "snd"], "many"))) == 0
    capsys.readouterr()
    ups = uploads(mhub)
    assert [u["name"] for u in ups] == ["big.png", "clip.webm", "clip.webm.poster.jpg", "voice.wav"]
    pic = _probe(ups[0]["data"], tmp_path)["streams"][0]
    assert ask_run.sniff_media(ups[0]["data"]) == "jpeg" and max(pic["width"], pic["height"]) == 2048
    video = _probe(ups[1]["data"], tmp_path)
    kinds = {s["codec_type"]: s for s in video["streams"]}
    assert ask_run.sniff_media(ups[1]["data"]) == "mp4"
    assert kinds["video"]["codec_name"] == "h264" and kinds["video"]["height"] == 720
    assert kinds["audio"]["codec_name"] == "aac"
    assert ask_run.sniff_media(ups[2]["data"]) == "jpeg"
    assert ask_run.sniff_media(ups[3]["data"]) == "m4a"                    # an audio brand, so the hub files it as audio
    assert _probe(ups[3]["data"], tmp_path)["streams"][0]["codec_name"] == "aac"
    body = mhub.requests[-1]["body"]
    assert body["pick"] == "many" and body["media"][1]["poster_id"] and "poster_id" not in body["media"][0]
    assert list(stage.iterdir()) == []
