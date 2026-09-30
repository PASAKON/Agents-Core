#!/usr/bin/env python3
"""Champa Unlimited runner (CEO 2026-10-01).

Zero-model script driving video generation on champa.io's Unlimited plan
(free, up to 8 jobs in parallel) and downloading results.

CLI:
  --prompts CSV (columns clip_id,prompt) required
  --cdp default http://127.0.0.1:9280 (champa Browser Home)
  --out dir, default $WORK_DIR/champa if WORK_DIR is set, else output/champa
  ledger: <out>/queue.jsonl
  --dry-run is DEFAULT mode
  --fire needs --max-jobs N with 1<=N<=8, else return 2 before connecting
  --model default "Seedance 2.0"
  --ratio default "16:9"
  --duration default "4s"
  --resolution default "720p"
  --harvest (download finished jobs only, no submits)
  --wait (after submitting, keep harvesting until done or --wait-max-min, default 150)

Exit codes:
  0: done
  2: bad arguments
  3: Refused by the guard (or balance drop)
  4: page problem (setting did not read back, label not free, textbox missing, unlimited switch not true)
  5: timed out with jobs still running
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.champa.queue_guard import (
    QueueGuard,
    Refused,
    is_free_label,
)

COMPOSER_URL = "https://champa.io/"
WAIT_LABEL_TIMEOUT_S = 5.0
WAIT_LABEL_POLL_S = 0.5
HARVEST_POLL_INTERVAL_S = 10.0


class ArgumentParsingError(Exception):
    """Raised when command line arguments fail validation."""


class NonExitingArgumentParser(argparse.ArgumentParser):
    """Argument parser that raises an exception instead of calling sys.exit."""

    def error(self, message: str) -> None:
        raise ArgumentParsingError(message)


def parse_balance(text: str | None) -> int | None:
    """Parse integer balance from button text like '1,350'."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def verify_settings(
    current: dict[str, str],
    expected_model: str,
    expected_ratio: str,
    expected_duration: str,
    expected_resolution: str,
) -> tuple[bool, str]:
    """Verify settings read back against expected values."""
    mismatches: list[str] = []
    curr_model = current.get("model", "")
    if curr_model != expected_model:
        mismatches.append(f"model {curr_model!r} != {expected_model!r}")

    curr_ratio = current.get("ratio", "")
    if curr_ratio != expected_ratio:
        mismatches.append(f"ratio {curr_ratio!r} != {expected_ratio!r}")

    curr_dur = current.get("duration", "")
    if curr_dur != expected_duration:
        mismatches.append(f"duration {curr_dur!r} != {expected_duration!r}")

    curr_res = current.get("resolution", "")
    if curr_res != expected_resolution:
        mismatches.append(f"resolution {curr_res!r} != {expected_resolution!r}")

    if mismatches:
        return False, "; ".join(mismatches)
    return True, "ok"


