#!/usr/bin/env python3
"""Safely re-download already-verified Flow clips as free 1080p exports.

This is deliberately a retrieval-only companion to ``flow_shoot.py``.  It
never calls Submit, never edits the production ledger, writes to a separate
destination, and keeps a resumable manifest keyed by shot and Flow clip id.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import flow_ledger
from tools.flow_shoot import (
    DOWNLOAD_GAP_S,
    FlowBrowser,
    first_dialogue_line,
    normalize_prompt_whitespace,
    parse_only,
    probe_video_dimensions,
    sha256_file,
    verify_clip,
)


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "rows": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("rows"), dict):
        raise RuntimeError(f"unsupported manifest format: {path}")
    return data


def save_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass


def select_targets(sheet: Path, ledger: Path, only: str, max_clips: int) -> list[dict]:
    wanted = parse_only(only)
    if not wanted:
        raise RuntimeError("--only must select at least one shot")
    if len(wanted) > max_clips:
        raise RuntimeError(
            f"selection has {len(wanted)} clips; safety limit is {max_clips}")
    shots = {s["shot"]: s for s in flow_ledger.parse_sheet(sheet)}
    rows = flow_ledger.load_ledger(ledger)
    result = []
    for number in sorted(wanted):
        shot = shots.get(number)
        row = rows.get(number)
        if shot is None or row is None:
            raise RuntimeError(f"shot {number}: missing from sheet or ledger")
        if row["status"] != "verified":
            raise RuntimeError(
                f"shot {number}: source ledger is {row['status']!r}, not verified")
        source = Path(row["file"])
        if not source.is_file():
            raise RuntimeError(f"shot {number}: source file missing: {source}")
        dimensions = probe_video_dimensions(source)
        if dimensions != (720, 1280):
            raise RuntimeError(
                f"shot {number}: source is {dimensions[0]}x{dimensions[1]}, "
                "expected an old 720x1280 clip")
        result.append({"shot": shot, "ledger": row, "source": source})
    return result


def _matching_batches(browser: FlowBrowser, shot: dict):
    """Return current-page batches matching full prompt and sheet duration."""
    page = browser.page
    page.goto(browser._project_url, wait_until="domcontentloaded", timeout=60_000)
    browser.mute_all_media()
    search = page.locator('input[aria-label="ค้นหา"]').first
    search.wait_for(state="visible", timeout=30_000)
    dialogue = first_dialogue_line(shot["prompt"])
    if not dialogue:
        raise RuntimeError(f"shot {shot['shot']}: prompt has no dialogue key")
    search.fill(dialogue)
    page.get_by_text(dialogue, exact=False).first.wait_for(
        state="visible", timeout=15_000)

    expected = normalize_prompt_whitespace(shot["prompt"])
    batches = page.locator("div.batch-container")
    exact = []
    for i in range(batches.count()):
        batch = batches.nth(i)
        actual = normalize_prompt_whitespace(batch.inner_text())
        if expected in actual:
            exact.append(batch)
    # A prompt can legitimately have multiple historical generations.  The
    # production had several forced-4s proof runs of shot 35, for example,
    # while the real sheet shot is 6s.  Use the card metadata's duration as a
    # second independent key; never choose the first matching prompt.
    duration_re = re.compile(rf"(?:^|\s){shot['dur_s']}\s*วินาที(?:\s|$)")
    return [batch for batch in exact if duration_re.search(batch.inner_text())]


def _open_batch_card(browser: FlowBrowser, shot: dict, ordinal: int):
    matches = _matching_batches(browser, shot)
    if ordinal >= len(matches):
        raise RuntimeError(
            f"shot {shot['shot']}: exact prompt+duration match count is "
            f"{len(matches)}, cannot open candidate {ordinal}")
    cards = matches[ordinal].locator("flow-grid-tile-container")
    if cards.count() != 1:
        raise RuntimeError(
            f"shot {shot['shot']}: matched batch has {cards.count()} cards, want 1")
    return cards.first


def _editor_identity(page, shot_number: int) -> tuple[str, str]:
    page.wait_for_url(re.compile(r"/edit/[^/?#]+"), timeout=30_000)
    match = re.search(r"/edit/([^/?#]+)", page.url)
    if not match:
        raise RuntimeError(f"shot {shot_number}: editor URL has no clip id")
    return page.url, match.group(1)


def find_exact_editor(browser: FlowBrowser, shot: dict,
                      source: Path) -> tuple[str, str]:
    """Resolve a shot to its exact historical card.

    Full prompt + duration can still identify multiple generations. In that
    case fetch each candidate's original 720p CDN bytes and require exactly
    one SHA-256 match with the already-verified local source clip.
    """
    matches = _matching_batches(browser, shot)
    if not matches:
        raise RuntimeError(
            f"shot {shot['shot']}: exact prompt+duration match count is 0")
    if len(matches) == 1:
        card = matches[0].locator("flow-grid-tile-container")
        if card.count() != 1:
            raise RuntimeError(
                f"shot {shot['shot']}: matched batch has {card.count()} cards, want 1")
        card.first.click()
        return _editor_identity(browser.page, shot["shot"])

    source_sha = sha256_file(source)
    sha_matches: list[tuple[str, str]] = []
    prior_resolution = browser.download_resolution
    try:
        browser.download_resolution = "720p"
        for ordinal in range(len(matches)):
            card = _open_batch_card(browser, shot, ordinal)
            candidate = browser.download_card(card)
            editor = _editor_identity(browser.page, shot["shot"])
            if sha256_file(candidate) == source_sha:
                sha_matches.append(editor)
    finally:
        browser.download_resolution = prior_resolution
    if len(sha_matches) != 1:
        raise RuntimeError(
            f"shot {shot['shot']}: {len(matches)} prompt+duration candidates, "
            f"but {len(sha_matches)} match the verified source SHA-256")
    return sha_matches[0]


def valid_completed_entry(entry: dict) -> bool:
    if entry.get("status") != "verified":
        return False
    output = Path(entry.get("output_file", ""))
    if not output.is_file():
        return False
    try:
        return (probe_video_dimensions(output) == (1080, 1920)
                and sha256_file(output) == entry.get("output_sha256"))
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--only", required=True)
    ap.add_argument("--max-clips", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    sheet = Path(args.sheet)
    ledger = Path(args.ledger)
    dest = Path(args.dest)
    manifest_path = Path(args.manifest)
    targets = select_targets(sheet, ledger, args.only, args.max_clips)
    manifest = load_manifest(manifest_path)
    manifest.update({"sheet": str(sheet), "ledger": str(ledger), "dest": str(dest)})

    browser = FlowBrowser()
    browser.download_resolution = "1080p"
    # Structural retrieval-only guard: even an accidental future call fails.
    browser.submit = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("flow_reupscale is retrieval-only; Submit is forbidden"))
    try:
        browser.attach()
        browser.mute_all_media()
        used_ids = {
            str(n): row.get("flow_clip_id")
            for n, row in manifest["rows"].items()
            if row.get("flow_clip_id")
        }
        for target in targets:
            shot = target["shot"]
            number = shot["shot"]
            key = str(number)
            old = manifest["rows"].get(key, {})
            if valid_completed_entry(old):
                print(f"shot {number}: skip — manifest/file already verified")
                continue

            editor_url, clip_id = find_exact_editor(browser, shot, target["source"])
            collision = next(
                (other for other, used in used_ids.items()
                 if other != key and used == clip_id), None)
            if collision:
                raise RuntimeError(
                    f"shot {number}: Flow clip {clip_id} already belongs to shot {collision}")

            entry = {
                "status": "matched" if args.dry_run else "downloading",
                "prompt_sha": target["ledger"]["prompt_sha"],
                "source_file": str(target["source"]),
                "source_sha256": sha256_file(target["source"]),
                "source_resolution": "720x1280",
                "flow_clip_id": clip_id,
                "editor_url": editor_url,
                "expected_duration_s": shot["dur_s"],
            }
            manifest["rows"][key] = entry
            used_ids[key] = clip_id
            save_manifest(manifest_path, manifest)
            if args.dry_run:
                print(f"DRY-RUN shot {number}: exact prompt -> clip {clip_id}")
                continue

            browser.page.goto(
                editor_url, wait_until="domcontentloaded", timeout=60_000)
            downloaded = browser._download_1080p_from_editor()
            dest.mkdir(parents=True, exist_ok=True)
            output = dest / f"shot-{number}.mp4"
            if output.exists():
                raise RuntimeError(
                    f"shot {number}: destination already exists but is not manifest-verified: {output}")
            staged = dest / f".shot-{number}.upscale.tmp.mp4"
            shutil.copy2(downloaded, staged)
            ok, reason = verify_clip(
                staged, shot["dur_s"], expected_resolution="1080p")
            if not ok:
                entry.update({"status": "failed", "note": reason,
                              "staged_file": str(staged)})
                save_manifest(manifest_path, manifest)
                raise RuntimeError(f"shot {number}: verification failed: {reason}")
            new_sha = sha256_file(staged)
            duplicate = next(
                (other for other, row in manifest["rows"].items()
                 if other != key and row.get("status") == "verified"
                 and row.get("output_sha256") == new_sha), None)
            if duplicate:
                entry.update({"status": "failed",
                              "note": f"same output checksum as shot {duplicate}"})
                save_manifest(manifest_path, manifest)
                raise RuntimeError(
                    f"shot {number}: duplicate output checksum matches shot {duplicate}")
            os.replace(staged, output)
            entry.update({"status": "verified", "output_file": str(output),
                          "output_sha256": new_sha, "verify": reason})
            save_manifest(manifest_path, manifest)
            print(f"shot {number}: verified — {reason} clip={clip_id}")
            time.sleep(DOWNLOAD_GAP_S)
    finally:
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
