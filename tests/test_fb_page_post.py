"""Tests for the FB Page general-post/Story composer poster (task-e4482d34).

Covers everything that needs no browser: the Page registry (config/fb_pages.yaml
format, key -> {profile_id, name}), the identity-switch pre/post-click
validators (validate_pre_switch/validate_post_switch — CEO/CTO addendum
cb63de3a, 2026-09-29; the live click itself is never run here, only these
pure decision functions), the comment-identity gate, comment orchestration via
a fake browser stub (post_comments_with_switch), and CLI argument parsing.
FBPageBrowser (the only class with real Playwright/CDP calls) is never
instantiated here, same convention as tests/test_fb_reel_post.py.

Run via:  pytest tests/test_fb_page_post.py
"""
from __future__ import annotations

import pytest

from tools import fb_page_post as fpp
from tools import fb_reel_post as frp


# -- reuse via import, not copy ----------------------------------------------

def test_fb_page_browser_subclasses_fb_reel_browser():
    assert issubclass(fpp.FBPageBrowser, frp.FBReelBrowser)


def test_does_not_redefine_shared_helpers_from_fb_reel_post():
    # These live only on frp — fb_page_post must call frp.<name>, never
    # define its own copy at module level.
    for name in (
        "do_first_comment", "parse_comment_identity", "is_duplicate_comment",
        "captions_match", "outcome_to_exit_code", "body_contains_text",
    ):
        assert name not in vars(fpp), f"{name} must be reused via frp.{name}, not redefined in fb_page_post"


# -- Page registry (CEO/CTO addendum 2026-09-29) -----------------------------

def test_parse_page_registry_basic():
    text = (
        "pages:\n"
        "  ilag:\n"
        '    profile_id: "61594116376333"\n'
        '    name: "ละครสั้นคุณธรรม by ILAG Studio"\n'
    )
    assert fpp.parse_page_registry(text) == {
        "ilag": {"profile_id": "61594116376333", "name": "ละครสั้นคุณธรรม by ILAG Studio"},
    }


def test_parse_page_registry_empty_text():
    assert fpp.parse_page_registry("") == {}


def test_parse_page_registry_no_pages_key():
    assert fpp.parse_page_registry("other: 1\n") == {}


def test_load_page_registry_reads_file(tmp_path):
    registry_path = tmp_path / "fb_pages.yaml"
    registry_path.write_text(
        'pages:\n  ilag:\n    profile_id: "61594116376333"\n    name: "N"\n',
        encoding="utf-8",
    )
    assert fpp.load_page_registry(str(registry_path)) == {
        "ilag": {"profile_id": "61594116376333", "name": "N"},
    }


def test_resolve_page_known_key():
    registry = {"ilag": {"profile_id": "1", "name": "N"}}
    assert fpp.resolve_page(registry, "ilag") == {"profile_id": "1", "name": "N"}


def test_resolve_page_unknown_key_raises_with_known_keys_listed():
    registry = {"ilag": {"profile_id": "1", "name": "N"}}
    with pytest.raises(ValueError, match="ilag"):
        fpp.resolve_page(registry, "doesnotexist")


# -- identity-switch validators (pure; the live click is never run here) ----

PROFILE_ID = "61594116376333"
PAGE_NAME = "ละครสั้นคุณธรรม by ILAG Studio"


def test_validate_pre_switch_all_checks_pass():
    result = fpp.validate_pre_switch(
        url=f"https://www.facebook.com/{PROFILE_ID}",
        first_h2_text=PAGE_NAME,
        switch_button_count=1,
        banner_text=f"สลับไปใช้เพจ {PAGE_NAME} เพื่อเริ่มจัดการ",
        profile_id=PROFILE_ID,
        expected_name=PAGE_NAME,
    )
    assert result == {"ok": True, "reason": "all pre-switch checks passed"}