class ComposerPage:
    """Adapter wrapping Playwright automation calls for the champa.io composer."""

    def __init__(self, page, opened_by_script: bool = False):
        self.page = page
        self.opened_by_script = opened_by_script

    def has_textbox(self) -> bool:
        """Check if visible prompt textarea exists."""
        try:
            return self.page.locator("textarea >> visible=true").count() > 0
        except Exception:
            return False

    def fill_prompt(self, text: str) -> None:
        """Fill prompt into the visible textarea."""
        self.page.locator("textarea >> visible=true").first.fill(text)

    def clear_prompt(self) -> None:
        """Clear prompt textarea."""
        self.page.locator("textarea >> visible=true").first.fill("")

    def read_label(self) -> str | None:
        """Read the inner text of the visible submit button."""
        try:
            loc = self.page.locator('button:has-text("ส่งเข้าคิว") >> visible=true').first
            if loc.count() == 0:
                return None
            txt = loc.inner_text()
            return txt.strip() if txt is not None else None
        except Exception:
            return None

    def read_unlimited_switch(self) -> str | None:
        """Read aria-checked of the visible Unlimited switch button."""
        try:
            loc = self.page.locator('button[aria-label="Unlimited"] >> visible=true').first
            if loc.count() == 0:
                return None
            return loc.get_attribute("aria-checked")
        except Exception:
            return None

    def read_balance(self) -> str | None:
        """Read balance from the visible balance button."""
        try:
            loc = self.page.locator('button[aria-label="จำปาและการใช้งาน"] >> visible=true').first
            if loc.count() == 0:
                return None
            txt = loc.inner_text()
            return txt.strip() if txt is not None else None
        except Exception:
            return None

    def read_settings(self) -> dict[str, str]:
        """Read current settings from visible settings bar buttons."""
        settings: dict[str, str] = {
            "model": "",
            "ratio": "",
            "duration": "",
            "resolution": "",
        }
        try:
            # Duration button: exact text matching ^\d+s$ (e.g. "4s")
            dur = self.page.locator("button >> visible=true").filter(
                has_text=re.compile(r"^\d+s$")
            ).first
            if dur.count() > 0:
                settings["duration"] = dur.inner_text().strip()

            # Ratio button: exact text matching ^\d+:\d+$ (e.g. "16:9")
            rat = self.page.locator("button >> visible=true").filter(
                has_text=re.compile(r"^\d+:\d+$")
            ).first
            if rat.count() > 0:
                settings["ratio"] = rat.inner_text().strip()

            # Resolution button: exact text matching ^\d+p$ (e.g. "720p")
            res = self.page.locator("button >> visible=true").filter(
                has_text=re.compile(r"^\d+p$")
            ).first
            if res.count() > 0:
                settings["resolution"] = res.inner_text().strip()

            # Model button: visible button matching known model names
            model_btn = self.page.locator("button >> visible=true").filter(
                has_text=re.compile(r"(Seedance|Veo|Google|Kling|Luma|Wan|Hunyuan)", re.I)
            ).first
            if model_btn.count() > 0:
                settings["model"] = model_btn.inner_text().strip()
        except Exception as e:
            print(f"Error reading settings: {e}", file=sys.stderr)
        return settings

    def apply_settings(
        self,
        model: str | None = None,
        resolution: str | None = None,
    ) -> None:
        """Apply model and resolution settings."""
        if model:
            try:
                curr = self.read_settings().get("model", "")
                if curr != model:
                    model_btn = self.page.locator("button >> visible=true").filter(
                        has_text=re.compile(r"(Seedance|Veo|Google|Kling|Luma|Wan|Hunyuan)", re.I)
                    ).first
                    if model_btn.count() > 0:
                        model_btn.click()
                        self.page.wait_for_timeout(300)
                        opt = self.page.locator("button >> visible=true").filter(
                            has_text=re.compile(rf"^{re.escape(model)}$")
                        ).first
                        if opt.count() > 0:
                            opt.click()
                            self.page.wait_for_timeout(300)
                        self.page.keyboard.press("Escape")
                        self.page.wait_for_timeout(200)
            except Exception as e:
                print(f"Error applying model setting: {e}", file=sys.stderr)

        if resolution:
            try:
                curr = self.read_settings().get("resolution", "")
                if curr != resolution:
                    res_btn = self.page.locator("button >> visible=true").filter(
                        has_text=re.compile(r"^\d+p$")
                    ).first
                    if res_btn.count() > 0:
                        res_btn.click()
                        self.page.wait_for_timeout(300)
                        opt = self.page.locator("button >> visible=true").filter(
                            has_text=re.compile(rf"^{re.escape(resolution)}\b")
                        ).first
                        if opt.count() > 0:
                            opt.click()
                            self.page.wait_for_timeout(300)
                        self.page.keyboard.press("Escape")
                        self.page.wait_for_timeout(200)
            except Exception as e:
                print(f"Error applying resolution setting: {e}", file=sys.stderr)

    def click_submit(self) -> None:
        """Click the submit button. Exactly ONE submit-click call site in the adapter."""
        self.page.locator('button:has-text("ส่งเข้าคิว") >> visible=true').first.click()

    def find_finished_job(self, prompt: str) -> str | None:
        """Identify a job card by prompt (first 60 chars) and return download href if done."""
        prompt_prefix = prompt[:60].strip()
        try:
            candidates = self.page.locator(f':text("{prompt_prefix}") >> visible=true')
            count = candidates.count()
            for i in range(count):
                elem = candidates.nth(i)
                card = elem.locator('xpath=./ancestor-or-self::*[.//button[@aria-label="Play"]][1]')
                if card.count() == 0:
                    continue
                more_btn = card.locator('button[aria-label="เพิ่มเติม"] >> visible=true').first
                if more_btn.count() == 0:
                    continue
                more_btn.click()
                self.page.wait_for_timeout(300)
                download_link = self.page.locator('a[download]:has-text("ดาวน์โหลด") >> visible=true').first
                href = None
                if download_link.count() > 0:
                    href = download_link.get_attribute("href")
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(200)
                if href and (href.endswith(".mp4") or "champa.io" in href):
                    return href
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
        return None

    def download(self, url: str, path: Path) -> int:
        """Download video at url using page cookies."""
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            cookies = self.page.context.cookies(url)
            if cookies:
                headers["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        except Exception:
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=240) as r, open(path, "wb") as f:
            f.write(r.read())
        return path.stat().st_size

    def close(self) -> None:
        """Close ONLY a page this script opened."""
        if self.opened_by_script and self.page is not None:
            try:
                self.page.close()
            except Exception:
                pass


