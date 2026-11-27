#!/usr/bin/env python3
"""
champa_fire.py — Champa.io batch B-roll generator & rolling queue harvester for BLACK LIQUIDITY.

Supports two modes:
  1. Unlimited mode (default): requires `Unlimited` switch ON and submit label `ส่งเข้าคิว Unlimited 0`.
  2. Credit-authorized mode (`--allow-credits --max-credits N`, authorized by CEO on Q-20261108-2210-24ed):
     uses existing account จำปา balance up to `--max-credits`, tracks every submission and download in
     `champa_ledger.jsonl`, and harvests completed `.mp4` clips named `<id>.mp4`.

Usage:
  # Check live Champa account & composer status:
  python3 scripts/champa/champa_fire.py --status

  # Dry-run: verify settings & cost against BL 192-shot educational CSV:
  python3 scripts/champa/champa_fire.py --allow-credits --max-credits 1350 --dry-run

  # Rolling queue (recommended): keep up to 6 concurrent renders active, harvesting <id>.mp4 as each finishes:
  python3 scripts/champa/champa_fire.py --allow-credits --max-credits 1350 --max-slots 6 --rolling-queue

  # Harvest completed videos from Champa history:
  python3 scripts/champa/champa_fire.py --harvest
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from queue_guard import QueueGuard, Refused, is_free_label  # noqa: E402

DEFAULT_PROMPTS_CSV = (
    THIS_DIR.parent.parent
    / "docs/reports/ph-a2c13fe6-bl-basket-series/bl_broll_prompts_65s.csv"
)
DEFAULT_OUT_DIR = Path("/Users/gob/MoonieXHQ/Assets/BlackLiquidity/broll-incoming")


def real_click_xy(page, x: float, y: float, pause: float = 0.4) -> None:
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.up()
    time.sleep(pause)


def reset_scroll_top(page) -> None:
    page.evaluate(
        """() => {
      window.scrollTo(0, 0);
      for (const el of document.querySelectorAll('*')) {
        if (el.scrollTop > 0) el.scrollTop = 0;
      }
    }"""
    )
    time.sleep(0.25)


def get_composer_bar_buttons(page) -> List[Dict[str, object]]:
    """Return buttons in the floating bottom composer bar (625 <= top <= 715, left > 240)."""
    return page.evaluate(
        """() => {
      const skipTxt = new Set(['แก้คำสั่ง', 'สร้างใหม่', 'More info']);
      const skipAria = new Set(['เพิ่มเติม', 'Play', 'Remove image']);
      return [...document.querySelectorAll('button')].map(b => {
        const r = b.getBoundingClientRect();
        return {
          txt: (b.innerText || '').trim().replace(/\\s+/g, ' '),
          aria: b.getAttribute('aria-label') || '',
          x: r.x + r.width / 2,
          y: r.y + r.height / 2,
          top: Math.round(r.y),
          left: Math.round(r.x),
        };
      }).filter(b => b.top >= 625 && b.top <= 715 && b.left > 240 && !skipTxt.has(b.txt) && !skipAria.has(b.aria));
    }"""
    )


def select_dropdown_option(page, trigger_btn: Dict[str, object], target_text: str) -> bool:
    """Click a composer bar dropdown pill, scroll the matching option into view, and click it."""
    real_click_xy(page, float(trigger_btn["x"]), float(trigger_btn["y"]), pause=0.45)
    pt = page.evaluate(
        """(target) => {
      const tLow = target.toLowerCase();
      const candidates = [...document.querySelectorAll('button')].filter(b => {
        const r = b.getBoundingClientRect();
        const txt = (b.innerText || '').trim().replace(/\\s+/g, ' ');
        if (!txt || r.y < 100 || (r.y >= 625 && r.y <= 715)) return false;
        return txt.toLowerCase().includes(tLow);
      });
      if (!candidates.length) return null;
      candidates.sort((a, b) => (a.innerText || '').trim().length - (b.innerText || '').trim().length);
      candidates[0].scrollIntoView({block: 'center'});
      return true;
    }""",
        target_text,
    )
    if not pt:
        page.keyboard.press("Escape")
        time.sleep(0.2)
        return False
    time.sleep(0.25)
    coords = page.evaluate(
        """(target) => {
      const tLow = target.toLowerCase();
      const candidates = [...document.querySelectorAll('button')].filter(b => {
        const r = b.getBoundingClientRect();
        const txt = (b.innerText || '').trim().replace(/\\s+/g, ' ');
        if (!txt || r.y < 100 || (r.y >= 625 && r.y <= 715)) return false;
        return txt.toLowerCase().includes(tLow);
      });
      if (!candidates.length) return null;
      candidates.sort((a, b) => (a.innerText || '').trim().length - (b.innerText || '').trim().length);
      const r = candidates[0].getBoundingClientRect();
      return {x: r.x + r.width / 2, y: r.y + r.height / 2, txt: (candidates[0].innerText || '').trim()};
    }""",
        target_text,
    )
    if coords:
        real_click_xy(page, float(coords["x"]), float(coords["y"]), pause=0.45)
        return True
    page.keyboard.press("Escape")
    return False


def apply_settings(
    page,
    model: Optional[str],
    ratio: Optional[str],
    duration: Optional[str],
    resolution: Optional[str],
    tier: Optional[str] = "Lite",
    mode: Optional[str] = "Element",
    ref_images: Optional[List[str]] = None,
) -> None:
    """Apply mode (Element/Frame), reference images, model, ratio, duration, resolution, and tier."""
    page.keyboard.press("Escape")
    time.sleep(0.2)

    # 0. Mode tab (Frame / เฟรมแรกและเฟรมสุดท้าย / Element at y ~ 510)
    if mode:
        mode_pt = page.evaluate(
            """(targetMode) => {
          for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText || '').trim();
            const r = b.getBoundingClientRect();
            if (t.toLowerCase() === targetMode.toLowerCase() && r.y >= 485 && r.y <= 545) {
              return {x: r.x + r.width / 2, y: r.y + r.height / 2};
            }
          }
          return null;
        }""",
            mode,
        )
        if mode_pt:
            real_click_xy(page, float(mode_pt["x"]), float(mode_pt["y"]), pause=0.35)

    if model:
        bar = get_composer_bar_buttons(page)
        if bar and model.lower() not in str(bar[0]["txt"]).lower():
            select_dropdown_option(page, bar[0], model)

    if ratio:
        bar = get_composer_bar_buttons(page)
        r_btns = [b for b in bar if ":" in str(b["txt"])]
        if r_btns and str(r_btns[0]["txt"]) != ratio:
            select_dropdown_option(page, r_btns[0], ratio)

    if duration:
        bar = get_composer_bar_buttons(page)
        d_btns = [b for b in bar if re.match(r"^\d+s$", str(b["txt"]), re.I)]
        if d_btns and str(d_btns[0]["txt"]).lower() != duration.lower():
            select_dropdown_option(page, d_btns[0], duration)

    if resolution:
        bar = get_composer_bar_buttons(page)
        res_btns = [b for b in bar if re.match(r"^(720p|1080p|4k)$", str(b["txt"]), re.I)]
        if res_btns and str(res_btns[0]["txt"]).lower() != resolution.lower():
            select_dropdown_option(page, res_btns[0], resolution)

    if tier:
        bar = get_composer_bar_buttons(page)
        t_btns = [b for b in bar if str(b["txt"]).lower() == tier.lower()]
        if t_btns:
            real_click_xy(page, float(t_btns[0]["x"]), float(t_btns[0]["y"]), pause=0.3)

    # 6. Upload reference image(s) via the paperclip button if ref_images provided and not yet attached
    if ref_images:
        valid_files = [str(Path(p).expanduser()) for p in ref_images if p and Path(p).expanduser().exists()]
        if valid_files:
            has_thumb = page.evaluate(
                """() => {
              for (const img of document.querySelectorAll('img')) {
                const r = img.getBoundingClientRect();
                if (r.y >= 540 && r.y <= 665 && r.x >= 240 && r.width >= 24 && r.height >= 24) {
                  return true;
                }
              }
              return false;
            }"""
            )
            if not has_thumb:
                bar = get_composer_bar_buttons(page)
                # Paperclip button is the first icon-only button (txt == '') in composer bar
                icon_btns = [b for b in bar if not str(b["txt"]).strip()]
                if icon_btns:
                    clip_btn = icon_btns[0]
                    try:
                        with page.expect_file_chooser(timeout=5000) as fc_info:
                            real_click_xy(page, float(clip_btn["x"]), float(clip_btn["y"]), pause=0.3)
                        fc = fc_info.value
                        if fc.is_multiple():
                            fc.set_files(valid_files[:2])
                        else:
                            fc.set_files(valid_files[0])
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"[champa_fire] warning: ref image upload error: {e}", file=sys.stderr)


def parse_balance_int(bal_str: Optional[str]) -> int:
    if not bal_str:
        return 0
    digits = re.sub(r"[^\d]", "", bal_str)
    return int(digits) if digits else 0


def parse_submit_cost(label: str) -> Optional[int]:
    if is_free_label(label):
        return 0
    m = re.search(r"สร้าง\s*(\d+)", label)
    if m:
        return int(m.group(1))
    return None


def live_active_renders(page) -> int:
    """Count how many cards on Champa are currently rendering or queued."""
    return int(
        page.evaluate(
            """() => {
      const seen = new Set();
      for (const el of document.querySelectorAll('div')) {
        const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
        if ((t.includes('กำลังสร้างสรรค์') || t.includes('อยู่ในคิว')) && t.includes('More info') && t.length < 900) {
          seen.add(t.slice(0, 220));
        }
      }
      return seen.size;
    }"""
        )
    )


def inspect_champa_status(page) -> Dict[str, object]:
    """Read live balance, Unlimited switch state, composer bar state, and active renders."""
    bar = get_composer_bar_buttons(page)
    info = page.evaluate(
        """() => {
      const balBtn = document.querySelector('button[aria-label="จำปาและการใช้งาน"]');
      const balance = balBtn ? (balBtn.innerText || '').trim() : null;
      const unlimSw = document.querySelector('[role="switch"][aria-label="Unlimited"], button[aria-label="Unlimited"]');
      const unlimitedSwitchPresent = !!unlimSw;
      const unlimitedChecked = unlimSw ? unlimSw.getAttribute('aria-checked') === 'true' : false;
      const banner = [...document.querySelectorAll('div, p')].map(el => (el.innerText || '').trim().replace(/\\s+/g, ' '))
        .find(t => t.includes('ไม่อยู่ใน Unlimited แล้ว') && t.length < 220) || null;
      return {
        url: location.href,
        balance_champa: balance,
        unlimited_switch_present: unlimitedSwitchPresent,
        unlimited_checked: unlimitedChecked,
        policy_banner: banner,
      };
    }"""
    )
    info["active_renders_on_page"] = live_active_renders(page)
    info["composer_bar"] = [b["txt"] for b in bar if b["txt"]]
    submit_btns = [
        b["txt"]
        for b in bar
        if str(b["aria"]) == "สร้าง"
        or "ส่งเข้าคิว" in str(b["txt"])
        or str(b["txt"]).startswith("สร้าง")
    ]
    info["submit_buttons"] = submit_btns
    return info


def load_prompts(
    path: Path,
    ep_filter: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return rows
    first_line = text.splitlines()[0]
    if "," in first_line and ("prompt" in first_line.lower() or "id" in first_line.lower()):
        reader = csv.DictReader(text.splitlines())
        for i, r in enumerate(reader, 1):
            pid = (r.get("id") or f"shot_{i:02d}").strip()
            p = (r.get("prompt") or "").strip()
            ep = (r.get("ep") or "").strip()
            if not p:
                continue
            if ep_filter and ep and ep.upper() not in ep_filter:
                continue
            rows.append(
                {
                    "id": pid,
                    "ep": ep,
                    "beat": (r.get("beat") or "").strip(),
                    "duration": (r.get("duration") or "").strip(),
                    "ratio": (r.get("ratio") or "").strip(),
                    "resolution": (r.get("resolution") or "").strip(),
                    "model": (r.get("model") or "").strip(),
                    "mode": (r.get("mode") or "Element").strip(),
                    "ref_images": (r.get("ref_images") or "").strip(),
                    "prompt": p,
                }
            )
    else:
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append({"id": f"shot_{i:02d}", "prompt": line})
    if limit and limit > 0:
        rows = rows[:limit]
    return rows


def connect_champa(cdp_url: str):
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    contexts = browser.contexts
    if not contexts:
        raise RuntimeError(f"No browser context on {cdp_url}. Run: relay-home.mjs launch champa")
    ctx = contexts[0]
    page = None
    for p in ctx.pages:
        if "champa.io" in (p.url or ""):
            page = p
            break
    if page is None:
        page = ctx.new_page()
        page.goto("https://champa.io/", wait_until="domcontentloaded", timeout=30000)
    elif page.url.rstrip("/") != "https://champa.io":
        page.goto("https://champa.io/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2.0)
    reset_scroll_top(page)
    return pw, browser, ctx, page


def verify_and_get_submit_button(
    page,
    guard: QueueGuard,
    allow_credits: bool,
    credits_spent_so_far: int,
    max_credits: int,
) -> tuple[Dict[str, object], str, int]:
    """Return (button_dict, label, cost_in_credits) or raise Refused."""
    bar = get_composer_bar_buttons(page)
    sub_btns = [
        b
        for b in bar
        if str(b["aria"]) == "สร้าง"
        or "ส่งเข้าคิว" in str(b["txt"])
        or str(b["txt"]).startswith("สร้าง")
    ]
    if not sub_btns:
        raise Refused(f"No submit button found in composer bar: {bar}")
    btn = sub_btns[-1]
    label = str(btn["txt"])
    cost = parse_submit_cost(label)
    if cost is None:
        raise Refused(f"Cannot parse cost from submit button label: {label!r}")

    if not allow_credits:
        if cost != 0 or not is_free_label(label):
            st = inspect_champa_status(page)
            raise Refused(
                f"Zero-credit guard active (--allow-credits not set) and submit button is {label!r} "
                f"(unlimited_switch_present={st.get('unlimited_switch_present')}, balance={st.get('balance_champa')})."
            )
        guard.check(label)
        return btn, label, 0

    if credits_spent_so_far + cost > max_credits:
        raise Refused(
            f"Credit cap reached: spent {credits_spent_so_far} + next {cost} > max_credits {max_credits}"
        )
    st = inspect_champa_status(page)
    live_bal = parse_balance_int(str(st.get("balance_champa") or "0"))
    if live_bal < cost:
        raise Refused(f"Insufficient Champa balance: {live_bal} < {cost}")
    return btn, label, cost


def harvest_completed(
    page,
    ctx,
    out_dir: Path,
    jobs: Optional[List[Dict[str, str]]] = None,
    guard: Optional[QueueGuard] = None,
    prompt_filter: Optional[str] = None,
    harvest_unmatched: bool = False,
) -> List[Path]:
    """Scroll through Champa history cards, click Play on matched cards, and save `<id>.mp4`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    seen_urls = set()

    prompt_map: List[tuple[str, str]] = []
    if jobs:
        for j in jobs:
            norm = re.sub(r"\s+", " ", j["prompt"].strip()).lower()
            if "is in the scene:" in norm:
                idx_s = norm.index("is in the scene:") + len("is in the scene:")
                body_key = norm[idx_s : idx_s + 85].strip()
            else:
                body_key = norm[65:155] if len(norm) > 100 else norm[:80]
            prompt_map.append((j["id"], body_key))

    reset_scroll_top(page)
    for _ in range(4):
        page.mouse.move(600, 350)
        page.mouse.wheel(0, 1200)
        time.sleep(0.35)
    reset_scroll_top(page)

    cards_meta = page.evaluate(
        """() => {
      const out = [];
      const seen = new Set();
      for (const el of document.querySelectorAll('div')) {
        const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
        if (t.includes('AI แก้คำสั่ง สร้างใหม่') && t.length < 900 && !t.includes('คืนจำปาแล้ว')) {
          const playBtn = el.querySelector('button[aria-label="Play"]');
          const img = el.querySelector('img');
          const key = (img && img.src) || t.slice(0, 220);
          if (playBtn && !seen.has(key)) {
            seen.add(key);
            out.push({txt: t, key});
          }
        }
      }
      return out;
    }"""
    )

    for idx, card in enumerate(cards_meta, 1):
        txt = card["txt"]
        if prompt_filter and prompt_filter.lower() not in txt.lower():
            continue
        norm_txt = re.sub(r"\s+", " ", txt).lower()
        matched_id = None
        for cid, body_key in prompt_map:
            if body_key and body_key in norm_txt:
                matched_id = cid
                break

        if not matched_id and not harvest_unmatched and not prompt_filter:
            continue

        if matched_id:
            existing_named = out_dir / f"{matched_id}.mp4"
            if existing_named.exists() and existing_named.stat().st_size > 50_000:
                saved.append(existing_named)
                if guard and matched_id not in guard.done_ids():
                    guard.record_done(matched_id, existing_named)
                continue

        clicked_js = page.evaluate(
            """(keyTxt) => {
          for (const el of document.querySelectorAll('div')) {
            const t = (el.innerText || '').trim().replace(/\\s+/g, ' ');
            if (t === keyTxt) {
              const playBtn = el.querySelector('button[aria-label="Play"]');
              if (playBtn) {
                playBtn.scrollIntoView({block: 'center'});
                playBtn.click();
                return true;
              }
            }
          }
          return false;
        }""",
            txt,
        )
        if clicked_js:
            time.sleep(1.8)

        vids = page.evaluate(
            """() => [...document.querySelectorAll('video')]
              .map(v => v.src || v.currentSrc || (v.querySelector('source') && v.querySelector('source').src) || '')
              .filter(Boolean)"""
        )
        for u in vids:
            if u in seen_urls or ".mp4" not in u:
                continue
            seen_urls.add(u)
            if matched_id:
                dest = out_dir / f"{matched_id}.mp4"
            else:
                h = hashlib.sha1(u.split("?")[0].encode()).hexdigest()[:10]
                slug = re.sub(r"[^a-z0-9]+", "_", txt[:45].lower()).strip("_")
                dest = out_dir / f"champa_{idx:02d}_{slug}_{h}.mp4"
            if dest.exists() and dest.stat().st_size > 50_000:
                saved.append(dest)
                continue
            resp = ctx.request.get(u, timeout=60000)
            if resp.ok:
                body = resp.body()
                dest.write_bytes(body)
                print(f"[harvest] saved: {dest.name} ({len(body):,} bytes) <- {txt[:80]}", flush=True)
                saved.append(dest)
                if matched_id and guard:
                    guard.record_done(matched_id, dest)
            else:
                print(f"[harvest] HTTP {resp.status} for {u[:80]}", file=sys.stderr, flush=True)

    reset_scroll_top(page)
    return saved