def test_validate_pre_switch_fails_when_url_missing_profile_id():
    result = fpp.validate_pre_switch(
        url="https://www.facebook.com/some-other-page",
        first_h2_text=PAGE_NAME, switch_button_count=1,
        banner_text=f"สลับไปใช้เพจ {PAGE_NAME} เพื่อเริ่มจัดการ",
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False
    assert "URL" in result["reason"]


def test_validate_pre_switch_fails_on_generic_h1_heading_not_page_name():
    # h1 is the generic "จัดการเพจ" heading, not the Page name — a caller
    # that reads h1 instead of h2 must fail here, not silently pass.
    result = fpp.validate_pre_switch(
        url=f"https://www.facebook.com/{PROFILE_ID}",
        first_h2_text="จัดการเพจ", switch_button_count=1,
        banner_text=f"สลับไปใช้เพจ {PAGE_NAME} เพื่อเริ่มจัดการ",
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False
    assert "h2" in result["reason"]


def test_validate_pre_switch_fails_when_switch_button_count_not_one():
    for count in (0, 2):
        result = fpp.validate_pre_switch(
            url=f"https://www.facebook.com/{PROFILE_ID}",
            first_h2_text=PAGE_NAME, switch_button_count=count,
            banner_text=f"สลับไปใช้เพจ {PAGE_NAME} เพื่อเริ่มจัดการ",
            profile_id=PROFILE_ID, expected_name=PAGE_NAME,
        )
        assert result["ok"] is False, count
        assert "สลับเลย" in result["reason"], count


def test_validate_pre_switch_fails_on_wrong_banner_text():
    result = fpp.validate_pre_switch(
        url=f"https://www.facebook.com/{PROFILE_ID}",
        first_h2_text=PAGE_NAME, switch_button_count=1,
        banner_text="สลับไปใช้เพจ ชื่ออื่น เพื่อเริ่มจัดการ",
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False
    assert "banner" in result["reason"]


def test_validate_post_switch_all_checks_pass():
    result = fpp.validate_post_switch(
        cookie_i_user=PROFILE_ID,
        comment_identity=PAGE_NAME,
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result == {"ok": True, "reason": "all post-switch checks passed"}


def test_validate_post_switch_fails_on_wrong_cookie():
    result = fpp.validate_post_switch(
        cookie_i_user="someone-elses-id",
        comment_identity=PAGE_NAME,
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False
    assert "cookie" in result["reason"]


def test_validate_post_switch_fails_on_missing_cookie():
    result = fpp.validate_post_switch(
        cookie_i_user=None,
        comment_identity=PAGE_NAME,
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False


def test_validate_post_switch_fails_on_wrong_comment_identity():
    result = fpp.validate_post_switch(
        cookie_i_user=PROFILE_ID,
        comment_identity="Dorsine Gobb",
        profile_id=PROFILE_ID, expected_name=PAGE_NAME,
    )
    assert result["ok"] is False
    assert "aria-label" in result["reason"]


# -- comment identity decision (unit-tested with fixtures; never live) ------

def test_comment_identity_decision_already_correct():
    d = fpp.comment_identity_decision(PAGE_NAME, PAGE_NAME, switch_to_page=False)
    assert d["action"] == "post"


def test_comment_identity_decision_wrong_without_switch_flag_refuses():
    d = fpp.comment_identity_decision("Dorsine Gobb", PAGE_NAME, switch_to_page=False)
    assert d["action"] == "refuse"
    assert "--switch-to-page" in d["reason"]


def test_comment_identity_decision_wrong_with_switch_flag():
    d = fpp.comment_identity_decision("Dorsine Gobb", PAGE_NAME, switch_to_page=True)
    assert d["action"] == "switch_then_recheck"


# -- comment orchestration (fake browser stub; do_first_comment/ ------------
# -- post_followup_comment monkeypatched — mirrors _FakeBrowser in ---------
# -- test_fb_reel_post.py's resolve_permalink tests) -------------------------

class _FakeBrowser:
    """Stands in for FBPageBrowser: only the methods post_comments_with_switch
    calls. identities is popped once per find_comment_box() call — first
    call before any switch, a second call after a switch re-navigates."""

    def __init__(self, identities, switch_result=None, cookie_i_user=None, login_wall=False):
        self.identities = list(identities)
        self.switch_result = switch_result
        self.cookie_i_user = cookie_i_user
        self.login_wall = login_wall
        self.opened_permalinks: list[str] = []
        self.switch_calls: list[tuple[str, str]] = []

    def open_permalink(self, permalink):
        self.opened_permalinks.append(permalink)

    def check_login_wall(self):
        return self.login_wall

    def expand_see_more(self):
        pass

    def find_comment_box(self):
        return (object(), self.identities.pop(0))

    def switch_to_page_identity(self, profile_id, expected_page_name):
        self.switch_calls.append((profile_id, expected_page_name))
        return self.switch_result

    def _read_cookie(self, name):
        return self.cookie_i_user


def _fake_comment_ok(pinned=False):
    return {"ok": True, "pinned": pinned, "skipped_duplicate": False, "reason": "posted"}


def test_post_comments_with_switch_identity_already_correct(monkeypatch):
    fb = _FakeBrowser(identities=[PAGE_NAME])
    monkeypatch.setattr(frp, "do_first_comment", lambda fb_, permalink, text, name: _fake_comment_ok(pinned=True))
    monkeypatch.setattr(fpp, "post_followup_comment", lambda fb_, permalink, text, name: _fake_comment_ok())

    result = fpp.post_comments_with_switch(fb, "https://x", ["c1", "c2"], PAGE_NAME, switch_to_page=False)

    assert result["ok"] is True
    assert len(result["results"]) == 2
    assert fb.switch_calls == []


def test_post_comments_with_switch_wrong_identity_no_switch_flag_refuses(monkeypatch):
    fb = _FakeBrowser(identities=["Dorsine Gobb"])
    result = fpp.post_comments_with_switch(fb, "https://x", ["c1"], PAGE_NAME, switch_to_page=False)
    assert result["ok"] is False
    assert result["results"] == []
    assert fb.switch_calls == []


def test_post_comments_with_switch_requested_but_no_profile_id_refuses():
    fb = _FakeBrowser(identities=["Dorsine Gobb"])
    result = fpp.post_comments_with_switch(fb, "https://x", ["c1"], PAGE_NAME, switch_to_page=True, profile_id=None)
    assert result["ok"] is False
    assert "profile_id" in result["reason"]
    assert fb.switch_calls == []


def test_post_comments_with_switch_pre_switch_check_failure_refuses():
    fb = _FakeBrowser(
        identities=["Dorsine Gobb"],
        switch_result={"ok": False, "reason": "pre-switch check failed: URL does not contain profile_id"},
    )
    result = fpp.post_comments_with_switch(fb, "https://x", ["c1"], PAGE_NAME, switch_to_page=True, profile_id=PROFILE_ID)
    assert result["ok"] is False
    assert "switch refused" in result["reason"]
    assert result["results"] == []
    assert fb.switch_calls == [(PROFILE_ID, PAGE_NAME)]


def test_post_comments_with_switch_post_switch_check_failure_refuses():
    # switch click "succeeds" but the re-check after re-navigating to the
    # permalink still shows the wrong identity — validate_post_switch must
    # catch this and nothing gets typed.
    fb = _FakeBrowser(
        identities=["Dorsine Gobb", "Still Wrong"],
        switch_result={"ok": True, "reason": "clicked"},
        cookie_i_user=PROFILE_ID,
    )
    result = fpp.post_comments_with_switch(fb, "https://x", ["c1"], PAGE_NAME, switch_to_page=True, profile_id=PROFILE_ID)
    assert result["ok"] is False
    assert "post-switch check failed" in result["reason"]
    assert result["results"] == []


def test_post_comments_with_switch_succeeds_after_switch(monkeypatch):
    fb = _FakeBrowser(
        identities=["Dorsine Gobb", PAGE_NAME],
        switch_result={"ok": True, "reason": "clicked"},
        cookie_i_user=PROFILE_ID,
    )
    monkeypatch.setattr(frp, "do_first_comment", lambda fb_, permalink, text, name: _fake_comment_ok(pinned=True))
    monkeypatch.setattr(fpp, "post_followup_comment", lambda fb_, permalink, text, name: _fake_comment_ok())

    result = fpp.post_comments_with_switch(fb, "https://x", ["c1", "c2"], PAGE_NAME, switch_to_page=True, profile_id=PROFILE_ID)

    assert result["ok"] is True
    assert len(result["results"]) == 2
    # opened once before the switch, once again after re-navigating back
    assert fb.opened_permalinks == ["https://x", "https://x"]


def test_post_comments_with_switch_login_wall_refuses():
    fb = _FakeBrowser(identities=[PAGE_NAME], login_wall=True)
    result = fpp.post_comments_with_switch(fb, "https://x", ["c1"], PAGE_NAME, switch_to_page=False)
    assert result == {"ok": False, "reason": "login wall", "results": []}


def test_post_comments_with_switch_first_comment_fails_aborts_before_second(monkeypatch):
    fb = _FakeBrowser(identities=[PAGE_NAME])
    monkeypatch.setattr(frp, "do_first_comment", lambda fb_, permalink, text, name: {
        "ok": False, "skipped_duplicate": False, "reason": "submit failed",
    })

    def boom(*a, **k):
        raise AssertionError("post_followup_comment must not run after comment 1 fails")

    monkeypatch.setattr(fpp, "post_followup_comment", boom)

    result = fpp.post_comments_with_switch(fb, "https://x", ["c1", "c2"], PAGE_NAME, switch_to_page=False)
    assert result["ok"] is False
    assert len(result["results"]) == 1


# -- CLI argument parsing -----------------------------------------------------

def test_build_parser_photo_minimal_args():
    ap = fpp.build_parser()
    args = ap.parse_args(["photo", "--image", "i.png", "--caption-file", "c.txt"])
    assert args.mode == "photo"
    assert args.image == "i.png"
    assert args.caption_file == "c.txt"
    assert args.page == fpp.DEFAULT_PAGE_KEY
    assert args.page_registry == fpp.DEFAULT_PAGE_REGISTRY_PATH
    assert args.switch_to_page is False
    assert args.dry_run is False
    assert args.cdp == "http://127.0.0.1:9230"


def test_build_parser_photo_missing_caption_file_exits():
    ap = fpp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["photo", "--image", "i.png"])


def test_build_parser_story_minimal_args():
    ap = fpp.build_parser()
    args = ap.parse_args(["story", "--video", "v.mp4"])
    assert args.mode == "story"
    assert args.video == "v.mp4"
    assert args.page == fpp.DEFAULT_PAGE_KEY


def test_build_parser_story_missing_video_exits():
    ap = fpp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["story"])


def test_build_parser_comments_minimal_args():
    ap = fpp.build_parser()
    args = ap.parse_args(["comments", "--permalink", "https://x", "--comment-file", "c1.txt"])
    assert args.mode == "comments"
    assert args.permalink == "https://x"
    assert args.comment_file == ["c1.txt"]


def test_build_parser_comments_missing_comment_file_exits():
    ap = fpp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["comments", "--permalink", "https://x"])


def test_build_parser_missing_mode_exits():
    ap = fpp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args([])


def test_build_parser_custom_page_and_registry():
    ap = fpp.build_parser()
    args = ap.parse_args([
        "photo", "--image", "i.png", "--caption-file", "c.txt",
        "--page", "other", "--page-registry", "/tmp/x.yaml",
    ])
    assert args.page == "other"
    assert args.page_registry == "/tmp/x.yaml"


def test_build_parser_switch_to_page_flag():
    ap = fpp.build_parser()
    args = ap.parse_args([
        "comments", "--permalink", "https://x", "--comment-file", "c1.txt", "--switch-to-page",
    ])
    assert args.switch_to_page is True


# -- early-exit guards (unknown --page key must never touch the browser) ----

def test_resolve_page_missing_registry_file_returns_none(capsys):
    ap = fpp.build_parser()
    args = ap.parse_args([
        "photo", "--image", "i.png", "--caption-file", "c.txt",
        "--page-registry", "/no/such/fb_pages.yaml",
    ])
    assert fpp._resolve_page(args) is None
    assert "REFUSED" in capsys.readouterr().err


def test_resolve_page_unknown_key_returns_none(tmp_path, capsys):
    registry_path = tmp_path / "fb_pages.yaml"
    registry_path.write_text('pages:\n  ilag:\n    profile_id: "1"\n    name: "N"\n', encoding="utf-8")
    ap = fpp.build_parser()
    args = ap.parse_args([
        "photo", "--image", "i.png", "--caption-file", "c.txt",
        "--page", "doesnotexist", "--page-registry", str(registry_path),
    ])
    assert fpp._resolve_page(args) is None
    assert "doesnotexist" in capsys.readouterr().err


def test_run_photo_unknown_page_key_exits_2_without_touching_browser(monkeypatch, tmp_path):
    registry_path = tmp_path / "fb_pages.yaml"
    registry_path.write_text('pages:\n  ilag:\n    profile_id: "1"\n    name: "N"\n', encoding="utf-8")

    def boom(*a, **k):
        raise AssertionError("FBPageBrowser must not be constructed when --page resolution fails")

    monkeypatch.setattr(fpp, "FBPageBrowser", boom)
    ap = fpp.build_parser()
    args = ap.parse_args([
        "photo", "--image", "/nonexistent.png", "--caption-file", "/nonexistent.txt",
        "--page", "doesnotexist", "--page-registry", str(registry_path),
    ])
    assert fpp.run_photo(args) == 2


def test_run_story_unknown_page_key_exits_2_without_touching_browser(monkeypatch, tmp_path):
    registry_path = tmp_path / "fb_pages.yaml"
    registry_path.write_text('pages:\n  ilag:\n    profile_id: "1"\n    name: "N"\n', encoding="utf-8")

    def boom(*a, **k):
        raise AssertionError("FBPageBrowser must not be constructed when --page resolution fails")

    monkeypatch.setattr(fpp, "FBPageBrowser", boom)
    ap = fpp.build_parser()
    args = ap.parse_args([
        "story", "--video", "/nonexistent.mp4",
        "--page", "doesnotexist", "--page-registry", str(registry_path),
    ])
    assert fpp.run_story(args) == 2


def test_run_comments_unknown_page_key_exits_2_without_touching_browser(monkeypatch, tmp_path):
    registry_path = tmp_path / "fb_pages.yaml"
    registry_path.write_text('pages:\n  ilag:\n    profile_id: "1"\n    name: "N"\n', encoding="utf-8")

    def boom(*a, **k):
        raise AssertionError("FBPageBrowser must not be constructed when --page resolution fails")

    monkeypatch.setattr(fpp, "FBPageBrowser", boom)
    ap = fpp.build_parser()
    args = ap.parse_args([
        "comments", "--permalink", "https://x", "--comment-file", "c1.txt",
        "--page", "doesnotexist", "--page-registry", str(registry_path),
    ])
    assert fpp.run_comments(args) == 2


# -- run() dispatch ------------------------------------------------------------

def test_run_dispatches_by_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(fpp, "run_photo", lambda args: calls.append("photo") or 0)
    monkeypatch.setattr(fpp, "run_story", lambda args: calls.append("story") or 0)
    monkeypatch.setattr(fpp, "run_comments", lambda args: calls.append("comments") or 0)

    for mode in ("photo", "story", "comments"):
        fpp.run(type("Args", (), {"mode": mode})())
    assert calls == ["photo", "story", "comments"]