def wait_for_free_label(
    adapter: ComposerPage,
    timeout_s: float | None = None,
    poll_s: float | None = None,
) -> tuple[bool, str | None]:
    """Poll adapter.read_label() up to timeout_s until is_free_label(label) is True."""
    if timeout_s is None:
        timeout_s = WAIT_LABEL_TIMEOUT_S
    if poll_s is None:
        poll_s = WAIT_LABEL_POLL_S

    label = adapter.read_label()
    if is_free_label(label):
        return True, label

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_s)
        label = adapter.read_label()
        if is_free_label(label):
            return True, label
    return False, label


def connect_over_cdp(cdp_url: str) -> tuple[ComposerPage, tuple[object, object]]:
    """Connect over CDP and attach to existing champa.io page or open a new one."""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
    except Exception:
        playwright.stop()
        raise

    target_page = None
    opened_by_script = False

    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                u = urllib.parse.urlparse(pg.url)
                if (
                    u.hostname == "champa.io"
                    or (u.hostname and u.hostname.endswith(".champa.io"))
                ):
                    target_page = pg
                    break
            except Exception:
                pass
        if target_page is not None:
            break

    if target_page is None:
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        target_page = ctx.new_page()
        target_page.goto(COMPOSER_URL)
        opened_by_script = True
    else:
        try:
            target_page.bring_to_front()
        except Exception:
            pass

    adapter = ComposerPage(target_page, opened_by_script=opened_by_script)
    return adapter, (playwright, browser)


def cleanup_cdp(
    adapter: ComposerPage | None, resources: tuple[object, object] | None
) -> None:
    """Close only script-opened page and disconnect playwright; never close browser."""
    if adapter is not None:
        try:
            adapter.close()
        except Exception:
            pass
    if resources is not None:
        playwright, _ = resources
        try:
            playwright.stop()
        except Exception:
            pass


def harvest_loop(
    adapter: ComposerPage,
    guard: QueueGuard,
    prompts_map: dict[str, str],
    out_dir: Path,
    wait: bool = False,
    wait_max_min: float = 150.0,
    poll_interval_s: float | None = None,
) -> int:
    """Download finished jobs that are submitted but not yet marked done."""
    if poll_interval_s is None:
        poll_interval_s = HARVEST_POLL_INTERVAL_S

    deadline = time.time() + (wait_max_min * 60.0 if wait else 0.0)
    out_dir.mkdir(parents=True, exist_ok=True)

    while True:
        pending_ids = [
            cid for cid in prompts_map.keys()
            if cid in guard.submitted_ids() and cid not in guard.done_ids()
        ]
        for cid in guard.submitted_ids():
            if cid not in guard.done_ids() and cid not in pending_ids:
                pending_ids.append(cid)
        if not pending_ids:
            return 0

        for cid in pending_ids:
            prompt = prompts_map.get(cid, "")
            href = adapter.find_finished_job(prompt)
            if href:
                dest_path = out_dir / f"{cid}.mp4"
                try:
                    adapter.download(href, dest_path)
                    guard.record_done(cid, dest_path)
                except Exception as e:
                    print(f"Error downloading clip {cid}: {e}", file=sys.stderr)

        remaining = [cid for cid in guard.submitted_ids() if cid not in guard.done_ids()]
        if not remaining:
            return 0

        if not wait:
            return 0

        if time.time() >= deadline:
            print(
                f"Timed out after {wait_max_min} min with {len(remaining)} jobs still running: {remaining}",
                file=sys.stderr,
            )
            return 5

        sleep_dur = min(poll_interval_s, max(0.0, deadline - time.time()))
        time.sleep(sleep_dur)