def write_progress(
    out_dir: Path,
    total_jobs: int,
    submitted_count: int,
    done_count: int,
    credits_spent: int,
    balance_str: Optional[str],
    active_renders: int,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    prog = {
        "updated_at": datetime.now().astimezone().isoformat(),
        "total_jobs": total_jobs,
        "submitted_count": submitted_count,
        "harvested_count": done_count,
        "active_renders_on_page": active_renders,
        "credits_spent_this_run": credits_spent,
        "balance_champa": balance_str,
    }
    (out_dir / "champa_progress.json").write_text(
        json.dumps(prog, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def submit_one_job(
    page,
    j: Dict[str, str],
    args,
    default_model: str,
    default_ratio: str,
    default_dur: str,
    default_res: str,
    guard: QueueGuard,
    credits_spent: int,
) -> int:
    row_model = args.model or j.get("model") or default_model
    row_ratio = args.ratio or j.get("ratio") or default_ratio
    row_dur = args.duration or j.get("duration") or default_dur
    row_res = args.resolution or j.get("resolution") or default_res
    row_mode = j.get("mode") or "Element"
    raw_refs = j.get("ref_images") or ""
    ref_list = [x.strip() for x in raw_refs.split(";") if x.strip()]

    for attempt in range(8):
        # Wait if there is already an active render and max_slots == 1
        while live_active_renders(page) >= max(args.max_slots, 1):
            time.sleep(10.0)

        st_before = inspect_champa_status(page)
        bal_before = parse_balance_int(str(st_before.get("balance_champa") or "0"))

        apply_settings(page, row_model, row_ratio, row_dur, row_res, tier=args.tier, mode=row_mode, ref_images=ref_list)

        box = page.locator("textarea, [contenteditable='true']").first
        box.click()
        box.fill(j["prompt"])
        time.sleep(0.45)

        sub_btn, lbl, cost = verify_and_get_submit_button(
            page,
            guard,
            allow_credits=args.allow_credits,
            credits_spent_so_far=credits_spent,
            max_credits=args.max_credits,
        )
        real_click_xy(page, float(sub_btn["x"]), float(sub_btn["y"]), pause=1.5)

        # Poll up to 10s for submission to register (Uploading 2 ref PNGs takes ~4-6s before balance deducts)
        for _ in range(10):
            time.sleep(1.0)
            st_after = inspect_champa_status(page)
            bal_after = parse_balance_int(str(st_after.get("balance_champa") or "0"))
            active_after = int(st_after.get("active_renders_on_page") or 0)
            if bal_after < bal_before or active_after > 0:
                guard.record_submit(j["id"], lbl)
                return cost
        print(f"[submit_one_job] attempt {attempt+1}: click did not deduct balance after 10s ({bal_before}->{bal_after}), waiting 8s and retrying…", flush=True)
        time.sleep(8.0)

    raise Refused(f"Failed to submit {j['id']} after 8 attempts")


def main() -> int:
    ap = argparse.ArgumentParser(description="Champa.io B-roll batch runner & rolling queue harvester")
    ap.add_argument("--cdp", default="http://127.0.0.1:9280", help="CDP endpoint for Champa browser home")
    ap.add_argument("--model", default=None, help="Override model name (e.g. 'Google Veo 3.1', 'Grok Imagine')")
    ap.add_argument("--ratio", default=None, help="Override aspect ratio (9:16, 16:9, 1:1)")
    ap.add_argument("--duration", default=None, help="Override clip duration (6s, 8s, 10s)")
    ap.add_argument("--resolution", default=None, help="Override resolution (720p, 1080p)")
    ap.add_argument("--tier", default="Lite", help="Tier pill for Veo 3.1 (Lite, Fast, Quality)")
    ap.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS_CSV, help="CSV or newline prompts file")
    ap.add_argument("--ep", default=None, help="Comma-separated episode filter (e.g. EP1,EP2,EP3)")
    ap.add_argument("--limit", type=int, default=None, help="Max number of prompts to process")
    ap.add_argument("--max-slots", type=int, default=1, help="Max concurrent active renders on Champa")
    ap.add_argument("--allow-credits", action="store_true", help="Allow spending existing Champa account credits")
    ap.add_argument("--max-credits", type=int, default=1350, help="Max Champa credits to spend")
    ap.add_argument("--status", action="store_true", help="Print live Champa balance & composer status and exit")
    ap.add_argument("--dry-run", action="store_true", help="Verify settings & cost without submitting")
    ap.add_argument("--fire", action="store_true", help="Submit pending prompts in one pass")
    ap.add_argument("--rolling-queue", action="store_true", help="Keep max-slots active renders & harvest continuously until all done")
    ap.add_argument("--harvest", action="store_true", help="Download completed videos from Champa history")
    ap.add_argument("--harvest-unmatched", action="store_true", help="Also download completed cards not in CSV")
    ap.add_argument("--harvest-filter", default=None, help="Substring filter on prompt text when harvesting")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    if not (args.status or args.dry_run or args.fire or args.rolling_queue or args.harvest):
        ap.error("Pass one of --status, --dry-run, --fire, --rolling-queue, or --harvest")

    pw, browser, ctx, page = connect_champa(args.cdp)
    try:
        status_info = inspect_champa_status(page)
        print("[champa_fire] Live status:", json.dumps(status_info, ensure_ascii=False, indent=2), flush=True)
        if args.status:
            return 0

        ep_filter = [x.strip().upper() for x in args.ep.split(",") if x.strip()] if args.ep else None
        all_jobs = load_prompts(args.prompts, ep_filter=None, limit=None) if args.prompts and args.prompts.exists() else []
        jobs = load_prompts(args.prompts, ep_filter=ep_filter, limit=args.limit) if args.prompts and args.prompts.exists() else []

        ledger_path = args.out / "champa_ledger.jsonl"
        guard = QueueGuard(max_in_flight=min(max(args.max_slots, 1), 8), ledger=ledger_path)

        # Ensure any already-downloaded <id>.mp4 files in args.out are recorded as submitted+done
        for j in all_jobs:
            f_mp4 = args.out / f"{j['id']}.mp4"
            if f_mp4.exists() and f_mp4.stat().st_size > 50_000:
                if j["id"] not in guard.submitted_ids():
                    guard.record_submit(j["id"], "already_on_disk")
                if j["id"] not in guard.done_ids():
                    guard.record_done(j["id"], f_mp4)

        if args.harvest and not (args.dry_run or args.fire or args.rolling_queue):
            saved = harvest_completed(
                page,
                ctx,
                args.out,
                jobs=all_jobs,
                guard=guard,
                prompt_filter=args.harvest_filter,
                harvest_unmatched=args.harvest_unmatched,
            )
            print(f"[champa_fire] Harvest complete: {len(saved)} file(s) in {args.out}", flush=True)
            return 0

        if not jobs:
            raise SystemExit(f"No prompts matched in {args.prompts} (ep={ep_filter})")

        first = jobs[0]
        target_model = args.model or first.get("model") or "Google Veo 3.1"
        target_ratio = args.ratio or first.get("ratio") or "9:16"
        target_duration = args.duration or first.get("duration") or "8s"
        target_res = args.resolution or first.get("resolution") or "720p"

        apply_settings(page, target_model, target_ratio, target_duration, target_res, tier=args.tier)

        btn, submit_label, unit_cost = verify_and_get_submit_button(
            page,
            guard,
            allow_credits=args.allow_credits,
            credits_spent_so_far=0,
            max_credits=args.max_credits,
        )
        already_submitted = guard.submitted_ids()
        pending_jobs = [j for j in jobs if j["id"] not in already_submitted]
        est_total_cost = len(pending_jobs) * unit_cost
        print(
            f"[champa_fire] Preflight OK · model={target_model!r} ratio={target_ratio} "
            f"duration={target_duration} res={target_res} tier={args.tier} · submit={submit_label!r} "
            f"(unit_cost={unit_cost} จำปา) · pending={len(pending_jobs)}/{len(jobs)} shots "
            f"(est_cost={est_total_cost} จำปา, cap={args.max_credits})",
            flush=True,
        )

        if args.dry_run and not (args.fire or args.rolling_queue):
            for j in pending_jobs[:20]:
                print(
                    f"  [dry-run] {j['id']} ({j.get('ep','')}/{j.get('beat','')}) "
                    f"[{j.get('model') or target_model} {j.get('ratio') or target_ratio} "
                    f"{j.get('duration') or target_duration} {j.get('resolution') or target_res} "
                    f"cost={unit_cost}]: {j['prompt'][:80]}…"
                )
            if len(pending_jobs) > 20:
                print(f"  ... and {len(pending_jobs) - 20} more shots.")
            print(f"[champa_fire] Dry-run complete ({len(pending_jobs)} pending shots verified, 0 credits spent).", flush=True)
            return 0

        credits_spent = 0

        if args.rolling_queue:
            queue_idx = 0
            target_id_set = {j["id"] for j in jobs}
            while True:
                # 1. Harvest any finished clips first
                harvest_completed(page, ctx, args.out, jobs=all_jobs, guard=guard)
                done_now = len(guard.done_ids() & target_id_set)
                sub_now = len(guard.submitted_ids() & target_id_set)
                active_on_page = live_active_renders(page)
                st = inspect_champa_status(page)
                bal_str = str(st.get("balance_champa") or "")
                bal_int = parse_balance_int(bal_str)

                write_progress(
                    args.out,
                    total_jobs=len(jobs),
                    submitted_count=sub_now,
                    done_count=done_now,
                    credits_spent=credits_spent,
                    balance_str=bal_str,
                    active_renders=active_on_page,
                )

                # 2. Fill empty slots up to args.max_slots
                while (
                    queue_idx < len(pending_jobs)
                    and active_on_page < args.max_slots
                    and bal_int >= unit_cost
                    and credits_spent + unit_cost <= args.max_credits
                ):
                    j = pending_jobs[queue_idx]
                    cost = submit_one_job(
                        page,
                        j,
                        args,
                        target_model,
                        target_ratio,
                        target_duration,
                        target_res,
                        guard,
                        credits_spent,
                    )
                    credits_spent += cost
                    queue_idx += 1
                    sub_now = len(guard.submitted_ids() & target_id_set)
                    st = inspect_champa_status(page)
                    bal_str = str(st.get("balance_champa") or "")
                    bal_int = parse_balance_int(bal_str)
                    active_on_page = int(st.get("active_renders_on_page") or 0)
                    print(
                        f"[rolling] SUBMITTED [{sub_now}/{len(jobs)}] {j['id']} "
                        f"({j.get('ep','')}/{j.get('beat','')}) · cost={cost} "
                        f"(spent={credits_spent}, balance={bal_str}, active={active_on_page}/{args.max_slots}, "
                        f"harvested={done_now})",
                        flush=True,
                    )
                    write_progress(
                        args.out,
                        total_jobs=len(jobs),
                        submitted_count=sub_now,
                        done_count=done_now,
                        credits_spent=credits_spent,
                        balance_str=bal_str,
                        active_renders=active_on_page,
                    )
                    time.sleep(1.5)

                # Check exit condition: all submitted jobs done and no more pending jobs (or balance exhausted)
                done_now = len(guard.done_ids() & target_id_set)
                sub_now = len(guard.submitted_ids() & target_id_set)
                active_on_page = live_active_renders(page)
                no_more_can_submit = (
                    queue_idx >= len(pending_jobs)
                    or bal_int < unit_cost
                    or credits_spent + unit_cost > args.max_credits
                )
                if no_more_can_submit and (done_now >= sub_now or active_on_page == 0):
                    # One final harvest pass
                    harvest_completed(page, ctx, args.out, jobs=all_jobs, guard=guard)
                    done_now = len(guard.done_ids() & target_id_set)
                    write_progress(
                        args.out,
                        total_jobs=len(jobs),
                        submitted_count=sub_now,
                        done_count=done_now,
                        credits_spent=credits_spent,
                        balance_str=bal_str,
                        active_renders=0,
                    )
                    print(
                        f"[rolling] COMPLETE · submitted={sub_now}/{len(jobs)} · harvested={done_now} "
                        f"· credits_spent={credits_spent} · remaining_balance={bal_str}",
                        flush=True,
                    )
                    break

                print(
                    f"[rolling] status: submitted={sub_now}/{len(jobs)} · harvested={done_now}/{sub_now} "
                    f"· active_on_page={active_on_page}/{args.max_slots} · balance={bal_str} · sleeping 18s…",
                    flush=True,
                )
                time.sleep(18)
            return 0

        if args.fire:
            for idx, j in enumerate(pending_jobs, 1):
                cost = submit_one_job(
                    page,
                    j,
                    args,
                    target_model,
                    target_ratio,
                    target_duration,
                    target_res,
                    guard,
                    credits_spent,
                )
                credits_spent += cost
                st_after = inspect_champa_status(page)
                print(
                    f"[champa_fire] [{idx}/{len(pending_jobs)}] SUBMITTED {j['id']} "
                    f"({j.get('ep','')}/{j.get('beat','')}) · cost={cost} (spent={credits_spent}, "
                    f"balance_now={st_after.get('balance_champa')})",
                    flush=True,
                )
                time.sleep(1.5)

        if args.harvest:
            saved = harvest_completed(
                page,
                ctx,
                args.out,
                jobs=all_jobs,
                guard=guard,
                prompt_filter=args.harvest_filter,
                harvest_unmatched=args.harvest_unmatched,
            )
            print(f"[champa_fire] Harvested {len(saved)} file(s) -> {args.out}", flush=True)
        return 0
    except Refused as e:
        print(
            f"[champa_fire] BLOCKED BY GUARD: {e}",
            file=sys.stderr,
            flush=True,
        )
        return 2
    finally:
        pw.stop()


if __name__ == "__main__":
    sys.exit(main())
