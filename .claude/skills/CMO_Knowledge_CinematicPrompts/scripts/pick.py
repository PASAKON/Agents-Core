#!/usr/bin/env python3
"""
scripts/pick.py — Cinematic prompt picker, finder, inspector, and linter.

Usage:
  pick.py list [--dir <path>]
  pick.py find --job broll|movie|shortfilm [--style <subcategory>] [--model <m>] [--aspect 9:16] [--max-seconds N] [--text <word>] [--dir <path>]
  pick.py show <id> [--dir <path>]
  pick.py lint [path] [--dir <path>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "references" / "prompts"
)

REQUIRED_FIELDS = [
    "id",
    "category",
    "subcategory",
    "title",
    "model",
    "aspect",
    "seconds",
    "camera",
    "light",
    "prompt",
    "negatives",
    "use_when",
    "source",
    "license",
]

BANNED_WORDS = [
    "blush",
    "blushing",
    "flushed",
    "red face",
    "red cheeks",
    "red ears",
    "rosy cheeks",
    "child",
    "minor",
    "teen",
    "schoolgirl",
]
BANNED_THAI = ["หน้าแดง", "หูแดง"]
BANNED_CHARS = ["«", "»", "—"]

BANNED_WORDS_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")\b",
    re.IGNORECASE,
)


def load_all_prompts(prompts_path):
    p = Path(prompts_path)
    entries = []
    if p.is_file():
        files = [p]
    elif p.is_dir():
        files = sorted(p.glob("*.json"))
    else:
        return []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    entries.extend(data)
                elif isinstance(data, dict):
                    entries.append(data)
        except Exception as e:
            print(f"Error reading {f}: {e}", file=sys.stderr)
    return entries


def cmd_list(args):
    prompts_dir = args.dir or DEFAULT_PROMPTS_DIR
    entries = load_all_prompts(prompts_dir)
    if not entries:
        print(f"No prompts found in {prompts_dir}")
        return 0

    cat_counts = {}
    subcat_counts = {}
    model_counts = {}
    for e in entries:
        cat = e.get("category", "unknown")
        subcat = e.get("subcategory", "unknown")
        model = e.get("model", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        subcat_counts[subcat] = subcat_counts.get(subcat, 0) + 1
        model_counts[model] = model_counts.get(model, 0) + 1

    print(f"Total entries: {len(entries)}\n")
    print("Category counts:")
    for k in sorted(cat_counts.keys()):
        print(f"  {k}: {cat_counts[k]}")
    print("\nSubcategory counts:")
    for k in sorted(subcat_counts.keys()):
        print(f"  {k}: {subcat_counts[k]}")
    print("\nModel counts:")
    for k in sorted(model_counts.keys()):
        print(f"  {k}: {model_counts[k]}")
    return 0


def cmd_find(args):
    prompts_dir = args.dir or DEFAULT_PROMPTS_DIR
    entries = load_all_prompts(prompts_dir)
    results = []

    for e in entries:
        if args.job and e.get("category") != args.job:
            continue
        if args.style and e.get("subcategory") != args.style:
            continue
        if args.model:
            entry_model = e.get("model", "")
            # model "any" in entry matches every --model,
            # and --model any matches all entries
            if args.model != "any" and entry_model != "any" and entry_model != args.model:
                continue
        if args.aspect and e.get("aspect") != args.aspect:
            continue
        if args.max_seconds is not None:
            sec = e.get("seconds")
            if sec is None or sec > args.max_seconds:
                continue
        if args.text:
            text_corpus = (
                f"{e.get('title', '')} {e.get('prompt', '')} "
                f"{e.get('subcategory', '')} {e.get('use_when', '')}"
            ).lower()
            if args.text.lower() not in text_corpus:
                continue
        results.append(e)

    for e in results:
        eid = e.get("id", "")
        title = e.get("title", "")
        model = e.get("model", "")
        aspect = e.get("aspect", "")
        seconds = e.get("seconds", "")
        print(f"{eid} | {title} | {model} | {aspect} | {seconds}s")
    return 0


def cmd_show(args):
    prompts_dir = args.dir or DEFAULT_PROMPTS_DIR
    entries = load_all_prompts(prompts_dir)
    target = None
    for e in entries:
        if e.get("id") == args.id:
            target = e
            break

    if not target:
        print(f"Error: Prompt ID '{args.id}' not found.", file=sys.stderr)
        return 1

    prompt = target.get("prompt", "")
    print(prompt)
    print()
    negs = target.get("negatives", [])
    if isinstance(negs, list):
        neg_str = ", ".join(negs)
    else:
        neg_str = str(negs)
    print(f"Negatives: {neg_str}")
    print(f"Use when: {target.get('use_when', '')}")
    print(f"Source: {target.get('source', '')}")
    print(f"License: {target.get('license', '')}")
    return 0


def check_banned_content(text):
    hits = []
    m = BANNED_WORDS_RE.findall(text)
    if m:
        hits.extend(m)
    for tw in BANNED_THAI:
        if tw in text:
            hits.append(tw)
    for ch in BANNED_CHARS:
        if ch in text:
            hits.append(ch)
    return hits


def lint_entry(e, seen_ids):
    errors = []
    eid = e.get("id")

    # 1. Required fields
    for field in REQUIRED_FIELDS:
        if field not in e:
            errors.append(f"missing required field '{field}'")
        elif e[field] is None or (isinstance(e[field], (str, list)) and len(e[field]) == 0):
            errors.append(f"empty required field '{field}'")

    # 2. Unique id
    if not eid:
        errors.append("entry has no 'id' or empty 'id'")
    else:
        if eid in seen_ids:
            errors.append(f"duplicate id: '{eid}'")
        seen_ids.add(eid)

    # 3. Seconds 4-15
    sec = e.get("seconds")
    if not isinstance(sec, int):
        errors.append(f"seconds must be integer, got {type(sec).__name__}: {sec!r}")
    elif sec < 4 or sec > 15:
        errors.append(f"seconds must be between 4 and 15, got {sec}")

    # 4. Aspect in first line of prompt
    prompt = e.get("prompt", "")
    aspect = e.get("aspect", "")
    first_line = prompt.split("\n", 1)[0] if prompt else ""
    if aspect and aspect not in first_line:
        errors.append(f"prompt first line does not contain aspect '{aspect}': {first_line!r}")

    # 5. Banned words and characters
    content_to_check = [
        ("prompt", prompt),
        ("title", e.get("title", "")),
        ("use_when", e.get("use_when", "")),
    ]
    negs = e.get("negatives", [])
    if isinstance(negs, list):
        content_to_check.append(("negatives", " ".join(negs)))

    for label, text in content_to_check:
        banned = check_banned_content(text)
        if banned:
            errors.append(f"banned words/chars in {label}: {sorted(set(banned))}")

    return errors


def cmd_lint(args):
    target_path = args.path or args.dir or DEFAULT_PROMPTS_DIR
    entries = load_all_prompts(target_path)
    if not entries:
        print(f"Lint error: No prompt entries found at {target_path}", file=sys.stderr)
        return 1

    seen_ids = set()
    all_errors = []

    for idx, e in enumerate(entries):
        eid = e.get("id", f"index-{idx}")
        errs = lint_entry(e, seen_ids)
        if errs:
            all_errors.append((eid, errs))

    if all_errors:
        print(f"Lint FAILED ({len(all_errors)} entry/entries with errors):", file=sys.stderr)
        for eid, errs in all_errors:
            print(f"  [{eid}]:", file=sys.stderr)
            for err in errs:
                print(f"    - {err}", file=sys.stderr)
        return 1

    print(f"Lint PASSED: {len(entries)} entries checked, 0 errors.")
    return 0


def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--dir", type=Path, default=None, help="Path to prompts directory")

    parser = argparse.ArgumentParser(description="Cinematic Prompt Library Picker & Linter", parents=[common_parser])
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="Print prompt counts by category/subcategory/model", parents=[common_parser])

    # find
    find_parser = subparsers.add_parser("find", help="Find matching prompts", parents=[common_parser])
    find_parser.add_argument("--job", choices=["broll", "movie", "shortfilm"], required=True, help="Job category")
    find_parser.add_argument("--style", help="Subcategory/style")
    find_parser.add_argument("--model", help="Model (seedance-2.5, wan-3.0, flow-omni-1.1, any)")
    find_parser.add_argument("--aspect", help="Aspect ratio (e.g. 9:16, 16:9, 1:1)")
    find_parser.add_argument("--max-seconds", type=int, help="Maximum clip duration in seconds")
    find_parser.add_argument("--text", help="Text search word")

    # show
    show_parser = subparsers.add_parser("show", help="Show full prompt details by ID", parents=[common_parser])
    show_parser.add_argument("id", help="Prompt ID to show")

    # lint
    lint_parser = subparsers.add_parser("lint", help="Lint all prompt entries", parents=[common_parser])
    lint_parser.add_argument("path", nargs="?", type=Path, default=None, help="Optional directory or file path to lint")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list":
        sys.exit(cmd_list(args))
    elif args.command == "find":
        sys.exit(cmd_find(args))
    elif args.command == "show":
        sys.exit(cmd_show(args))
    elif args.command == "lint":
        sys.exit(cmd_lint(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