def build_parser() -> NonExitingArgumentParser:
    """Build the command line argument parser."""
    parser = NonExitingArgumentParser(description="Champa Unlimited Fire Runner")
    parser.add_argument("--prompts", required=True, help="Prompts CSV path (clip_id,prompt)")
    parser.add_argument(
        "--cdp", default="http://127.0.0.1:9280", help="CDP endpoint"
    )
    parser.add_argument("--out", default=None, help="Output directory")
    parser.add_argument(
        "--dry-run", action="store_true", default=False, help="Run in dry-run mode"
    )
    parser.add_argument(
        "--fire", action="store_true", default=False, help="Fire video generation"
    )
    parser.add_argument(
        "--max-jobs", type=int, default=None, help="Max parallel jobs (1..8)"
    )
    parser.add_argument(
        "--model", default="Seedance 2.0", help="Model name (default Seedance 2.0)"
    )
    parser.add_argument(
        "--ratio", default="16:9", help="Aspect ratio (default 16:9)"
    )
    parser.add_argument(
        "--duration", default="4s", help="Duration (default 4s)"
    )
    parser.add_argument(
        "--resolution", default="720p", help="Resolution (default 720p)"
    )
    parser.add_argument(
        "--harvest", action="store_true", default=False, help="Download finished jobs only, no submits"
    )
    parser.add_argument(
        "--wait", action="store_true", default=False, help="Keep harvesting until done or wait-max-min"
    )
    parser.add_argument(
        "--wait-max-min", type=float, default=150.0, help="Wait timeout in minutes (default 150)"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of clips to run"
    )
    return parser


