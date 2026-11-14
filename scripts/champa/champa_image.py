#!/usr/bin/env python3
"""Zero-model image runner. Dry-run is offline; paid submissions require a cap.

Exit codes match champa_fire: 0 success, 2 arguments, 3 guard, 4 page/data error.
The ledger uses clip_id for compatibility; for images this is the input name.
"""
from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.champa import champa_fire as video
from scripts.champa.queue_guard import QueueGuard, Refused


def load_prompts(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("prompts must be a JSON list")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each prompt must be an object")
        name, prompt = row.get("name"), row.get("prompt")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("unsafe image name")
        if name in result:
            raise ValueError("duplicate image name")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a nonempty string")
        result[name] = prompt
    return result


class ImageGuard(QueueGuard):
    def _read_ledger(self):
        # Fail closed on damaged history: ignoring a partial write risks duplicates.
        submitted, done = set(), set()
        if self.ledger.exists():
            for line in self.ledger.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("event") not in ("submit", "done") or not isinstance(row.get("clip_id"), str):
                    raise ValueError("invalid image ledger")
                (submitted if row["event"] == "submit" else done).add(row["clip_id"])
        return submitted, done

    def check_paid(self, label, expected, spent, cap):
        # Exactly one integer price; decimals, discounts and ambiguous labels fail closed.
        if not label or not re.fullmatch(r"สร้าง\s*(?:⚡\s*)?[0-9]+", label.strip()):
            raise Refused("unrecognized submit price")
        if video.label_credits(label) != expected:
            raise Refused("submit price differs from expected credits")
        if spent + expected > cap:
            raise Refused("spend cap reached")
        if self.in_flight() >= self.max_in_flight:
            raise Refused("queue cap reached; harvest completed images first")

    def record_submit(self, clip_id, label):
        super().record_submit(clip_id, label)
        # Persist the reservation before the potentially ambiguous browser click.
        with self.ledger.open("ab") as stream:
            os.fsync(stream.fileno())


@contextmanager
def ledger_lock(out):
    out.mkdir(parents=True, exist_ok=True)
    with (out / ".image_queue.lock").open("a") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise Refused("another image runner owns this output directory")
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused("another image runner owns this output directory")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class ImagePage(video.ComposerPage):
    patterns = {
        "model": r"(Nano Banana|Seedream|Flux|GPT Image|Imagen|Seedance|Veo)",
        "ratio": r"^\d+:\d+$",
        "resolution": r"^\d+[Kkp]$",
    }

    def setting_button(self, key):
        return self.page.locator("button >> visible=true").filter(
            has_text=re.compile(self.patterns[key], re.I)
        ).first

    def dismiss_popups(self):
        # Champa shows a "Latest Updates" modal that intercepts every click.
        if not hasattr(self.page, "locator"):
            return
        close = self.page.locator('div.fixed.inset-0 button[aria-label="Close"] >> visible=true')
        if close.count() == 1:
            close.click()
            self.page.wait_for_timeout(500)

    def configure(self, settings):
        # The mode switch is a pair of plain buttons; the selected one carries a
        # highlight <span class="absolute ...">, not aria-selected (live page 2026-11-14).
        tab = self.page.get_by_role("button", name="ภาพ", exact=True).locator("visible=true")
        if tab.count() != 1:
            raise ValueError("image tab missing or ambiguous")
        tab.click()
        self.page.wait_for_timeout(800)
        if tab.locator("span.absolute").count() < 1:
            raise ValueError("image tab did not read back")
        for key, value in settings.items():
            button = self.setting_button(key)
            if button.inner_text().strip() != value:
                button.click()
                self.page.get_by_text(value, exact=True).click()
                self.page.keyboard.press("Escape")
            if self.setting_button(key).inner_text().strip() != value:
                raise ValueError("image setting did not read back")

    def submit_button(self):
        button = self.page.locator('button[aria-label="สร้าง"] >> visible=true')
        if button.count() != 1:
            raise ValueError("submit button missing or ambiguous")
        return button

    def read_label(self):
        return self.submit_button().inner_text().strip()

    def wait(self, ms):
        if hasattr(self.page, "wait_for_timeout"):
            self.page.wait_for_timeout(ms)

    def click_submit(self):
        self.submit_button().click()
        self.page.wait_for_timeout(1000)

    def find_finished_job(self, prompt):
        # Full prompt matching avoids collisions between designs with common prefixes.
        matches = self.page.get_by_text(prompt, exact=True)
        for i in range(matches.count()):
            card = matches.nth(i).locator(
                'xpath=./ancestor::*[.//img and .//button[@aria-label="เพิ่มเติม"]][1]'
            )
            if card.count() != 1:
                continue
            more = card.locator('button[aria-label="เพิ่มเติม"]')
            # The same prompt text also sits outside cards (e.g. a "More info"
            # panel) whose nearest img+button ancestor is the whole history list.
            if more.count() != 1:
                continue
            more.click()
            try:
                link = self.page.locator('a[download]:has-text("ดาวน์โหลด") >> visible=true')
                if link.count() == 1:
                    from urllib.parse import urljoin
                    return urljoin(self.page.url, link.get_attribute("href"))
            finally:
                self.page.keyboard.press("Escape")
        return None


def connect_over_cdp(endpoint):
    # Same CDP lifecycle as the video runner, with cleanup even if navigation fails.
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse
    pw = sync_playwright().start()
    adapter = None
    try:
        browser = pw.chromium.connect_over_cdp(endpoint)
        page = next((p for c in browser.contexts for p in c.pages
                     if (urlparse(p.url).hostname or "") == "champa.io"
                     or (urlparse(p.url).hostname or "").endswith(".champa.io")), None)
        owned = page is None
        if owned:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
        adapter = ImagePage(page, opened_by_script=owned)
        if owned:
            page.goto(video.COMPOSER_URL)
        adapter.dismiss_popups()
        # Do not expose page URLs, including exception messages containing URLs.
        print(f"tab id={id(page)}")
        return adapter, (pw, browser)
    except Exception:
        video.cleanup_cdp(adapter, (pw, None))
        raise


def save_image(adapter, url, destination):
    from PIL import Image
    temporary = destination.with_suffix(".download")
    converted = destination.with_suffix(".png.tmp")
    try:
        adapter.download(url, temporary)
        with Image.open(temporary) as image:
            if image.format not in ("PNG", "JPEG", "WEBP"):
                raise ValueError("unsupported image format")
            image.verify()
        with Image.open(temporary) as image:
            image.convert("RGBA").save(converted, format="PNG")
        converted.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
        converted.unlink(missing_ok=True)


def main(argv=None, adapter=None):
    parser = video.NonExitingArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--out", type=Path, default=Path(os.getenv("WORK_DIR", "output")) / "champa")
    parser.add_argument("--cdp", default="http://127.0.0.1:9280")
    mode = parser.add_mutually_exclusive_group()
    for flag in ("--fire", "--harvest", "--dry-run"):
        mode.add_argument(flag, action="store_true")
    parser.add_argument("--max-credits", type=video.spend_cap_arg)
    parser.add_argument("--expected-credits", type=int, default=2)
    parser.add_argument("--model", default="Nano Banana 2")
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--resolution", default="1K")
    resources = None
    try:
        args = parser.parse_args(argv)
        if args.fire and args.max_credits is None:
            raise ValueError("--fire requires --max-credits")
        if args.expected_credits <= 0:
            raise ValueError("--expected-credits must be positive")
        prompts = load_prompts(args.prompts)
    except (video.ArgumentParsingError, ValueError, OSError):
        print("Invalid arguments or prompts", file=sys.stderr)
        return 2
    try:
        guard = ImageGuard(8, args.out / "image_queue.jsonl")
        if not args.fire and not args.harvest:
            skipped = guard.submitted_ids() | guard.done_ids()
            pending = [name for name in prompts if name not in skipped]
            print(f"DRY model={args.model} ratio={args.ratio} resolution={args.resolution}")
            for name in pending:
                print(f"PLAN {name}: {args.expected_credits} credits")
            print(f"Total credits: {len(pending) * args.expected_credits}")
            return 0
        with ledger_lock(args.out):
            # Validate history before connecting.
            skipped = guard.submitted_ids() | guard.done_ids()
            if adapter is None:
                adapter, resources = connect_over_cdp(args.cdp)
            if args.harvest:
                for name, prompt in prompts.items():
                    if name in guard.done_ids():
                        continue
                    url = adapter.find_finished_job(prompt)
                    if url:
                        path = args.out / f"{name}.png"
                        save_image(adapter, url, path)
                        guard.record_done(name, path)
                        print(f"DONE {name}")
                return 0
            spent = 0
            settings = {key: getattr(args, key) for key in ("model", "ratio", "resolution")}
            for name, prompt in prompts.items():
                if name in skipped:
                    continue
                if spent + args.expected_credits > args.max_credits:
                    raise Refused("spend cap reached")
                adapter.configure(settings)
                if not adapter.has_textbox():
                    raise ValueError("missing prompt textbox")
                adapter.fill_prompt(prompt)
                before = video.parse_balance(adapter.read_balance())
                if before is None:
                    raise ValueError("unreadable balance")
                if before < args.expected_credits:
                    raise Refused("insufficient balance")
                label = adapter.read_label()
                guard.check_paid(label, args.expected_credits, spent, args.max_credits)
                guard.record_submit(name, label)
                spent += args.expected_credits
                adapter.click_submit()
                # Live 2026-11-14: clicks 2 s apart were silently dropped (1 of 6 made).
                # Wait until the charge shows before the next item; no charge = stop.
                after = video.parse_balance(adapter.read_balance())
                for _ in range(getattr(adapter, "confirm_polls", 120)):
                    if after is None or before - after >= args.expected_credits:
                        break
                    getattr(adapter, "wait", lambda ms: None)(1000)
                    after = video.parse_balance(adapter.read_balance())
                if after is None or before - after > args.expected_credits:
                    raise Refused("unexpected or unreadable balance after submit")
                if before - after < args.expected_credits:
                    raise Refused("submit not confirmed: balance unchanged")
                adapter.clear_prompt()
            return 0
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except Exception:
        print("Image page, download, or ledger error; stopped safely", file=sys.stderr)
        if os.environ.get("CHAMPA_DEBUG"): import traceback; traceback.print_exc(limit=4)
        return 4
    finally:
        video.cleanup_cdp(adapter, resources)


if __name__ == "__main__":
    sys.exit(main())
