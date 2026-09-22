#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The zero-model Flow shot runner — docs/ops/flow-operator-design.md, built.

Drives the logged-in automation Chrome (port 9223, dedicated profile — see
scripts/flow/launch-chrome-debug.sh) over CDP to shoot a «บัญชี» act's shots
in Google Flow: attach chips, paste the prompt, submit, download, verify.
STANDALONE — no Claude in the loop, zero token cost at runtime, same pattern
as scripts/higgsfield/gen_loop.py. The ledger (tools/flow_ledger.py) is the
runner's memory, not a context window: a crash restarts from the first
non-verified row, and a verified row is never re-fired.

    python3 tools/flow_shoot.py run    --sheet docs/scripts/banchi-ACT2.md \
        --ledger state/banchi/ACT2.tsv --dest ~/Desktop/banchi-ACT2 \
        --credit-cap 300 [--only 37-46] [--dry-run] \
        [--resolution {720p,360p}] [--force-duration N]
    python3 tools/flow_shoot.py pull   --sheet docs/scripts/banchi-ACT2.md \
        --ledger state/banchi/ACT2.tsv --dest ~/Desktop/banchi-ACT2 [--only 53-58]
    python3 tools/flow_shoot.py status --ledger state/banchi/ACT2.tsv

All Playwright/CDP calls live behind FlowBrowser below, so every decision the
runner makes (credit cap, refusal handling, zip vs. bare mp4, duration
tolerance, sheet parsing) is unit-testable without a browser — see
tests/test_flow_shoot.py. FlowBrowser itself is unverified against the live
DOM: it was written from docs/scripts/BANCHI-SHOOT-BRIEF.md and the
google-flow-ops skill, and the first live check is a human-run --dry-run
after the CEO logs into the automation Chrome (a worker cannot).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import clip_review, flow_ledger  # noqa: E402

CDP = "http://127.0.0.1:9223"
LOG_PATH = Path("state/banchi/flow_shoot.log")
DOWNLOAD_GAP_S = 8  # brief's rule: never fire two downloads closer than this
POLL_S = 8
COMPLETION_TIMEOUT_S = 8 * 60
UPSCALE_TIMEOUT_S = 3 * 60
DURATION_TOLERANCE_S = 0.6
MIN_AUDIO_DB = -60.0

# The mute-before-anything-plays snippet, verbatim from the brief. A worker
# (and this runner) has no ears; a clip playing is pure cost, zero information.
MUTE_JS = """
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.body, {childList: true, subtree: true});
""".strip()

# "ล้มเหลว / ... อาจละเมิดนโยบาย ..." — task spec's exact detection rule.
_DIALOGUE_RE = re.compile(r'says:\s*"([^"]+)"')
_CREDIT_RE = re.compile(r"(\d+)\s*เครดิต")

# CORRECTED 2026-09-19 (task-04851451, live check against the automation
# Chrome, read-only, on the project's 11 already-charged clips):
# [aria-label="Download"]/[aria-label="ดาวน์โหลด"] confirmed to match ZERO
# elements — the only "download" mat-icon anywhere on the page is nested
# inside a per-batch "ดาวน์โหลดแบบกลุ่ม" (bulk download) button, not a
# per-clip control in the project feed. The signed CDN URL remains useful for
# completion detection and the explicit legacy 720p mode. Production exports
# now open the clip editor and use Flow's free 1080p upscale menu instead.
CDN_VIDEO_RE = re.compile(r"flow-content\.google/video/")


class EstimateUnreadable(RuntimeError):
    """Raised by FlowBrowser.read_credit_estimate() when the live panel's
    credit text cannot be parsed. Deliberately its own type, not a plain
    RuntimeError, so cmd_run can catch it specifically and STOP THE WHOLE
    RUN rather than silently moving on to the next shot — an unreadable
    price is not a free price (task-04851451: the previous behaviour fell
    into the generic per-shot exception handler, which marks one row
    failed and continues to the next todo shot, exactly the "quietly
    proceed past an unknown cost" failure this must not do)."""


class ChipCountMismatch(RuntimeError):
    """Raised by FlowBrowser.submit() itself when handed an
    expected_chip_count that doesn't match the live count it re-reads at
    that instant. task-04851451, incident 2: a proof-shot run logged
    attach_chip() TimeoutErrors for BOTH handles and still reached
    'submitted' — the caller-side hard gate (cmd_run comparing
    live_chip_count to len(shot['chips']) before calling submit) had
    already covered this class of bug once (see the existing
    test_chip_count_mismatch_blocks_submit, from iteration 2) and a
    read-only pull of the actual clip afterward showed both references had
    in fact rendered correctly — attach_chip()'s own return value is
    decoupled from reality (a Playwright click-wait can time out on a
    confirm button that the browser still processes a moment later; the
    DOM chip count is the ground truth, not that boolean). Still: a guard
    that lives only in the caller is one edit away from being skipped.
    This makes the same check unavoidable at the only place credits can be
    spent, exactly like the dry_run guard above."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"expected {expected} chip(s) attached, found {actual} — refusing to submit")
        self.expected = expected
        self.actual = actual


class CreditCapExceeded(RuntimeError):
    """Raised by _submit_or_raise() as a backstop if browser.submit() is
    ever reached despite the cap already being exceeded — belt-and-braces
    alongside cmd_run's own pre-submit check, so a future refactor that
    adds a second path to Submit still cannot spend past the cap."""

    def __init__(self, spent_this_run: int, estimate: int, cap: int):
        super().__init__(
            f"spent={spent_this_run} + estimate={estimate} > cap={cap}")
        self.spent_this_run = spent_this_run
        self.estimate = estimate
        self.cap = cap


# ── pure helpers (no browser — these are what tests/test_flow_shoot.py covers) ──

def parse_only(spec: str) -> set[int]:
    """"37-46" or "37,40,52" or "37-40,52" -> {37,38,...,46} / etc."""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


def is_refusal_text(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("ล้มเหลว") or "อาจละเมิดนโยบาย" in t


def credit_cap_exceeded(spent_this_run: int, estimate: int, cap: int) -> bool:
    return spent_this_run + estimate > cap


def normalize_prompt_whitespace(text: str) -> str:
    """The composer's contenteditable box re-normalizes every run of one or
    more newlines to its own paragraph-break rendering — confirmed live
    2026-09-19 (task-a09ed18a): a single '\\n' between two dialogue lines
    and a blank-line '\\n\\n' between two paragraphs both round-trip through
    the DOM as a different, but internally consistent, number of newlines.
    Every character of actual TEXT survives; only the exact newline COUNT
    does not. Comparing raw strings after a paste therefore always reports
    a false mismatch — this collapses newline runs on both sides so the
    comparison checks content, the thing that can actually go wrong."""
    return re.sub(r"\n+", "\n", text).strip()


def effective_duration(sheet_dur_s: int, force_duration: int | None) -> int:
    """--force-duration (proof shots only) overrides the sheet's per-shot
    duration for BOTH the composer's duration setting and verify_clip's
    tolerance — the two must never disagree, or a shot generated at the
    override length would fail verification against the sheet's length."""
    return force_duration if force_duration is not None else sheet_dur_s


