#!/usr/bin/env python3
"""Higgsfield credit lane runner (CEO 2026-10-01).

Zero-model runner driving Higgsfield video generation on the paid credit lane
with hard spend limits.

CLI:
  --prompts CSV (columns clip_id,prompt) required
  --cdp default http://127.0.0.1:9281
  --out dir, default $WORK_DIR/higgsfield-credit if WORK_DIR is set, else output/higgsfield-credit
  --dry-run is DEFAULT mode; --fire must be given to spend
  --fire requires BOTH --max-per-clip N and --budget N
  --duration, --ratio, --resolution optional
  --limit N clips per run (default all)

Exit codes:
  0: done
  2: bad arguments
  3: SpendRefused
  4: page problem (settings did not read back, label unreadable, textbox missing)
  5: a clip did not finish (timeout / unknown)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.higgsfield.credit_guard import (
    SpendGuard,
    SpendRefused,
    parse_price,
)
from scripts.higgsfield.gen_loop import (
    _hf_urls,
    _ts_from_url,
    _work_dir,
    btn_text,
    download,
    poll_for_result,
    type_prompt,
)


COMPOSER_URL = "https://higgsfield.ai/ai/video"


class ArgumentParsingError(Exception):
    """Raised when command line arguments fail validation."""


class NonExitingArgumentParser(argparse.ArgumentParser):
    """Argument parser that raises an exception instead of calling sys.exit."""

    def error(self, message: str) -> None:
        raise ArgumentParsingError(message)


class ComposerPage:
    """Adapter wrapping Playwright automation calls for the Higgsfield composer."""

    def __init__(self, page, opened_by_script: bool = False):
        self.page = page
        self.opened_by_script = opened_by_script

    def read_label(self) -> str | None:
        """Read the inner text of the submit button."""
        try:
            loc = self.page.locator("button[type=submit]").first
            if loc.count() == 0:
                return None
            txt = loc.inner_text()
            return txt if txt is not None else None
        except Exception:
            return None

    def read_settings(self) -> dict[str, str]:
        """Read current Duration, Ratio, and Resolution button labels."""
        return {
            "duration": btn_text(self.page, "Duration"),
            "ratio": btn_text(self.page, "Ratio"),
            "resolution": btn_text(self.page, "Resolution"),
        }

    def apply_settings(
        self,
        duration: str | None = None,
        ratio: str | None = None,
        resolution: str | None = None,
    ) -> None:
        """Apply Duration, Ratio, and Resolution settings on the page."""
        for _ in range(3):
            try:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(150)
            except Exception:
                pass

        if duration:
            try:
                self.page.locator('button[aria-label="Duration"]').first.click()
                self.page.wait_for_timeout(800)
                dur = self.page.locator('[role=slider][aria-valuemax="15"]')
                if dur.count() == 0:
                    dur = self.page.locator("[role=slider]").nth(1)
                dur.first.click(timeout=3000)
                self.page.wait_for_timeout(200)
                self.page.keyboard.press("Home")
                self.page.wait_for_timeout(250)
                target_dur = str(duration).strip().rstrip("s")
                for _ in range(25):
                    val = dur.first.evaluate(
                        "el=>el.getAttribute('aria-valuenow')"
                    )
                    if val == target_dur:
                        break
                    self.page.keyboard.press("ArrowRight")
                    self.page.wait_for_timeout(70)
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(300)
            except Exception as e:
                print(f"  duration set err: {e!r}", file=sys.stderr)

        if ratio:
            try:
                self.page.locator('button[aria-label="Ratio"]').first.click()
                self.page.wait_for_timeout(700)
                self.page.locator('[class*="group/item"]').filter(
                    has_text=ratio
                ).first.click(timeout=3000)
                self.page.wait_for_timeout(300)
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(250)
            except Exception as e:
                print(f"  ratio set err: {e!r}", file=sys.stderr)

        if resolution:
            try:
                self.page.locator(
                    'button[aria-label="Resolution"]'
                ).first.click()
                self.page.wait_for_timeout(700)
                self.page.locator('[class*="group/item"]').filter(
                    has_text=resolution
                ).first.click(timeout=3000)
                self.page.wait_for_timeout(300)
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(250)
            except Exception as e:
                print(f"  resolution set err: {e!r}", file=sys.stderr)

    def has_textbox(self) -> bool:
        """Check if the prompt textbox div[role=textbox] exists on the page."""
        try:
            return self.page.locator("div[role=textbox]").count() > 0
        except Exception:
            return False

    def type_prompt(self, text: str) -> None:
        """Type the prompt text into the prompt box and commit via Escape."""
        type_prompt(self.page, text)
        self.page.wait_for_timeout(400)
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(400)

    def click_submit(self) -> None:
        """Click the submit button. Exactly ONE submit-click call site in the adapter."""
        self.page.locator("button[type=submit]").first.click()

    def newest_ts(self) -> str:
        """Record the newest hf_<timestamp> currently present in history."""
        try:
            self.page.locator('button:has-text("History")').first.click(
                timeout=2000
            )
        except Exception:
            pass
        return max([_ts_from_url(u) for u in _hf_urls(self.page)] + [""])

    def poll(self, t0_max: str, timeout_s: int = 900) -> dict:
        """Poll history for a completion newer than t0_max."""
        return poll_for_result(self.page, t0_max, timeout_s=timeout_s)

    def download(self, url: str, path: Path) -> int:
        """Download video at url to path."""
        return download(url, path, self.page)

    def close(self) -> None:
        """Close the page ONLY if it was opened by this script."""
        if self.opened_by_script and self.page is not None:
            try:
                self.page.close()
            except Exception:
                pass


WAIT_PRICE_TIMEOUT_S = 5.0
WAIT_PRICE_POLL_S = 0.5


def wait_for_price(
    adapter: ComposerPage,
    timeout_s: float | None = None,
    poll_interval_s: float | None = None,
) -> tuple[int | None, str | None]:
    """Poll adapter.read_label() up to timeout_s (every poll_interval_s) until parse_price is not None."""
    if timeout_s is None:
        timeout_s = WAIT_PRICE_TIMEOUT_S
    if poll_interval_s is None:
        poll_interval_s = WAIT_PRICE_POLL_S

    label = adapter.read_label()
    price = parse_price(label) if label else None
    if price is not None:
        return price, label

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_interval_s)
        label = adapter.read_label()
        price = parse_price(label) if label else None
        if price is not None:
            return price, label

    return None, label


def verify_settings(
    current: dict[str, str],
    expected_duration: str | None,
    expected_ratio: str | None,
    expected_resolution: str | None,
) -> bool:
    """Verify that current settings read back match expected values."""
    if expected_duration is not None:
        target_dur = str(expected_duration).strip().lower().rstrip("s")
        actual_dur = current.get("duration", "").lower()
        if target_dur not in actual_dur:
            return False

    if expected_ratio is not None:
        target_ratio = str(expected_ratio).strip().lower()
        actual_ratio = current.get("ratio", "").lower()
        if target_ratio not in actual_ratio:
            return False

    if expected_resolution is not None:
        target_res = str(expected_resolution).strip().lower().rstrip("p")
        actual_res = current.get("resolution", "").lower()
        if target_res not in actual_res:
            return False

    return True


def connect_over_cdp(cdp_url: str) -> tuple[ComposerPage, tuple[object, object]]:
    """Connect over CDP and attach to or create the Higgsfield composer page."""
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
                    u.hostname == "higgsfield.ai"
                    or (u.hostname and u.hostname.endswith(".higgsfield.ai"))
                ) and u.path.startswith("/ai/video"):
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
    """Clean up page and browser connection according to task rules."""
    if adapter is not None:
        try:
            adapter.close()
        except Exception:
            pass
    if resources is not None:
        playwright, browser = resources
        try:
            browser.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass


def build_parser() -> NonExitingArgumentParser:
    """Build the command line argument parser."""
    parser = NonExitingArgumentParser(
        description="Higgsfield Credit Fire Runner"
    )
    parser.add_argument("--prompts", required=True, help="Prompts CSV path")
    parser.add_argument(
        "--cdp", default="http://127.0.0.1:9281", help="CDP endpoint"
    )
    parser.add_argument("--out", default=None, help="Output directory")
    parser.add_argument(
        "--dry-run", action="store_true", default=False, help="Run in dry-run mode"
    )
    parser.add_argument(
        "--fire", action="store_true", default=False, help="Fire paid generations"
    )
    parser.add_argument(
        "--max-per-clip", type=int, default=None, help="Max credits per clip"
    )
    parser.add_argument(
        "--budget", type=int, default=None, help="Total credit budget"
    )
    parser.add_argument(
        "--duration", default=None, help="Optional duration setting (e.g. 5s)"
    )
    parser.add_argument(
        "--ratio", default=None, help="Optional ratio setting (e.g. 16:9)"
    )
    parser.add_argument(
        "--resolution",
        default=None,
        help="Optional resolution setting (e.g. 1080p)",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of clips to run"
    )
    return parser


def main(
    argv: list[str] | None = None,
    adapter: ComposerPage | None = None,
    guard: SpendGuard | None = None,
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

    # --dry-run is DEFAULT mode; --fire must be given to spend
    if args.fire and args.dry_run:
        print("Cannot specify both --fire and --dry-run", file=sys.stderr)
        return 2

    is_fire = bool(args.fire)

    # --fire requires BOTH --max-per-clip N and --budget N; return 2 before browser
    if is_fire:
        if args.max_per_clip is None or args.budget is None:
            print(
                "Error: --fire requires BOTH --max-per-clip and --budget",
                file=sys.stderr,
            )
            return 2
        if args.max_per_clip <= 0 or args.budget <= 0:
            print(
                "Error: --max-per-clip and --budget must be positive integers",
                file=sys.stderr,
            )
            return 2
    else:
        if args.max_per_clip is not None and args.max_per_clip <= 0:
            print(
                "Error: --max-per-clip must be a positive integer",
                file=sys.stderr,
            )
            return 2
        if args.budget is not None and args.budget <= 0:
            print(
                "Error: --budget must be a positive integer",
                file=sys.stderr,
            )
            return 2

    # Verify prompts CSV exists and has required columns
    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"Error: prompts file not found: {args.prompts}", file=sys.stderr)
        return 2

    rows: list[dict[str, str]] = []
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
    except Exception as e:
        print(f"Error reading prompts CSV: {e}", file=sys.stderr)
        return 2

    # Resolve output directory and ledger path
    if args.out:
        out_dir = Path(args.out)
    else:
        wd = _work_dir()
        if wd:
            out_dir = Path(wd) / "higgsfield-credit"
        else:
            out_dir = Path("output/higgsfield-credit")
    ledger_path = out_dir / "spend.jsonl"

    # Resume: skip any clip_id already in the ledger
    done_ids: set[str] = set()
    if ledger_path.exists():
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "clip_id" in data:
                        done_ids.add(str(data["clip_id"]))
                except Exception:
                    pass

    todo = [r for r in rows if str(r.get("clip_id")) not in done_ids]
    if args.limit and args.limit > 0:
        todo = todo[: args.limit]

    # Instantiate guard if firing
    if is_fire and guard is None:
        guard = SpendGuard(args.max_per_clip, args.budget, ledger_path)

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

        # Apply settings if flags given
        if args.duration or args.ratio or args.resolution:
            adapter.apply_settings(
                duration=args.duration,
                ratio=args.ratio,
                resolution=args.resolution,
            )

        if not is_fire:
            # DRY RUN MODE
            # attach/open, apply settings if flags given, check textbox exists.
            # per clip: type prompt, wait up to 5s until label parses, report DRY line.
            current_settings = adapter.read_settings()
            if not verify_settings(
                current_settings, args.duration, args.ratio, args.resolution
            ):
                print(
                    f"Page problem: settings mismatch {current_settings}",
                    file=sys.stderr,
                )
                return 4

            if not adapter.has_textbox():
                print(
                    "Page problem: textbox div[role=textbox] missing",
                    file=sys.stderr,
                )
                return 4

            has_caps = (
                args.max_per_clip is not None and args.budget is not None
            )
            sim_spent = guard.spent() if guard else (
                SpendGuard(args.max_per_clip, args.budget, ledger_path).spent()
                if (has_caps and ledger_path.exists())
                else 0
            )

            for r in todo:
                cid = str(r["clip_id"])
                prompt_text = str(r.get("prompt", ""))

                adapter.type_prompt(prompt_text)
                price, _ = wait_for_price(adapter)

                if not has_caps:
                    if price is None:
                        would_fire = "no"
                        reason = "unreadable label"
                        price_str = "None"
                    else:
                        would_fire = "no"
                        reason = "caps not given (dry-run)"
                        price_str = str(price)
                else:
                    if price is None:
                        would_fire = "no"
                        reason = "unreadable label"
                        price_str = "None"
                    elif price > args.max_per_clip:
                        would_fire = "no"
                        reason = f"price {price} > max_per_clip {args.max_per_clip}"
                        price_str = str(price)
                    elif sim_spent + price > args.budget:
                        would_fire = "no"
                        reason = f"price {price} + spent {sim_spent} > budget {args.budget}"
                        price_str = str(price)
                    else:
                        would_fire = "yes"
                        reason = "ok"
                        price_str = str(price)
                        sim_spent += price

                print(
                    f"DRY clip_id={cid} price={price_str} would_fire={would_fire} reason={reason}"
                )
            return 0

        # FIRE MODE
        # Per clip, in this order:
        # read settings back (mismatch = exit 4) ->
        # type prompt ->
        # wait up to 5 s until label parses (never parses = exit 4, nothing clicked) ->
        # guard.check(label) (SpendRefused = exit 3, nothing clicked) ->
        # remember newest hf_ timestamp ->
        # click_submit once ->
        # guard.record(clip_id, price) immediately (count spend before outcome) ->
        # poll_for_result ->
        # download to <out>/<clip_id>.mp4.
        # Timeout or unknown result = write outcome, stop run, exit 5.
        for r in todo:
            cid = str(r["clip_id"])
            prompt_text = str(r["prompt"])

            # 1. read settings back (mismatch = exit 4)
            current_settings = adapter.read_settings()
            if not verify_settings(
                current_settings, args.duration, args.ratio, args.resolution
            ):
                print(
                    f"Page problem: settings mismatch on clip {cid}: {current_settings}",
                    file=sys.stderr,
                )
                return 4

            if not adapter.has_textbox():
                print(
                    f"Page problem: prompt textbox div[role=textbox] missing on clip {cid}",
                    file=sys.stderr,
                )
                return 4

            # 2. type prompt
            adapter.type_prompt(prompt_text)

            # 3. wait up to 5 s until the label parses before guard.check
            price, label = wait_for_price(adapter)
            if price is None or label is None:
                print(
                    f"Page problem: submit button label unreadable on clip {cid}: {label!r}",
                    file=sys.stderr,
                )
                return 4

            # 4. guard.check(label) (SpendRefused = exit 3, nothing clicked)
            try:
                price = guard.check(label)
            except SpendRefused as e:
                print(f"SpendRefused on clip {cid}: {e}", file=sys.stderr)
                return 3

            # 5. remember newest hf_ timestamp
            t0_max = adapter.newest_ts()

            # 6. click_submit once (EXACTLY ONE submit-click call site in the loop)
            adapter.click_submit()

            # 7. guard.record(clip_id, price) immediately
            try:
                guard.record(cid, price)
            except SpendRefused as e:
                print(
                    f"SpendRefused during record on clip {cid}: {e}",
                    file=sys.stderr,
                )
                return 3

            # 8. poll_for_result
            result = adapter.poll(t0_max)
            if (
                not isinstance(result, dict)
                or result.get("status") != "download"
                or not result.get("url")
            ):
                print(
                    f"Clip {cid} did not finish: outcome={result}",
                    file=sys.stderr,
                )
                return 5

            # 9. download to <out>/<clip_id>.mp4
            out_dir.mkdir(parents=True, exist_ok=True)
            clip_dest = out_dir / f"{cid}.mp4"
            try:
                adapter.download(result["url"], clip_dest)
            except Exception as e:
                print(
                    f"Download error for clip {cid}: {e}",
                    file=sys.stderr,
                )
                return 5

        return 0

    finally:
        if managed_adapter:
            cleanup_cdp(adapter, resources)


if __name__ == "__main__":
    sys.exit(main())
