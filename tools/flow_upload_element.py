#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload a local image into a Google Flow project with NO human click, then
attach it as a composer chip (an "Element" / องค์ประกอบ reference) — the probe
docs/ops/briefs/taachang-characters.md Part B asked for.

Flow's "เมนูเพิ่มสื่อ → อัปโหลด" (Add media -> Upload) looks like a call to
`showOpenFilePicker()`: no `<input type=file>` ever enters the DOM, so the
claude-in-chrome extension's file_upload tool and a synthetic JS click both
fail on it (see the google-flow-ops skill, "What the frame picker will
actually show you"). Three methods were to be tried in order, and the first
one worked, live, on 2026-09-25 (task-c2723478):

    1. page.expect_file_chooser() around the อัปโหลด click, then set_files().
       WORKED — an <input type=file> is created lazily for exactly this
       click, Playwright's file-chooser interception catches it, and the
       image uploads and appears in the project's media grid.

Methods 2 (override window.showOpenFilePicker with an in-page File) and 3
(synthetic drag/drop with a DataTransfer) were never needed and are not
implemented here — see the REPORT for what would be tried next if method 1
ever regresses.

After upload, "turning it into a character Element" does NOT mean Flow's
separate "สร้างตัวละคร" (Create Character) flow — that is a generator (model
group selector, "เริ่มสร้าง" submit) and would re-render the face from a
prompt, which is exactly the identity drift this production is trying to
avoid, and it may not be free (unverified — never clicked "เริ่มสร้าง" to
check). Instead: rename the uploaded plain image to the handle, then use its
right-click "เพิ่มไปยังพรอมต์" (add to prompt) item, which is Flow's actual
reference-chip mechanism — the same action a picker's "เพิ่มไปยังพรอมต์"
button performs. Both steps are confirmed free (no "เริ่มสร้าง" involved).

    python3 tools/flow_upload_element.py \\
        --cdp-url http://127.0.0.1:9223 \\
        --project-url https://flow.google.com/project/<uuid> \\
        --file /Users/gob/MoonieXHQ/Work/<task-id>/out/plates/pa__face.png \\
        --name pa__face \\
        [--dry-run]

If --project-url is omitted, a new project is created and named --project-name
(default "ตาชั่งของเสี่ย"). Prefer passing --project-url explicitly — reusing
one project for a whole cast keeps every Element in one place.

HARD, per the brief: if any control on the way shows a credit cost, this
tool stops and prints the exact text instead of clicking it. Upload and the
attach steps measured on 2026-09-25 show no priced control at all — only
"เริ่มสร้าง" (Start creating / Submit) is priced, and this tool never touches
it.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import flow_cdp  # noqa: E402

CDP_DEFAULT = flow_cdp.DEFAULT_CDP
FLOW_HOME = "https://labs.google/fx/th/tools/flow"

MUTE_JS = """
document.querySelectorAll('video,audio').forEach(v => {v.muted = true; v.volume = 0;});
new MutationObserver(() => document.querySelectorAll('video,audio')
  .forEach(v => {v.muted = true; v.volume = 0;}))
  .observe(document.documentElement, {childList: true, subtree: true});
""".strip()

# Any button whose visible text looks like a priced action carries a number
# after the label ("เริ่มสร้าง 20"); a free one reads e.g. "เริ่มสร้าง" alone.
# We never click เริ่มสร้าง in this tool, but we still scan for stray priced
# text anywhere on the page before acting, per the brief's HARD stop.
_PRICE_RE = re.compile(r"(เครดิต|credit)", re.IGNORECASE)


class FlowUploadError(RuntimeError):
    pass


class CreditGuardError(RuntimeError):
    """Raised when a priced control is visible; the caller must stop and
    report the exact text, never click through it."""


class FlowUploader:
    """Playwright-over-CDP adapter, same shape as tools/flow_shoot.py's
    FlowBrowser and tools/chatgpt_images.py's ChatGPTBrowser."""

    def __init__(self, cdp_url: str = CDP_DEFAULT):
        self.cdp_url = cdp_url
        self._pw = None
        self._browser = None
        self.page = None

    def attach(self):
        flow_cdp.enforce_platform()
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        ctx = self._browser.contexts[0]
        page = ctx.new_page()  # never reuse a tab another task may be driving
        # A fresh CDP tab comes up ~1114x662; at that size Flow's layout never shows the
        # อัปโหลด item as clickable and the click times out (CTO, 2026-09-25).
        page.set_viewport_size({"width": 1600, "height": 1000})
        self.page = page
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

    def menuitem(self, text: str):
        """The visible menu item carrying this text. Plain get_by_text(...).first also
        matches filter tabs and tile captions elsewhere on the page."""
        return self.page.get_by_role("menuitem").filter(has_text=text).first

    def mute_all_media(self) -> None:
        self.page.evaluate(MUTE_JS)

    def check_signed_in(self) -> bool:
        """google-flow-ops: signed-out redirects everything to /about with no
        error text. An avatar/account aria-label means signed in."""
        labels = self.page.evaluate(
            "[...document.querySelectorAll('[aria-label]')]"
            ".map(e => e.getAttribute('aria-label'))"
        )
        return any("บัญชี Google" in (l or "") for l in labels)

    def scan_for_price(self, context: str) -> None:
        body = self.page.evaluate("document.body.innerText")
        if _PRICE_RE.search(body):
            lines = [l for l in body.splitlines() if _PRICE_RE.search(l)]
            raise CreditGuardError(
                f"priced text visible during {context}: {lines[:5]!r}"
            )

    def open_or_create_project(self, project_url: str | None, project_name: str) -> str:
        if project_url:
            self.page.goto(project_url, wait_until="domcontentloaded", timeout=45_000)
            self.page.wait_for_timeout(2000)
            self.mute_all_media()
            return project_url

        self.page.goto(FLOW_HOME, wait_until="domcontentloaded", timeout=45_000)
        self.page.wait_for_timeout(2500)
        self.mute_all_media()
        if not self.check_signed_in():
            raise FlowUploadError("not signed in to Google — hard stop, do not sign in")
        self.page.get_by_text("โปรเจ็กต์ใหม่", exact=False).first.click()
        self.page.wait_for_timeout(4000)
        new_url = self.page.url

        name_input = self.page.locator("input.editable-text-input").first
        name_input.click()
        name_input.press("Meta+A")  # Ctrl+A on this Mac Chrome moves to line
        name_input.type(project_name, delay=30)  # start (emacs binding), not
        name_input.press("Enter")                # select-all — use Meta+A.
        self.page.wait_for_timeout(1000)
        return new_url

    def upload_via_file_chooser(self, file_path: Path) -> None:
        """Method 1 (the one that worked): page.expect_file_chooser() around
        the อัปโหลด click, then set_files()."""
        self.page.get_by_label("เมนูเพิ่มสื่อ").click()
        self.page.wait_for_timeout(800)
        self.scan_for_price("add-media menu")
        # get_by_text("อัปโหลด").first is WRONG once the project holds uploads: the filter
        # tabs "รายการที่อัปโหลด" / "รูปภาพที่อัปโหลด" appear and match first (CTO, 2026-09-25).
        with self.page.expect_file_chooser(timeout=8000) as fc_info:
            self.menuitem("อัปโหลด").click()
        fc_info.value.set_files(str(file_path))
        for _ in range(45):
            if self.page.get_by_label(file_path.name).count() > 0:
                break
            self.page.wait_for_timeout(1000)
        else:
            raise FlowUploadError("uploaded tile did not appear within 45s")
        self.page.wait_for_timeout(1500)  # let the upload progress % clear

    def find_tile(self, label: str, timeout_s: int = 12):
        """The grid tile whose aria-label is exactly `label`, or None.

        Flow's media grid is virtualised: only the newest few tiles are in the DOM, so a
        plain get_by_label misses older assets (measured 2026-09-25: 6 of 23 rendered).
        Filter with the project search box first so the tile is forced to render."""
        tile = self.page.get_by_label(label, exact=True)
        if tile.count():
            return tile.first
        search = self.page.locator('input[aria-label="ค้นหา"]').first
        try:
            search.fill(label)
        except Exception:
            return None
        for _ in range(timeout_s * 2):
            if tile.count():
                return tile.first
            self.page.wait_for_timeout(500)
        return None

    def clear_search(self) -> None:
        try:
            self.page.locator('input[aria-label="ค้นหา"]').first.fill("")
            self.page.wait_for_timeout(800)
        except Exception:
            pass

    def open_context_item(self, label: str, item: str, tries: int = 15) -> None:
        """Right-click the tile until its menu offers `item`. A freshly uploaded tile
        shows a reduced menu (no เปลี่ยนชื่อ) until the upload has settled; one fixed
        wait after upload lost 21 of 21 renames in one batch (2026-09-25)."""
        for _ in range(tries):
            tile = self.find_tile(label)
            if tile is None:
                raise FlowUploadError(f"tile {label!r} not found in the project")
            tile.click(button="right")
            self.page.wait_for_timeout(700)
            self.scan_for_price("asset context menu")
            mi = self.menuitem(item)
            if mi.count() and mi.is_visible():
                mi.click()
                return
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(2000)
        raise FlowUploadError(f"context menu of {label!r} never offered {item!r}")

    def rename_asset(self, old_label: str, new_name: str) -> None:
        self.open_context_item(old_label, "เปลี่ยนชื่อ")
        self.page.wait_for_timeout(600)
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.type(new_name, delay=30)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(1000)
        self.clear_search()

    def attach_as_element(self, label: str) -> bool:
        """Right-click -> เพิ่มไปยังพรอมต์. Returns True if a chip
        (alt="รูปภาพองค์ประกอบ") is now present in the composer."""
        self.open_context_item(label, "เพิ่มไปยังพรอมต์")
        self.page.wait_for_timeout(1200)
        chip_count = self.page.evaluate(
            "document.querySelectorAll('img[alt=\"รูปภาพองค์ประกอบ\"]').length"
        )
        return chip_count > 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdp-url", default=None,
                     help="Flow automation Chrome's CDP endpoint. Defaults to "
                          "$FLOW_CDP, else the winbox default (tools/flow_cdp.py).")
    ap.add_argument("--project-url", default=None,
                     help="reuse an existing Flow project; omit to create one")
    ap.add_argument("--project-name", default="ตาชั่งของเสี่ย",
                     help="only used when --project-url is omitted")
    ap.add_argument("--file", required=True, help="local image to upload")
    ap.add_argument("--name", required=True,
                     help="handle to rename the uploaded asset to, e.g. pa__face")
    ap.add_argument("--dry-run", action="store_true",
                     help="check CDP connection and signed-in state only")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    file_path = Path(args.file).expanduser().resolve()
    if not args.dry_run and not file_path.is_file():
        print(f"ERROR: file not found: {file_path}", file=sys.stderr)
        return 2

    uploader = FlowUploader(flow_cdp.pick_cdp_url(args.cdp_url))
    try:
        uploader.attach()
        if args.dry_run:
            uploader.page.goto(FLOW_HOME, wait_until="domcontentloaded", timeout=45_000)
            uploader.page.wait_for_timeout(2000)
            uploader.mute_all_media()
            signed_in = uploader.check_signed_in()
            print(f"DRY RUN: signed_in={signed_in}, would upload {file_path.name} as {args.name}")
            return 0 if signed_in else 1

        project_url = uploader.open_or_create_project(args.project_url, args.project_name)
        print(f"PROJECT: {project_url}")
        uploader.scan_for_price("project load")
        uploader.upload_via_file_chooser(file_path)
        print(f"UPLOADED: {file_path.name}")
        uploader.rename_asset(file_path.name, args.name)
        print(f"RENAMED: {file_path.name} -> {args.name}")
        bound = uploader.attach_as_element(args.name)
        print(f"ELEMENT_CHIP_BOUND: {bound}")
        if not bound:
            print("WARNING: attach click ran but no รูปภาพองค์ประกอบ chip was found",
                  file=sys.stderr)
            return 1
        return 0
    except CreditGuardError as e:
        print(f"STOP — priced control visible, not clicking: {e}", file=sys.stderr)
        return 3
    except (FlowUploadError, Exception) as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        uploader.close()


if __name__ == "__main__":
    raise SystemExit(main())
