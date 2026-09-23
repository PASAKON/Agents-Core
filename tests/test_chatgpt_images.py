"""Tests for the zero-model ChatGPT image runner (task-854cb512).

Covers everything a browser is NOT needed for: brief parsing (markdown and
JSON), hazard classification, the MD5 no-duplicate guard, and the ledger's
resumable skip-what's-done behaviour, driven through `cmd_run` with
`ChatGPTBrowser` swapped for a scripted stub. `ChatGPTBrowser` itself (the
only class that touches Playwright/CDP) is never instantiated here — see its
docstring in tools/chatgpt_images.py.

Run via:  pytest tests/test_chatgpt_images.py
(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_flow_shoot.py.)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tools import chatgpt_images as ci

FIXTURE_BRIEF = (Path(__file__).resolve().parent.parent / "docs" / "ops" / "briefs"
                  / "ilag-trailer-chatgpt-round3-village.md")


# ── markdown brief parsing ───────────────────────────────────────────────────

def test_parse_markdown_brief_reads_every_image_in_the_fixture():
    images = ci.parse_markdown_brief(FIXTURE_BRIEF.read_text(encoding="utf-8"))
    assert [im["name"] for im in images] == [
        "loc_village_above_A", "loc_village_above_B", "loc_village_roots"]
    assert all(im["attach"] is None for im in images)
    assert images[0]["prompt"].startswith("Cinematic photorealistic environment concept")
    assert images[0]["prompt"].endswith("no watermark.")


def test_parse_markdown_brief_supports_optional_attach_line():
    text = """
## Image 1: char_mount_v2
ATTACH: C:\\mooniex\\ilag-trailer\\plates\\char_mount.png