def parse_credit_estimate(text: str) -> int | None:
    m = _CREDIT_RE.search(text or "")
    return int(m.group(1)) if m else None


def first_dialogue_line(prompt: str) -> str | None:
    """The distinctive fragment `pull` searches the feed for — dialogue is
    unique per shot, prompt openings are not (google-flow-ops skill)."""
    m = _DIALOGUE_RE.search(prompt)
    return m.group(1) if m else None


def extract_clip(downloaded: Path, dest_dir: Path, shot_no: int) -> Path:
    """Flow's download arrives as a .zip with one .mp4, or a bare .mp4."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"shot-{shot_no:02d}.mp4"
    suffix = downloaded.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(downloaded) as zf:
            mp4s = [n for n in zf.namelist() if n.lower().endswith(".mp4")]
            if len(mp4s) != 1:
                raise ValueError(f"zip has {len(mp4s)} mp4 entries, expected 1: {mp4s}")
            with zf.open(mp4s[0]) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    elif suffix == ".mp4":
        shutil.copyfile(downloaded, dest)
    else:
        raise ValueError(f"unexpected download type: {downloaded.suffix!r}")
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_video_dimensions(path: Path) -> tuple[int, int]:
    """Return the first video stream's width/height via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0",
         str(path)],
        check=True, capture_output=True, text=True,
    )
    width, height = result.stdout.strip().split(",", 1)
    return int(width), int(height)


def validate_download_option(text: str, resolution: str) -> None:
    """Refuse any paid or mismatched export option before clicking it."""
    normalized = " ".join((text or "").split())
    if resolution != "1080p":
        raise ValueError(f"unsupported upscale resolution: {resolution!r}")
    if "1080p" not in normalized or "เพิ่มความละเอียดแล้ว" not in normalized:
        raise RuntimeError(
            f"live Flow menu is not the expected free 1080p upscale: {normalized!r}")
    if "เครดิต" in normalized:
        raise RuntimeError(
            f"refusing a credit-bearing download option: {normalized!r}")


def verify_clip(path: Path, expected_dur: float,
                expected_resolution: str | None = None) -> tuple[bool, str]:
    """ffprobe duration within tolerance, audio present. Reuses
    clip_review's own probes so the two tools never disagree on what a
    passing clip looks like."""
    if not path.exists():
        return False, "file missing"
    got = clip_review.probe_duration(path)
    if abs(got - expected_dur) > DURATION_TOLERANCE_S:
        return False, f"DURATION got {got:.1f}s want {expected_dur}s"
    db = clip_review.mean_db(path)
    if db is None or db < MIN_AUDIO_DB:
        return False, "NO AUDIO"
    if expected_resolution:
        try:
            width, height = probe_video_dimensions(path)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            return False, f"RESOLUTION unreadable: {e!r}"
        expected = {"720p": (720, 1280), "1080p": (1080, 1920)}.get(
            expected_resolution)
        if expected is None:
            return False, f"RESOLUTION unsupported target {expected_resolution!r}"
        if (width, height) != expected:
            return False, (f"RESOLUTION got {width}x{height} want "
                           f"{expected[0]}x{expected[1]}")
        return True, f"{got:.1f}s {width}x{height}"
    return True, f"{got:.1f}s"


def _log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    # The log file is UTF-8, but stdout on Windows defaults to cp1252 and every
    # shot in this production carries Thai dialogue. An un-encodable character
    # raised UnicodeEncodeError out of print() and killed a run mid-shoot
    # (measured 2026-09-22: 18 shots in, Act 5 stopped at shot 128). Reporting
    # progress must never be able to stop the work, so the console write degrades
    # and the file keeps the real text.
    try:
        print(line)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(line.encode(enc, errors="replace").decode(enc, errors="replace"))
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── the only place that touches a browser ───────────────────────────────────