def main(
    argv: list[str] | None = None,
    adapter: ComposerPage | None = None,
    guard: QueueGuard | None = None,
) -> int:
    """Main CLI runner entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except (ArgumentParsingError, Exception) as e:
        print(f"Argument parsing error: {e}", file=sys.stderr)
        return 2

    # Validate mode combinations
    if args.fire and args.dry_run:
        print("Cannot specify both --fire and --dry-run", file=sys.stderr)
        return 2

    if args.fire and args.harvest:
        print("Cannot specify both --fire and --harvest", file=sys.stderr)
        return 2

    is_fire = bool(args.fire)
    is_harvest = bool(args.harvest)
    is_dry_run = not is_fire and not is_harvest

    # --fire needs --max-jobs N with 1<=N<=8, else print why and return 2 BEFORE connecting
    if is_fire:
        if args.max_jobs is None:
            print("Error: --fire requires --max-jobs N with 1<=N<=8", file=sys.stderr)
            return 2
        if args.max_jobs < 1 or args.max_jobs > 8:
            print(f"Error: --max-jobs must be between 1 and 8, got {args.max_jobs}", file=sys.stderr)
            return 2
    else:
        if args.max_jobs is not None and (args.max_jobs < 1 or args.max_jobs > 8):
            print(f"Error: --max-jobs must be between 1 and 8, got {args.max_jobs}", file=sys.stderr)
            return 2

    if args.wait_max_min < 0:
        print(f"Error: --wait-max-min must be non-negative, got {args.wait_max_min}", file=sys.stderr)
        return 2

    # Validate prompts CSV
    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"Error: prompts file not found: {args.prompts}", file=sys.stderr)
        return 2

    rows: list[dict[str, str]] = []
    prompts_map: dict[str, str] = {}
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if (
                not reader.fieldnames
                or "clip_id" not in reader.fieldnames
                or "prompt" not in reader.fieldnames
            ):
                print(
                    "Error: prompts CSV must contain clip_id,prompt columns",
                    file=sys.stderr,
                )
                return 2
            for row in reader:
                rows.append(row)
                prompts_map[str(row["clip_id"])] = str(row.get("prompt", ""))
    except Exception as e:
        print(f"Error reading prompts CSV: {e}", file=sys.stderr)
        return 2

    # Resolve output directory and ledger path
    if args.out:
        out_dir = Path(args.out)
    else:
        work_dir = os.environ.get("WORK_DIR")
        if work_dir:
            out_dir = Path(work_dir) / "champa"
        else:
            out_dir = Path("output/champa")
    ledger_path = out_dir / "queue.jsonl"

    # Instantiate guard
    if guard is None:
        guard = QueueGuard(max_in_flight=args.max_jobs or 8, ledger=ledger_path)

    # Resume: skip clip_ids already submitted in the ledger
    submitted_ids = guard.submitted_ids()
    todo = [r for r in rows if str(r.get("clip_id")) not in submitted_ids]
    if args.limit and args.limit > 0:
        todo = todo[: args.limit]

    resources: tuple[object, object] | None = None
    managed_adapter = False

    try:
        if adapter is None:
            try:
                adapter, resources = connect_over_cdp(args.cdp)
                managed_adapter = True
            except Exception as e:
                print(f"Failed to connect to browser over CDP: {e}", file=sys.stderr)
                return 4

        # Unlimited switch must be true; never click it
        switch_val = adapter.read_unlimited_switch()
        if switch_val != "true":
            print(
                f"Page problem: Unlimited switch aria-checked is {switch_val!r}, expected 'true'",
                file=sys.stderr,
            )
            return 4

        # Apply settings
        adapter.apply_settings(model=args.model, resolution=args.resolution)

        # HARVEST ONLY MODE
        if is_harvest:
            return harvest_loop(
                adapter=adapter,
                guard=guard,
                prompts_map=prompts_map,
                out_dir=out_dir,
                wait=args.wait,
                wait_max_min=args.wait_max_min,
            )

        # DRY RUN MODE
        if is_dry_run:
            if not adapter.has_textbox():
                print("Page problem: textbox missing", file=sys.stderr)
                return 4

            current_settings = adapter.read_settings()
            settings_ok, mismatch_msg = verify_settings(
                current_settings, args.model, args.ratio, args.duration, args.resolution
            )
            settings_str = "ok" if settings_ok else f"mismatch {mismatch_msg}"

            had_mismatch = not settings_ok
            had_unfree = False

            for r in todo:
                cid = str(r["clip_id"])
                prompt_text = str(r.get("prompt", ""))

                adapter.fill_prompt(prompt_text)
                is_free, label = wait_for_free_label(adapter)
                free_str = "yes" if is_free else "no"
                if not is_free:
                    had_unfree = True

                print(
                    f"DRY clip_id={cid} free={free_str} label={label} settings={settings_str}"
                )
                adapter.clear_prompt()

            if had_mismatch or had_unfree:
                return 4
            return 0

        # FIRE MODE
        # Read balance before first submit
        initial_balance_text = adapter.read_balance()
        initial_balance = parse_balance(initial_balance_text)

        submits_this_run = 0
        for r in todo:
            if submits_this_run >= args.max_jobs:
                break

            cid = str(r["clip_id"])
            prompt_text = str(r.get("prompt", ""))

            # 1. settings read back OK -> exit 4 if mismatch
            current_settings = adapter.read_settings()
            settings_ok, mismatch_msg = verify_settings(
                current_settings, args.model, args.ratio, args.duration, args.resolution
            )
            if not settings_ok:
                print(
                    f"Page problem: settings mismatch on clip {cid}: {mismatch_msg}",
                    file=sys.stderr,
                )
                return 4

            if not adapter.has_textbox():
                print(
                    f"Page problem: prompt textarea missing on clip {cid}",
                    file=sys.stderr,
                )
                return 4

            # 2. fill prompt
            adapter.fill_prompt(prompt_text)

            # 3. wait up to 5 s (poll 0.5 s) until is_free_label(label)
            is_free, label = wait_for_free_label(adapter)
            if label is None:
                print(
                    f"Page problem: submit button label unreadable on clip {cid}",
                    file=sys.stderr,
                )
                return 4

            # 4. guard.check(label) -> Refused = exit 3
            try:
                guard.check(label)
            except Refused as e:
                print(f"Refused by guard on clip {cid}: {e}", file=sys.stderr)
                return 3

            # 5. click_submit once (EXACTLY ONE submit-click call site in the loop)
            adapter.click_submit()

            # 6. record_submit immediately
            guard.record_submit(cid, label)
            submits_this_run += 1

            # Check balance after submit; stop if dropped
            post_balance_text = adapter.read_balance()
            post_balance = parse_balance(post_balance_text)
            if (
                initial_balance is not None
                and post_balance is not None
                and post_balance < initial_balance
            ):
                print(
                    f"Balance dropped from {initial_balance} to {post_balance}! Stopping run.",
                    file=sys.stderr,
                )
                return 3

        # Read balance after last submit
        final_balance_text = adapter.read_balance()
        final_balance = parse_balance(final_balance_text)
        if (
            initial_balance is not None
            and final_balance is not None
            and final_balance < initial_balance
        ):
            print(
                f"Balance dropped from {initial_balance} to {final_balance}! Stopping run.",
                file=sys.stderr,
            )
            return 3

        # If --wait, keep harvesting until every submitted clip is done or timeout
        if args.wait:
            ret = harvest_loop(
                adapter=adapter,
                guard=guard,
                prompts_map=prompts_map,
                out_dir=out_dir,
                wait=True,
                wait_max_min=args.wait_max_min,
            )
            if ret != 0:
                return ret

        return 0

    finally:
        if managed_adapter:
            cleanup_cdp(adapter, resources)


if __name__ == "__main__":
    sys.exit(main())