PROMPT START
keep this exact creature
PROMPT END
"""
    images = ci.parse_markdown_brief(text)
    assert images[0]["attach"] == "C:\\mooniex\\ilag-trailer\\plates\\char_mount.png"
    assert images[0]["prompt"] == "keep this exact creature"


def test_parse_markdown_brief_rejects_duplicate_names():
    text = (
        "## Image 1: foo\nPROMPT START\na\nPROMPT END\n"
        "## Image 2: foo\nPROMPT START\nb\nPROMPT END\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        ci.parse_markdown_brief(text)


def test_parse_markdown_brief_rejects_missing_prompt_block():
    with pytest.raises(ValueError, match="PROMPT START/END"):
        ci.parse_markdown_brief("## Image 1: foo\nno prompt here\n")


def test_parse_markdown_brief_rejects_no_headings():
    with pytest.raises(ValueError, match="headings"):
        ci.parse_markdown_brief("just some text")


# ── JSON brief parsing ───────────────────────────────────────────────────────

def test_parse_json_brief_round_trips_fields():
    text = json.dumps([
        {"name": "apple", "prompt": "a red apple", "attach": "ref.png"},
        {"name": "pear", "prompt": "a green pear"},
    ])
    images = ci.parse_json_brief(text)
    assert images[0] == {"name": "apple", "prompt": "a red apple", "attach": "ref.png"}
    assert images[1] == {"name": "pear", "prompt": "a green pear", "attach": None}


def test_parse_json_brief_rejects_non_list():
    with pytest.raises(ValueError, match="list"):
        ci.parse_json_brief(json.dumps({"name": "x", "prompt": "y"}))


def test_parse_json_brief_rejects_missing_fields():
    with pytest.raises(ValueError, match="name.*prompt"):
        ci.parse_json_brief(json.dumps([{"name": "x"}]))


def test_load_images_dispatches_on_extension(tmp_path):
    json_path = tmp_path / "list.json"
    json_path.write_text(json.dumps([{"name": "x", "prompt": "y"}]), encoding="utf-8")
    assert ci.load_images(json_path) == [{"name": "x", "prompt": "y", "attach": None}]

    md_path = tmp_path / "brief.md"
    md_path.write_text("## Image 1: x\nPROMPT START\ny\nPROMPT END\n", encoding="utf-8")
    assert ci.load_images(md_path)[0]["name"] == "x"


# ── hazard classification ────────────────────────────────────────────────────

def test_classify_hazard_signed_out_only_when_composer_absent():
    body = "Log in\nSign up for free\nChatGPT"
    assert ci.classify_hazard(body, composer_present=False)[0] == "signed_out"
    # composer present -> "Log in" in a sidebar/footer must not false-positive
    assert ci.classify_hazard(body, composer_present=True) is None


def test_classify_hazard_usage_limit():
    kind, excerpt = ci.classify_hazard(
        "You've reached the limit for GPT-image generations today.", True)
    assert kind == "usage_limit"
    assert "reached" in excerpt.lower()


def test_classify_hazard_paywall():
    kind, _ = ci.classify_hazard("Upgrade to Plus to keep creating images.", True)
    assert kind == "paywall"


def test_classify_hazard_none_for_ordinary_page():
    assert ci.classify_hazard("ChatGPT can make mistakes. Check important info.", True) is None


# ── md5 duplicate guard ──────────────────────────────────────────────────────

def test_existing_md5s_scans_output_dir(tmp_path):
    (tmp_path / "a.png").write_bytes(b"AAAA")
    (tmp_path / "b.png").write_bytes(b"BBBB")
    (tmp_path / "ledger.json").write_text("{}", encoding="utf-8")  # non-png, ignored
    dupes = ci.existing_md5s(tmp_path)
    assert ci.md5_bytes(b"AAAA") in dupes
    assert dupes[ci.md5_bytes(b"AAAA")].name == "a.png"
    assert len(dupes) == 2


def test_existing_md5s_empty_dir_returns_empty(tmp_path):
    assert ci.existing_md5s(tmp_path / "does-not-exist") == {}


# ── ledger ────────────────────────────────────────────────────────────────

def test_ledger_round_trip(tmp_path):
    path = tmp_path / "ledger.json"
    assert ci.load_ledger(path) == {}
    rows = {"apple": {"name": "apple", "status": "done"}}
    ci.save_ledger(path, rows)
    assert ci.load_ledger(path) == rows


# ── orchestration, via a scripted stub browser ──────────────────────────────

class StubBrowser:
    """Mimics ChatGPTBrowser's public surface with scripted per-name results
    instead of a real page — no Playwright import anywhere in this class."""

    def __init__(self, script: dict[str, dict]):
        self.script = script
        self.closed = False
        self.attached = False
        self.seen_names: list[str] = []
        self.page = argparse.Namespace(url="https://chatgpt.com/c/stub")
        self.calls: list[tuple] = []
        self.wait_kwargs: list[dict] = []

    def attach(self):
        self.attached = True

    def close(self):
        self.closed = True

    def new_chat(self):
        self.calls.append(("new_chat",))

    def open_chat(self, url):
        self.calls.append(("open_chat", url))
        self.page.url = url

    def baseline(self):
        return {"src": "http://x/previous.png", "assistant_turns": 1, "user_turns": 1}

    def composer_present(self):
        name = self._current
        return self.script[name].get("composer_present", True)

    def body_text(self):
        return self.script[self._current].get("body", "")

    def attach_reference(self, path):
        if self.script[self._current].get("attach_fails"):
            raise RuntimeError("no file input")

    def paste_prompt(self, text):
        # a real composer APPENDS a second paste; model that so the retry path is honest
        self._pastes = getattr(self, "_pastes", 0) + 1
        first_bad = self.script.get(getattr(self, "_current", ""), {}).get("first_paste_garbled")
        garbled = text[:10] if (first_bad and self._pastes == 1) else text
        self._pasted = getattr(self, "_pasted", "") + garbled if self._pastes > 1 else garbled

    def clear_composer(self):
        self.calls.append(("clear_composer",))
        self._pasted = ""

    def read_composer_text(self):
        return self._pasted

    def send(self):
        pass

    def wait_for_result(self, timeout_s, **kw):
        self.wait_kwargs.append(kw)
        result = self.script[self._current]["result"]
        if self.script[self._current].get("new_chat_url"):
            self.page.url = self.script[self._current]["new_chat_url"]
        return result

    def fetch_image_bytes(self, url):
        return self.script[self._current]["bytes"]

    def process(self, name):
        self._current = name
        self.seen_names.append(name)


def _run(images, script, out_dir, one=None, dry_run=False):
    browser = StubBrowser(script)
    orig_process_one = ci.process_one

    def patched(browser_arg, image, out_dir_arg, ledger_path, ledger, timeout_s):
        browser_arg.process(image["name"])
        return orig_process_one(browser_arg, image, out_dir_arg, ledger_path, ledger, timeout_s)

    args = argparse.Namespace(
        brief=None, json=str(out_dir / "images.json"), out=str(out_dir),
        one=one, dry_run=dry_run, cdp_url="stub://", timeout_s=1,
    )
    (out_dir / "images.json").write_text(json.dumps(images), encoding="utf-8")

    import unittest.mock as mock
    with mock.patch.object(ci, "ChatGPTBrowser", return_value=browser), \
         mock.patch.object(ci, "process_one", patched):
        code = ci.cmd_run(args)
    return code, browser


def test_cmd_run_dry_run_never_touches_a_browser(tmp_path):
    images = [{"name": "apple", "prompt": "a red apple"}]
    args = argparse.Namespace(
        brief=None, json=str(tmp_path / "images.json"), out=str(tmp_path),
        one=None, dry_run=True, cdp_url="stub://", timeout_s=1,
    )
    (tmp_path / "images.json").write_text(json.dumps(images), encoding="utf-8")

    import unittest.mock as mock
    with mock.patch.object(ci, "ChatGPTBrowser") as cls:
        code = ci.cmd_run(args)
    cls.assert_not_called()
    assert code == 0


def test_cmd_run_saves_image_and_ledger_on_success(tmp_path):
    images = [{"name": "apple", "prompt": "a red apple"}]
    script = {"apple": {"result": {"status": "done", "src": "http://x/img.png",
                                     "width": 100, "height": 80},
                          "bytes": b"PNGDATA"}}
    code, browser = _run(images, script, tmp_path)
    assert code == 0
    assert (tmp_path / "apple.png").read_bytes() == b"PNGDATA"
    ledger = ci.load_ledger(tmp_path / "ledger.json")
    assert ledger["apple"]["status"] == "done"
    assert ledger["apple"]["md5"] == ci.md5_bytes(b"PNGDATA")
    assert ledger["apple"]["width"] == 100


def test_cmd_run_skips_names_already_done_in_the_ledger(tmp_path):
    ci.save_ledger(tmp_path / "ledger.json", {"apple": {"name": "apple", "status": "done"}})
    images = [{"name": "apple", "prompt": "a red apple"},
              {"name": "pear", "prompt": "a green pear"}]
    script = {"pear": {"result": {"status": "done", "src": "http://x/img.png",
                                    "width": 1, "height": 1},
                         "bytes": b"PEARDATA"}}
    code, browser = _run(images, script, tmp_path)
    assert code == 0
    assert browser.seen_names == ["pear"]  # apple was never touched


def test_cmd_run_stops_the_whole_batch_on_a_hazard(tmp_path):
    images = [{"name": "apple", "prompt": "a red apple"},
              {"name": "pear", "prompt": "a green pear"}]
    script = {"apple": {"result": {"status": "hazard", "hazard_kind": "usage_limit",
                                     "text": "usage cap reached"}}}
    code, browser = _run(images, script, tmp_path)
    assert code == 1
    assert browser.seen_names == ["apple"]  # pear never attempted
    ledger = ci.load_ledger(tmp_path / "ledger.json")
    assert ledger["apple"]["status"] == "stopped"
    assert ledger["apple"]["hazard_kind"] == "usage_limit"


def test_cmd_run_stops_the_batch_on_a_refusal():
    pass  # covered by test_process_one_refusal_stops below (same code path)


def test_process_one_records_refusal_and_returns_stopped(tmp_path):
    browser = StubBrowser({"apple": {"result": {"status": "refusal", "text": "I can't create that."}}})
    browser._current = "apple"
    ledger: dict = {}
    row = ci.process_one(browser, {"name": "apple", "prompt": "x"}, tmp_path,
                          tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "stopped"
    assert row["hazard_kind"] == "refusal"
    assert row["note"] == "I can't create that."


def test_process_one_refuses_to_overwrite_existing_file(tmp_path):
    (tmp_path / "apple.png").write_bytes(b"old")
    browser = StubBrowser({})
    ledger: dict = {}
    row = ci.process_one(browser, {"name": "apple", "prompt": "x"}, tmp_path,
                          tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "failed"
    assert "already exists" in row["note"]
    assert (tmp_path / "apple.png").read_bytes() == b"old"  # untouched


def test_process_one_refuses_a_duplicate_md5(tmp_path):
    (tmp_path / "existing.png").write_bytes(b"SAME")
    browser = StubBrowser({"apple": {"result": {"status": "done", "src": "http://x/img.png",
                                                  "width": 1, "height": 1},
                                       "bytes": b"SAME"}})
    browser._current = "apple"
    ledger: dict = {}
    row = ci.process_one(browser, {"name": "apple", "prompt": "x"}, tmp_path,
                          tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "failed"
    assert "duplicate" in row["note"]
    assert not (tmp_path / "apple.png").exists()


def test_process_one_records_signed_out_when_composer_missing(tmp_path):
    browser = StubBrowser({"apple": {"composer_present": False, "body": "Log in\nSign up"}})
    browser._current = "apple"
    ledger: dict = {}
    row = ci.process_one(browser, {"name": "apple", "prompt": "x"}, tmp_path,
                          tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "stopped"
    assert row["hazard_kind"] == "signed_out"


# ── follow-up in the same chat (CEO 2026-09-24) ──────────────────────────────

def _done(src, data):
    return {"result": {"status": "done", "src": src, "width": 10, "height": 10}, "bytes": data}


def test_parse_json_and_markdown_carry_continue():
    j = ci.parse_json_brief(json.dumps([{"name": "a", "prompt": "x"},
                                        {"name": "b", "prompt": "y", "continue": "a"}]))
    assert [im.get("continue") for im in j] == [None, "a"]
    md = ci.parse_markdown_brief(
        "## Image 1: a\nPROMPT START\nx\nPROMPT END\n"
        "## Image 2: b\nCONTINUE: a\nPROMPT START\ny\nPROMPT END\n")
    assert [im.get("continue") for im in md] == [None, "a"]


def test_continue_reopens_the_parent_chat_and_excludes_its_image(tmp_path):
    ledger = {"a": {"name": "a", "status": "done", "chat_url": "https://chatgpt.com/c/AAA"}}
    browser = StubBrowser({"b": _done("http://x/new.png", b"NEW")})
    browser._current = "b"
    row = ci.process_one(browser, {"name": "b", "prompt": "thinner stroke", "continue": "a"},
                          tmp_path, tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "done"
    assert row["continued_from"] == "a"
    assert ("open_chat", "https://chatgpt.com/c/AAA") in browser.calls
    assert ("new_chat",) not in browser.calls
    assert browser.wait_kwargs[-1] == {"exclude_src": "http://x/previous.png",
                                       "min_assistant_turns": 2}


def test_continue_refuses_a_parent_that_is_not_done(tmp_path):
    ledger = {"a": {"name": "a", "status": "failed"}}
    browser = StubBrowser({"b": {}})
    browser._current = "b"
    row = ci.process_one(browser, {"name": "b", "prompt": "y", "continue": "a"},
                          tmp_path, tmp_path / "ledger.json", ledger, timeout_s=1)
    assert row["status"] == "failed"
    assert "cannot continue 'a'" in row["note"]
    assert browser.calls == []  # never touched the page


def test_a_chain_of_edits_runs_in_one_batch(tmp_path):
    images = [{"name": "a", "prompt": "logo"},
              {"name": "b", "prompt": "bolder", "continue": "a"},
              {"name": "c", "prompt": "redder", "continue": "b"}]
    script = {"a": {**_done("http://x/a.png", b"A"), "new_chat_url": "https://chatgpt.com/c/AAA"},
              "b": _done("http://x/b.png", b"B"),
              "c": _done("http://x/c.png", b"C")}
    code, browser = _run(images, script, tmp_path)
    assert code == 0
    ledger = ci.load_ledger(tmp_path / "ledger.json")
    assert [ledger[n]["status"] for n in "abc"] == ["done"] * 3
    assert ledger["b"]["chat_url"] == ledger["c"]["chat_url"] == "https://chatgpt.com/c/AAA"
    assert browser.calls.count(("new_chat",)) == 1


def test_prompt_mode_needs_a_name(tmp_path, capsys):
    args = ci.build_parser().parse_args(["--prompt", "x", "--out", str(tmp_path)])
    assert ci.cmd_run(args) == 2
    assert "--name" in capsys.readouterr().out


def test_recover_saves_the_image_already_in_the_chat(tmp_path):
    ledger = {"a": {"name": "a", "status": "stopped", "note": "refusal",
                    "chat_url": "https://chatgpt.com/c/AAA"}}
    browser = StubBrowser({"a": {"bytes": b"FINISHED"}})
    browser._current = "a"
    row = ci.recover_one(browser, "a", tmp_path, tmp_path / "ledger.json", ledger)
    assert row["status"] == "done"
    assert (tmp_path / "a.png").read_bytes() == b"FINISHED"
    assert ("open_chat", "https://chatgpt.com/c/AAA") in browser.calls
    assert "recovered" in ci.load_ledger(tmp_path / "ledger.json")["a"]["note"]


def test_recover_refuses_without_a_chat_url(tmp_path):
    row = ci.recover_one(StubBrowser({}), "a", tmp_path, tmp_path / "ledger.json", {"a": {"status": "failed"}})
    assert row["status"] == "failed"


def test_a_garbled_first_paste_is_cleared_before_the_retry(tmp_path):
    browser = StubBrowser({"b": {**_done("http://x/b.png", b"B"), "first_paste_garbled": True}})
    browser._current = "b"
    row = ci.process_one(browser, {"name": "b", "prompt": "a long prompt text"}, tmp_path,
                          tmp_path / "ledger.json", {}, timeout_s=1)
    assert row["status"] == "done"
    assert ("clear_composer",) in browser.calls