class FlowBrowser:
    """Playwright-over-CDP adapter. Every method here is one decision the
    brief/skill documented; nothing here is exercised by the unit tests —
    swap this class for a stub with the same method names to test the
    runner's control flow without Chrome."""

    def __init__(self, cdp_url: str = CDP):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None
        # Set by cmd_run right after construction. submit() checks this
        # itself (see below) so dry-run is structurally incapable of
        # spending — not just "the caller happens not to call submit()".
        self.dry_run = False
        # Production exports default to Flow's free 1080p upscale. 720p is
        # retained only as an explicit legacy/debug choice. 4K is deliberately
        # unsupported because the live menu labels it as a 50-credit action.
        self.download_resolution = "1080p"
        # Every flow-content.google/video/<id> response observed on this
        # page, in order — see CDN_VIDEO_RE. This detects completion and
        # supports explicit legacy 720p downloads; normal exports use the
        # editor's free 1080p upscale menu.
        self._captured_video_urls: list[str] = []
        self._pending_download: Path | None = None
        self._last_dialogue: str | None = None
        # Stable project/composer route captured at attach time. Submit moves
        # the live page to /edit/<uuid>; later shots must navigate back here,
        # not reload the clip editor.
        self._project_url: str | None = None

    def _on_response(self, response) -> None:
        if CDN_VIDEO_RE.search(response.url):
            self._captured_video_urls.append(response.url)

    def attach(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = next((pg for pg in ctx.pages if "flow.google.com" in pg.url), None)
        if page is None:
            raise RuntimeError(
                "NO_FLOW_TAB — open the project tab in the automation Chrome first")
        try:
            page.bring_to_front()
        except Exception:
            pass
        page.on("response", self._on_response)
        self.page = page
        # A prior interrupted run may have left the tab on a clip editor.
        # Flow's project composer is the same URL prefix before /edit/<uuid>.
        self._project_url = re.sub(r"/edit/[^/?#]+.*$", "", page.url)
        return page

    def close(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def mute_all_media(self) -> None:
        self.page.evaluate(MUTE_JS)

    def _close_settings_panel(self) -> None:
        """Close the settings overlay without pressing Escape.

        winbox reserves Escape for the resident CookieRun controller, so the
        Flow runner must use the UI's own controls.  The settings trigger is a
        true toggle (confirmed live on 2026-09-20) and removes both the panel
        and its backdrop when clicked a second time.
        """
        panel = self.page.locator("flow-prompt-box-settings")
        if panel.count():
            self.page.locator(
                'button[aria-label="ทริกเกอร์การตั้งค่า"]'
            ).first.click(timeout=3000, force=True)
            panel.wait_for(state="detached", timeout=3000)

    def _close_account_panel(self) -> None:
        panel = self.page.locator("flow-account-panel")
        if panel.count():
            panel.locator('.close-btn[aria-label="ปิดแผงบัญชี"]').first.click(
                timeout=3000)
            panel.wait_for(state="detached", timeout=3000)

    def reset_composer(self) -> None:
        """Reload the current project route before each shot.

        Flow keeps prompt and ingredient chips in the page session across
        separate runner processes. The picker then hides an already-attached
        asset, making a clean retry report ``no matching .asset-item row``;
        worse, stale chips from another shot can satisfy the count-only gate.
        A reload clears composer state at zero credits. Settings are deliberately
        applied after this call because Flow resets them during navigation.
        """
        if not self._project_url:
            raise RuntimeError("project URL unavailable — attach() must run first")
        self.page.goto(self._project_url, wait_until="domcontentloaded", timeout=60_000)
        self.mute_all_media()
        self.page.locator(
            'button[aria-label="ทริกเกอร์การตั้งค่า"]'
        ).first.wait_for(state="visible", timeout=60_000)
        self.mute_all_media()

    def set_settings(self, dur_s: int, resolution: str = "720p") -> dict:
        """Set model=Omni 1.1 Flash, mode=องค์ประกอบ, aspect=9:16, qty=x1,
        resolution, duration=dur_s, then read every one of them back off the
        DOM — NONE of them are sticky (BANCHI-SHOOT-BRIEF.md).

        CORRECTED 2026-09-19 (task-a09ed18a, live --dry-run against the
        automation Chrome): the composer's collapsed pill (aria-label
        "ทริกเกอร์การตั้งค่า") only ever shows facets as flattened TEXT —
        there are no per-facet aria-labels ("Ratio"/"Duration"/"Resolution")
        anywhere in the DOM; the original guesses always timed out. Every
        real facet control lives inside the `<flow-prompt-box-settings>`
        overlay panel that button opens, as an Angular Material
        `mat-button-toggle` group per facet (image/video, เฟรม/องค์ประกอบ,
        aspect, resolution, duration, quantity), matched here by each
        option's own visible text — none of them carry a stable aria-label
        either. The panel defaults to the "รูปภาพ" (Image) tab on a fresh
        open; "วิดีโอ" must be clicked first or every later facet click hits
        the wrong (image-mode) panel.
        """
        page = self.page
        # Never press Escape on winbox: it writes a persistent human-hold
        # marker for the resident CookieRun farm. Close known Flow overlays by
        # their explicit controls instead.
        self._close_account_panel()
        self._close_settings_panel()
        panel = page.locator("flow-prompt-box-settings")
        # Opening the panel is racy in the same way chip-attach is
        # documented as racy (google-flow-ops) — a single click does not
        # reliably land. Poll instead of trusting one click+wait.
        for _ in range(5):
            if panel.count():
                break
            try:
                page.locator('button[aria-label="ทริกเกอร์การตั้งค่า"]').first.click(
                    timeout=3000, force=True)
            except Exception as e:
                _log(f"  settings panel open err: {e!r}")
            page.wait_for_timeout(400)
        if panel.count() == 0:
            _log("  settings panel never opened after 5 attempts")
        # The panel can reopen on either the "รูปภาพ" (Image) or "วิดีโอ"
        # tab depending on what it last showed in this page session — check
        # the actual state (duration buttons only exist in video mode)
        # instead of assuming one click is needed.
        for _ in range(3):
            try:
                txt = panel.evaluate("el => el.innerText") if panel.count() else ""
            except Exception:
                txt = ""
            if "วินาที" in txt:
                break
            try:
                panel.get_by_text("วิดีโอ", exact=True).first.click(timeout=2000)
            except Exception as e:
                _log(f"  video-tab select err: {e!r}")
            page.wait_for_timeout(300)
        try:
            panel.locator('button[aria-label="เลือกกลุ่มผลิตภัณฑ์โมเดล"]').first.click(
                timeout=3000, force=True)
            page.wait_for_timeout(300)
            page.locator("[role=menuitem]").filter(
                has_text="Omni 1.1 Flash"
            ).first.click(timeout=3000, force=True)
        except Exception as e:
            _log(f"  model select err: {e!r}")
            # Close the model menu through its own backdrop so it cannot
            # intercept every following settings click. Never use Escape on
            # winbox: that key is reserved by the resident farm controller.
            try:
                backdrop = page.locator(
                    ".cdk-overlay-backdrop.settings-menu-backdrop"
                ).last
                if backdrop.count():
                    backdrop.click(timeout=3000, force=True)
                    page.wait_for_timeout(200)
            except Exception:
                pass
        try:
            panel.locator("mat-button-toggle").filter(has_text="องค์ประกอบ").first.click(timeout=3000)
        except Exception as e:
            _log(f"  mode select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text="9:16").first.click(timeout=3000)
        except Exception as e:
            _log(f"  ratio select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text=resolution).first.click(timeout=3000)
        except Exception as e:
            _log(f"  resolution select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text=f"{dur_s} วินาที").first.click(timeout=3000)
        except Exception as e:
            _log(f"  duration select err: {e!r}")
        try:
            panel.locator("mat-button-toggle").filter(has_text="x1").first.click(timeout=3000)
        except Exception as e:
            _log(f"  quantity select err: {e!r}")
        page.wait_for_timeout(200)
        settings = self.read_settings(dur_s, resolution)
        self._close_settings_panel()
        page.wait_for_timeout(200)
        return settings

    def _toggle_checked(self, panel, label_text: str) -> bool:
        """mat-button-toggle labels (720p/360p, x1..x4, เฟรม/องค์ประกอบ, every
        aspect ratio, every duration) are ALL rendered at once regardless of
        which is selected — `"720p" in body` is true whether or not 720p is
        the active choice. The selected option alone carries the
        `mat-button-toggle-checked` class on the <mat-button-toggle> wrapper,
        one level above the clickable <button>; that class is the only
        reliable read-back."""
        el = panel.locator("mat-button-toggle").filter(has_text=label_text).first
        if el.count() == 0:
            return False
        return "mat-button-toggle-checked" in (el.get_attribute("class") or "")

    def read_settings(self, dur_s: int, resolution: str = "720p") -> dict:
        page = self.page
        panel = page.locator("flow-prompt-box-settings")
        if panel.count() == 0:
            # Panel already closed — the collapsed pill's flattened text is
            # the only signal left for facets it actually renders (model,
            # aspect, resolution, duration); mode/quantity aren't shown
            # collapsed at all, so they can't be contradicted from here.
            body = page.evaluate("() => document.body.innerText")
            return {
                "model_omni": "Omni 1.1 Flash" in body,
                "mode_ingredients": True,
                "aspect_9_16": "9:16" in body,
                "qty_x1": True,
                "resolution": resolution in body,
                "duration": f"{dur_s} วินาที" in body,
            }
        body = panel.evaluate("el => el.innerText")
        return {
            "model_omni": "Omni 1.1 Flash" in body,
            "mode_ingredients": self._toggle_checked(panel, "องค์ประกอบ"),
            "aspect_9_16": self._toggle_checked(panel, "9:16"),
            "qty_x1": self._toggle_checked(panel, "x1"),
            "resolution": self._toggle_checked(panel, resolution),
            "duration": self._toggle_checked(panel, f"{dur_s} วินาที"),
        }

    def chip_count(self) -> int:
        """CORRECTED 2026-09-19 (task-a09ed18a, live dry-run): a chip is
        <flow-ingredient-chip><flow-*-ingredient-chip>...</...>, not the
        outdated `span.mention-chip[data-entity-id]` (0 matches, always).
        `flow-ingredient-chip` alone is page-wide — every past generation
        card in the feed renders its own (19+ on a modest project) — so this
        must scope to the composer's own bar, `<flow-ingredient-bar
        class="prompt-ingredient-bar">`, confirmed to appear exactly once."""
        return self.page.locator("flow-ingredient-bar flow-ingredient-chip").count()

    def attach_chip(self, handle: str) -> bool:
        """Attach one ingredient by searching the picker's full dataset.

        Live DOM probe 2026-09-19: the picker renders only ten virtualized
        ``.asset-item`` rows, so scanning rendered rows reports valid assets as
        missing. Its search field is the unique page-level
        ``input[aria-label=ค้นหา]``; it is not a DOM descendant of the visible
        ``[role=dialog]`` overlay. The separate project search uses
        ``aria-label=ค้นหาเนื้อหา``. Search forces the matching asset to render.
        Row click may attach directly or
        open a preview with เพิ่มไปยังพรอมต์, so success is always the live
        composer chip count increasing, never merely a click returning.
        """
        page = self.page
        name = handle.lstrip("@")
        before = self.chip_count()

        def close_picker() -> None:
            try:
                dialog = page.locator('[role="dialog"]:visible').last
                if dialog.count():
                    dialog.locator('button[aria-label="ปิด"]').first.click(
                        timeout=3000, force=True)
                    dialog.wait_for(state="hidden", timeout=3000)
                page.wait_for_timeout(200)
            except Exception:
                pass

        try:
            page.locator(
                'button[aria-label="เพิ่มองค์ประกอบลงในช่องพรอมต์"]'
            ).first.click(timeout=3000)
            dialog = page.locator('[role="dialog"]').last
            dialog.wait_for(state="visible", timeout=3000)
            # Current mobile layout labels the picker search "ค้นหาเนื้อหา";
            # older desktop builds used "ค้นหา". Scope both the search and
            # result rows to the dialog so the project-feed search cannot be
            # mistaken for the ingredient picker.
            search = dialog.locator(
                'input[aria-label="ค้นหาเนื้อหา"], input[aria-label="ค้นหา"]'
            ).first
            search.wait_for(state="visible", timeout=3000)

            row = dialog.locator(".asset-item").filter(has_text=handle).first
            matched_query = None
            for query in (handle, name):
                search.fill("")
                search.fill(query)
                try:
                    row.wait_for(state="visible", timeout=4000)
                    matched_query = query
                    break
                except Exception:
                    pass
            if matched_query is None:
                rendered_rows = []
                rows = dialog.locator(".asset-item:visible")
                for i in range(min(rows.count(), 20)):
                    rendered_rows.append(rows.nth(i).inner_text(timeout=1000))
                _log(
                    f"  attach_chip({handle}): no matching row after picker "
                    f"queries={[handle, name]!r} value={search.input_value()!r} "
                    f"rows={rendered_rows!r}"
                )
                close_picker()
                return False

            row.click(timeout=3000)
            for _ in range(4):
                if self.chip_count() > before:
                    return True
                page.wait_for_timeout(250)

            page.get_by_text(
                "เพิ่มไปยังพรอมต์", exact=False
            ).first.click(timeout=3000)
            for _ in range(12):
                if self.chip_count() > before:
                    return True
                page.wait_for_timeout(250)

            _log(f"  attach_chip({handle}): click landed but chip count did not increase")
            close_picker()
            return False
        except Exception as e:
            # A direct attach can close its dialog while a pending locator is
            # resolving; trust the effect at the composer, not that stale UI.
            if self.chip_count() > before:
                return True
            _log(f"  attach_chip({handle}) failed: {e!r}")
            close_picker()
            return False

    def paste_prompt(self, text: str) -> None:
        """CORRECTED 2026-09-19 (task-a09ed18a, live dry-run): typing the
        prompt character-by-character (`keyboard.type`) mashed the sheet's
        blank-line paragraph breaks together with NO separator at all
        ("staircase.In a narrow...", one word run-on) — CDP key events don't
        drive this editor's own paragraph-insertion logic the way a real
        paste does. `keyboard.insert_text()` (CDP Input.insertText, the same
        primitive a paste uses) reproduces every paragraph break correctly.
        The editor still re-normalizes blank-line COUNT on its own terms —
        see normalize_prompt_whitespace() for why the mismatch check must
        compare content, not exact newline counts."""
        box = self.page.locator('[contenteditable="true"]').first
        box.click()
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.press("Backspace")
        box.evaluate("el => el.focus()")
        self.page.keyboard.insert_text(text)
        self._last_dialogue = first_dialogue_line(text)

    def read_prompt_text(self) -> str:
        return self.page.locator('[contenteditable="true"]').first.inner_text()

    def read_credit_estimate(self) -> int:
        """The estimate ("การสร้างจะใช้ N เครดิต") is rendered ONLY inside the
        `<flow-prompt-box-settings>` overlay panel — confirmed live
        2026-09-19: it is present in document.body.innerText while the panel
        is open and gone the instant it closes. BANCHI-SHOOT-BRIEF.md calls
        for reading it "immediately before Submit", so this reopens the
        panel fresh each time rather than reusing a value cached from
        set_settings, and leaves the page exactly as it found it (closes
        the panel again if it opened it)."""
        page = self.page
        panel = page.locator("flow-prompt-box-settings")
        opened_here = panel.count() == 0
        if opened_here:
            for _ in range(5):
                if panel.count():
                    break
                try:
                    page.locator(
                        'button[aria-label="ทริกเกอร์การตั้งค่า"]'
                    ).first.click(timeout=3000, force=True)
                except Exception:
                    pass
                page.wait_for_timeout(400)
            for _ in range(3):
                try:
                    txt = panel.evaluate("el => el.innerText") if panel.count() else ""
                except Exception:
                    txt = ""
                if "วินาที" in txt:
                    break
                try:
                    panel.get_by_text("วิดีโอ", exact=True).first.click(timeout=2000)
                except Exception:
                    pass  # already on วิดีโอ from an earlier open this session
                page.wait_for_timeout(300)
        try:
            text = panel.evaluate("el => el.innerText") if panel.count() else ""
        except Exception:
            text = ""
        if opened_here:
            self._close_settings_panel()
            page.wait_for_timeout(200)
        est = parse_credit_estimate(text)
        if est is None:
            raise EstimateUnreadable(
                "could not read live credit estimate from the panel — "
                "STOP, not a zero: an unreadable price is not a free price")
        return est

    def submit(self, expected_chip_count: int | None = None) -> None:
        if self.dry_run:
            raise RuntimeError(
                "BUG: FlowBrowser.submit() called while dry_run is set — "
                "dry-run must be structurally incapable of spending credits "
                "(task-04851451: 15 real generations fired past two "
                "control-flow-only guards while iteration 2 edited this "
                "file between manual runs)")
        if expected_chip_count is not None:
            actual = self.chip_count()
            if actual != expected_chip_count:
                raise ChipCountMismatch(expected_chip_count, actual)
        self.page.locator('button[aria-label="เริ่มสร้าง"]').first.click()

    def poll_result(self, timeout_s: int = COMPLETION_TIMEOUT_S) -> dict:
        """CORRECTED 2026-09-19 (task-04851451, live read-only check):
        [aria-label="Download"]/[aria-label="ดาวน์โหลด"] match ZERO elements
        on this account — a run polling for them times out after
        COMPLETION_TIMEOUT_S on every success, exactly as REPORT-iter2
        documented happening to its own proof shot. Submit navigates to the
        clip's own /edit/<uuid> page (google-flow-ops, "capture each clip's
        id at SUBMIT"); Flow itself fetches the signed CDN URL to render
        that page's <video>, which _on_response captures. Nudging a muted
        play() every poll is what reliably triggers that fetch — proven
        live against an already-completed clip (200, 381529 bytes, ffprobe
        confirmed 4.01s h264+aac)."""
        page = self.page
        start = time.time()
        baseline = len(self._captured_video_urls)
        while time.time() - start < timeout_s:
            # A project feed may contain refusal text from older shots. Scope
            # policy detection to the batch containing this shot's unique
            # dialogue so historical cards cannot trigger a false retry.
            result_text = ""
            if self._last_dialogue:
                current_prompt = page.get_by_text(
                    self._last_dialogue, exact=False).first
                if current_prompt.count():
                    current_batch = current_prompt.locator(
                        'xpath=ancestor::div[contains(@class,"batch-container")]'
                    ).first
                    if current_batch.count():
                        result_text = current_batch.inner_text()
            if is_refusal_text(result_text):
                m = re.search(r"ล้มเหลว[^\n]*\n[^\n]*", result_text)
                return {"status": "refusal", "text": m.group(0) if m else "ล้มเหลว"}
            if len(self._captured_video_urls) > baseline:
                return {"status": "download", "text": ""}
            # The editor may load the video before poll_result() installs its
            # baseline, or serve it entirely from Chrome's disk cache. In both
            # cases there is no *new* response event, but currentSrc still
            # exposes the same signed CDN URL used by download_card().
            try:
                current_src = page.locator("video").first.evaluate(
                    "v => v.currentSrc || v.src")
                if current_src and CDN_VIDEO_RE.search(current_src):
                    self._captured_video_urls.append(current_src)
                    return {"status": "download", "text": ""}
            except Exception:
                pass
            # Current Flow mobile layout stays on the project feed after
            # Submit instead of navigating to /edit/<uuid>. Once the new card
            # appears, identify it by the shot's unique dialogue, open it, and
            # capture/download its CDN URL using the same cache-safe path as
            # `pull`.
            if self._last_dialogue and "/edit/" not in page.url:
                prompt_match = page.get_by_text(
                    self._last_dialogue, exact=False
                ).first
                if prompt_match.count():
                    batch = prompt_match.locator(
                        'xpath=ancestor::div[contains(@class,"batch-container")]'
                    ).first
                    card = batch.locator("flow-grid-tile-container").first
                    if card.count():
                        try:
                            self._pending_download = self.download_card(card)
                            return {"status": "download", "text": ""}
                        except Exception as e:
                            _log(f"  completed card found but download not ready: {e!r}")
            try:
                page.evaluate(
                    "() => { const v = document.querySelector('video'); "
                    "if (v) { v.muted = true; v.play().catch(() => {}); } }")
            except Exception:
                pass
            time.sleep(POLL_S)
        return {"status": "timeout", "text": ""}

    def _fetch_captured_video(self) -> Path:
        if not self._captured_video_urls:
            raise RuntimeError(
                "no flow-content.google/video/ response ever observed on "
                "this page — nothing to download")
        url = self._captured_video_urls[-1]
        resp = self.page.request.get(url)
        if resp.status != 200:
            raise RuntimeError(f"CDN fetch failed: HTTP {resp.status} for {url}")
        import tempfile
        path = Path(tempfile.mkdtemp()) / "clip.mp4"
        path.write_bytes(resp.body())
        return path

    def _close_download_menus(self) -> None:
        """Dismiss Material menus explicitly, never with Escape."""
        page = self.page
        for _ in range(3):
            backdrops = page.locator(
                ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing")
            visible = [backdrops.nth(i) for i in range(backdrops.count())
                       if backdrops.nth(i).is_visible()]
            if not visible:
                return
            visible[-1].click(force=True)
            page.wait_for_timeout(150)
            # Some Material submenu backdrops consume the click without
            # closing the parent menu. Toggle the editor's already-expanded
            # More button directly; this is the menu's own close action.
            expanded = page.locator(
                'button[aria-label="ตัวเลือกเพิ่มเติม"][aria-expanded="true"]')
            if expanded.count() and expanded.first.is_visible():
                expanded.first.click(force=True)
                page.wait_for_timeout(150)
        remaining = page.locator(
            ".cdk-overlay-backdrop.cdk-overlay-backdrop-showing:visible")
        if remaining.count():
            raise RuntimeError("download menu backdrop would not close")

    def _open_enabled_download_menu(self):
        """Open More and wait until Flow has made Download available.

        The editor route renders before its media model. During that gap the
        genuine Download item exists but carries ``disabled=true`` and cannot
        open the resolution submenu. Reopen the menu while the clip finishes
        initializing instead of mistaking that transient DOM for a selector
        failure.
        """
        page = self.page
        more = page.locator('button[aria-label="ตัวเลือกเพิ่มเติม"]').first
        more.wait_for(state="visible", timeout=30_000)
        deadline = time.time() + 60
        while time.time() < deadline:
            self._close_download_menus()
            more.click()
            download_menu = page.locator('[role="menuitem"]').filter(
                has_text=re.compile(r"ดาวน์โหลด(?:สื่อ|คลิป)")).first
            download_menu.wait_for(state="visible", timeout=5_000)
            if download_menu.is_enabled():
                return download_menu
            self._close_download_menus()
            page.wait_for_timeout(1_000)
        raise RuntimeError(
            "Download stayed disabled for 60s; the editor media did not load")

    def _download_1080p_from_editor(self) -> Path:
        """Use Flow's free 1080p export and wait for the real download.

        Live DOM, 2026-09-20: editor More -> `ดาวน์โหลดสื่อ` (hover) ->
        `1080p / เพิ่มความละเอียดแล้ว`. The neighbouring 4K option says
        `50 เครดิต`; validate_download_option() makes it structurally
        impossible for this path to click a paid entry.
        """
        page = self.page
        if "/edit/" not in page.url:
            raise RuntimeError(
                "1080p upscale requires the clip editor /edit/<id> route")
        try:
            download_menu = self._open_enabled_download_menu()
            option = None
            for _ in range(3):
                download_menu.hover()
                page.wait_for_timeout(500)
                candidate = page.locator(
                    '[role="menuitem"]', has_text="1080p").first
                if candidate.count() and candidate.is_visible():
                    option = candidate
                    break
            if option is None:
                raise RuntimeError(
                    "1080p submenu did not appear after hovering Download")
            validate_download_option(option.inner_text(), "1080p")
            with page.expect_download(timeout=UPSCALE_TIMEOUT_S * 1000) as info:
                option.click()
            download = info.value
            suffix = Path(download.suggested_filename).suffix or ".mp4"
            path = Path(tempfile.mkdtemp()) / f"flow-1080p{suffix}"
            download.save_as(str(path))
            return path
        except Exception:
            self._close_download_menus()
            raise

    def download(self) -> Path:
        """Download the configured export, defaulting to free 1080p upscale."""
        if self._pending_download is not None:
            path = self._pending_download
            self._pending_download = None
            return path
        if self.download_resolution == "1080p":
            return self._download_1080p_from_editor()
        return self._fetch_captured_video()

    def find_card_by_dialogue(self, fragment: str):
        # `pull` may start on an editor URL left by a previous target. Return
        # to the project feed, then use its search input so virtualized cards
        # outside the rendered viewport can be found. Searching by dialogue is
        # the production's documented unique-key convention.
        page = self.page
        if not self._project_url:
            raise RuntimeError("project URL unavailable — attach() must run first")
        # Navigate even when already on the feed: this clears a stale search,
        # picker, or other overlay left by an interrupted retrieval.
        page.goto(self._project_url, wait_until="domcontentloaded", timeout=60_000)
        self.mute_all_media()
        search = page.locator('input[aria-label="ค้นหา"]')
        search.first.wait_for(state="visible", timeout=30_000)
        search.first.fill(fragment)
        prompt_match = page.get_by_text(fragment, exact=False).first
        try:
            prompt_match.wait_for(state="visible", timeout=10_000)
        except Exception:
            return None
        batch = prompt_match.locator(
            'xpath=ancestor::div[contains(@class,"batch-container")]'
        ).first
        card = batch.locator("flow-grid-tile-container").first
        return card if card.count() else None

    def download_card(self, card) -> Path:
        """Open a feed card and download the configured export.

        Normal 1080p uses the editor's free upscale menu. Explicit legacy
        720p mode captures the signed CDN response/currentSrc.
        """
        baseline = len(self._captured_video_urls)
        card.click()
        self.page.wait_for_timeout(1000)
        try:
            self.page.evaluate(MUTE_JS)
        except Exception:
            pass
        if self.download_resolution == "1080p":
            self.page.wait_for_url(re.compile(r"/edit/"), timeout=30_000)
            return self._download_1080p_from_editor()
        deadline = time.time() + COMPLETION_TIMEOUT_S
        while time.time() < deadline and len(self._captured_video_urls) <= baseline:
            # A clip already played in this Chrome profile may come entirely
            # from disk cache, producing no response event. The signed CDN URL
            # is still exposed as video.currentSrc, so capture that directly.
            try:
                current_src = self.page.locator("video").first.evaluate(
                    "v => v.currentSrc || v.src")
                if current_src and CDN_VIDEO_RE.search(current_src):
                    self._captured_video_urls.append(current_src)
                    break
            except Exception:
                pass
            try:
                self.page.evaluate(
                    "() => { const v = document.querySelector('video'); "
                    "if (v) { v.muted = true; v.play().catch(() => {}); } }")
            except Exception:
                pass
            self.page.wait_for_timeout(1000)
        if len(self._captured_video_urls) <= baseline:
            raise RuntimeError(
                "card opened but no new flow-content.google/video/ URL "
                "appeared before timeout — refusing to reuse a prior clip URL")
        return self._fetch_captured_video()


# ── the runner ───────────────────────────────────────────────────────────────

def _submit_or_raise(browser: FlowBrowser, spent_this_run: int, estimate: int,
                      cap: int, expected_chip_count: int) -> None:
    """The ONLY call site for browser.submit() in the whole runner. All
    three money/correctness guards are re-checked here, immediately before
    the call — task-04851451: cmd_run already had a cap check and a
    dry-run check ahead of its one submit() call, in that same order, and
    15 real generations still fired while iteration 2 edited the
    surrounding code between manual runs. Centralizing the check into the
    only function that can spend means a future edit has to remove a guard
    from inside this function, not just avoid tripping over one two lines
    above a call. expected_chip_count is forwarded into submit() itself
    (see ChipCountMismatch) rather than checked only here, so a caller
    skipping this wrapper entirely still can't spend with the wrong
    references attached."""
    if browser.dry_run:
        raise RuntimeError("BUG: _submit_or_raise called while dry_run is set")
    if credit_cap_exceeded(spent_this_run, estimate, cap):
        raise CreditCapExceeded(spent_this_run, estimate, cap)
    browser.submit(expected_chip_count=expected_chip_count)


def _attempt_chip(browser: FlowBrowser, handle: str) -> bool:
    before = browser.chip_count()
    browser.attach_chip(handle)
    for _ in range(5):
        if browser.chip_count() > before:
            return True
        time.sleep(1.5)
    return False


def cmd_run(args: argparse.Namespace, browser_factory=FlowBrowser) -> int:
    """browser_factory is overridable so tests can exercise this control
    flow (e.g. the chip-count hard gate) against a stub instead of a real
    Playwright/CDP connection — nothing else about the CLI changes."""
    sheet_path = Path(args.sheet)
    ledger_path = Path(args.ledger)
    dest = Path(args.dest).expanduser()
    only = parse_only(args.only) if args.only else None

    flow_ledger.init_ledger(sheet_path, ledger_path)
    rows = flow_ledger.load_ledger(ledger_path)
    sheet_shots = {s["shot"]: s for s in flow_ledger.parse_sheet(sheet_path)}

    todo = [n for n in sorted(rows)
            if rows[n]["status"] not in ("verified", "refused")
            and (only is None or n in only)]
    if not todo:
        _log("nothing to do")
        return 0

    if args.force_duration is not None:
        _log(f"*** FORCE-DURATION OVERRIDE ACTIVE: {args.force_duration}s overrides "
             f"every shot's sheet duration in this run, for BOTH the composer's "
             f"duration setting AND verify_clip's tolerance — PROOF SHOTS ONLY, "
             f"never use this for a production run ***")

    browser = browser_factory()
    # Set immediately after construction, before anything else can touch
    # the browser — FlowBrowser.submit() itself refuses while this is set
    # (structural, not "the control flow happens not to call it").
    browser.dry_run = args.dry_run
    browser.download_resolution = getattr(args, "download_resolution", "1080p")
    spent_this_run = 0
    try:
        try:
            browser.attach()
            browser.mute_all_media()
        except Exception as e:
            _log(f"cannot attach to Chrome at {CDP}: {e!r}")
            _log("is scripts/flow/launch-chrome-debug.sh running, "
                 "logged in, with the project tab open?")
            return 1
        _log(f"attached + muted, {len(todo)} row(s) to attempt")

        for n in todo:
            row = rows[n]
            shot = sheet_shots.get(n)
            if shot is None:
                _log(f"shot {n}: not in sheet — skip")
                continue
            dur_s = effective_duration(shot["dur_s"], args.force_duration)
            # Clear any note from a prior failed attempt on this row before
            # trying again — CTO, 19 Sep: a stale "chip never attached" note
            # from an earlier run survived next to a fresh "submitted"
            # status, reading as if the CURRENT attempt was the broken one.
            row["note"] = ""
            try:
                # Flow composer state outlives this Python process. Reset at
                # every shot boundary so retries cannot inherit prompt/chips
                # from a prior dry-run or another shot. This must precede
                # set_settings(): navigation resets those facets too.
                browser.reset_composer()
                settings = browser.set_settings(dur_s, args.resolution)
                bad = [k for k, v in settings.items() if not v]
                if bad:
                    row["status"], row["note"] = "needs_model", f"settings not confirmed: {bad}"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: needs_model — {row['note']}")
                    continue

                attach_fail = None
                for handle in shot["chips"]:
                    if not _attempt_chip(browser, handle):
                        attach_fail = handle
                        break
                if attach_fail:
                    row["status"], row["note"] = "needs_model", f"chip never attached: {attach_fail}"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: needs_model — {row['note']}")
                    continue

                # HARD GATE (CTO, 19 Sep, live proof run task-a09ed18a): a
                # per-handle "count increased" check is not proof the RIGHT
                # count is attached — a shot submitted 2026-09-19T19:03:31
                # despite an attach_chip() timeout logged one second
                # earlier, because _attempt_chip's polling loop alone
                # decided the count had moved. Re-verify the TOTAL live
                # chip count against what this shot needs, one last time,
                # right before anything that can spend credits. A mismatch
                # here is needs_model and MUST NOT reach submit.
                live_chip_count = browser.chip_count()
                if live_chip_count != len(shot["chips"]):
                    row["status"] = "needs_model"
                    row["note"] = (f"chip count mismatch after attach: expected "
                                    f"{len(shot['chips'])}, found {live_chip_count}")
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: needs_model — {row['note']}")
                    continue

                browser.paste_prompt(shot["prompt"])
                actual = browser.read_prompt_text()
                if normalize_prompt_whitespace(actual) != normalize_prompt_whitespace(shot["prompt"]):
                    browser.paste_prompt(shot["prompt"])
                    actual = browser.read_prompt_text()
                    if normalize_prompt_whitespace(actual) != normalize_prompt_whitespace(shot["prompt"]):
                        row["status"], row["note"] = "needs_model", "prompt mismatch after retry"
                        flow_ledger.save_ledger(ledger_path, rows)
                        _log(f"shot {n}: needs_model — prompt mismatch")
                        continue

                estimate = browser.read_credit_estimate()
                if credit_cap_exceeded(spent_this_run, estimate, args.credit_cap):
                    _log(f"CAP REACHED: spent={spent_this_run} + estimate={estimate} "
                         f"> cap={args.credit_cap} — stopping the whole run")
                    break

                if args.dry_run:
                    _log(f"DRY-RUN shot {n}: settings={settings} chips={shot['chips']} "
                         f"resolution={args.resolution} dur_s={dur_s} "
                         f"prompt_verified=True estimate={estimate} credits — stopping before Submit")
                    return 0

                _submit_or_raise(browser, spent_this_run, estimate, args.credit_cap,
                                  expected_chip_count=len(shot["chips"]))
                row["attempts"] = str(int(row.get("attempts") or 0) + 1)
                row["status"] = "submitted"
                flow_ledger.save_ledger(ledger_path, rows)
                spent_this_run += estimate
                _log(f"shot {n}: submitted (attempt {row['attempts']}, est {estimate} credits)")

                result = browser.poll_result()
                if result["status"] == "refusal" and int(row["attempts"]) == 1:
                    _log(f"shot {n}: refused — re-firing identical prompt once (refunded)")
                    _submit_or_raise(browser, spent_this_run, estimate, args.credit_cap,
                                  expected_chip_count=len(shot["chips"]))
                    row["attempts"] = "2"
                    flow_ledger.save_ledger(ledger_path, rows)
                    result = browser.poll_result()

                if result["status"] == "refusal":
                    row["status"], row["note"] = "refused", result["text"]
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: refused — {result['text']!r}")
                    continue
                if result["status"] == "timeout":
                    row["status"], row["note"] = "failed", "timeout"
                    flow_ledger.save_ledger(ledger_path, rows)
                    _log(f"shot {n}: failed — timeout")
                    continue

                row["status"] = "generated"
                flow_ledger.save_ledger(ledger_path, rows)

                downloaded = browser.download()
                time.sleep(DOWNLOAD_GAP_S)
                clip_path = extract_clip(downloaded, dest, n)
                row["file"] = str(clip_path)
                row["status"] = "downloaded"
                flow_ledger.save_ledger(ledger_path, rows)

                ok, reason = verify_clip(
                    clip_path, dur_s,
                    expected_resolution=browser.download_resolution)
                row["sha256"] = sha256_file(clip_path)
                row["got_dur"] = reason
                if ok:
                    row["status"] = "verified"
                else:
                    bad_path = clip_path.with_name("bad-" + clip_path.name)
                    clip_path.rename(bad_path)
                    row["file"], row["status"], row["note"] = str(bad_path), "failed", reason
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: {row['status']} — {reason}")

            except ChipCountMismatch as e:
                # Same severity as the pre-check hard gate above (needs_model,
                # try the next shot) — this is a per-shot reference problem,
                # not a run-wide money-safety issue like the two below.
                row["status"], row["note"] = "needs_model", f"chip count mismatch at submit: {e!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: needs_model — chip count mismatch caught inside "
                     f"submit() itself: {e!r}")
                continue
            except EstimateUnreadable as e:
                row["status"], row["note"] = "failed", f"estimate unreadable: {e!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: CREDIT ESTIMATE UNREADABLE — STOPPING THE WHOLE "
                     f"RUN, not just this shot (an unreadable price is not a "
                     f"free price): {e!r}")
                break
            except CreditCapExceeded as e:
                row["status"], row["note"] = "failed", f"cap exceeded: {e!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: CAP REACHED (backstop) — stopping the whole run: {e!r}")
                break
            except Exception as e:
                row["status"], row["note"] = "failed", f"exception: {e!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: EXCEPTION {e!r}")
                continue
    finally:
        browser.close()

    print(flow_ledger.status_summary(ledger_path))
    final = flow_ledger.load_ledger(ledger_path)
    attempted = [n for n in todo if final[n]["status"] != "todo"]
    all_ok = all(final[n]["status"] == "verified" for n in attempted) if attempted else True
    return 0 if all_ok else 1


def cmd_pull(args: argparse.Namespace) -> int:
    sheet_path = Path(args.sheet)
    ledger_path = Path(args.ledger)
    dest = Path(args.dest).expanduser()
    only = parse_only(args.only) if args.only else None

    flow_ledger.init_ledger(sheet_path, ledger_path)
    rows = flow_ledger.load_ledger(ledger_path)
    sheet_shots = {s["shot"]: s for s in flow_ledger.parse_sheet(sheet_path)}

    targets = [n for n in sorted(rows)
               if rows[n]["status"] != "verified" and (only is None or n in only)]
    if not targets:
        _log("nothing to pull")
        return 0

    browser = FlowBrowser()
    browser.download_resolution = getattr(args, "download_resolution", "1080p")
    try:
        try:
            browser.attach()
            browser.mute_all_media()
        except Exception as e:
            _log(f"cannot attach to Chrome at {CDP}: {e!r}")
            _log("is scripts/flow/launch-chrome-debug.sh running, "
                 "logged in, with the project tab open?")
            return 1
        for n in targets:
            row = rows[n]
            shot = sheet_shots.get(n)
            dialogue = first_dialogue_line(shot["prompt"]) if shot else None
            if not dialogue:
                row["status"], row["note"] = "needs_model", "no dialogue line to search for"
                flow_ledger.save_ledger(ledger_path, rows)
                continue
            card = browser.find_card_by_dialogue(dialogue)
            if card is None:
                row["status"], row["note"] = "needs_model", f"card not found for: {dialogue!r}"
                flow_ledger.save_ledger(ledger_path, rows)
                _log(f"shot {n}: needs_model — card not found")
                continue
            downloaded = browser.download_card(card)
            time.sleep(DOWNLOAD_GAP_S)
            clip_path = extract_clip(downloaded, dest, n)
            ok, reason = verify_clip(
                clip_path, shot["dur_s"],
                expected_resolution=browser.download_resolution)
            row["file"] = str(clip_path)
            row["sha256"] = sha256_file(clip_path)
            row["got_dur"] = reason
            if ok:
                row["status"] = "verified"
            else:
                bad_path = clip_path.with_name("bad-" + clip_path.name)
                clip_path.rename(bad_path)
                row["file"], row["status"], row["note"] = str(bad_path), "failed", reason
            flow_ledger.save_ledger(ledger_path, rows)
            _log(f"shot {n}: {row['status']} — {reason}")
    finally:
        browser.close()

    print(flow_ledger.status_summary(ledger_path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(flow_ledger.status_summary(Path(args.ledger)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--sheet", required=True)
    p_run.add_argument("--ledger", required=True)
    p_run.add_argument("--dest", required=True)
    p_run.add_argument("--credit-cap", type=int, required=True)
    p_run.add_argument("--only", default=None)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--resolution", choices=["720p", "360p"], default="720p",
                        help="Composer resolution facet — read back off the "
                             "settings row like the other settings.")
    p_run.add_argument(
        "--download-resolution", choices=["1080p", "720p"], default="1080p",
        help="Export resolution. Defaults to Flow's free 1080p upscale; 4K "
             "is intentionally unsupported because it costs 50 credits.")
    p_run.add_argument("--force-duration", type=int, default=None,
                        help="PROOF SHOTS ONLY. Overrides the sheet's per-shot "
                             "duration for both the composer's duration setting "
                             "and verify_clip's tolerance.")
    p_run.set_defaults(func=cmd_run)

    p_pull = sub.add_parser("pull")
    p_pull.add_argument("--sheet", required=True)
    p_pull.add_argument("--ledger", required=True)
    p_pull.add_argument("--dest", required=True)
    p_pull.add_argument("--only", default=None)
    p_pull.add_argument(
        "--download-resolution", choices=["1080p", "720p"], default="1080p",
        help="Export resolution. Defaults to Flow's free 1080p upscale.")
    p_pull.set_defaults(func=cmd_pull)

    p_status = sub.add_parser("status")
    p_status.add_argument("--ledger", required=True)
    p_status.set_defaults(func=cmd_status)

    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
