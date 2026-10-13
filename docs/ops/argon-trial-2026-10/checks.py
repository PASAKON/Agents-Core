"""Mechanical checks the CTO runs on both outputs (no model): translation layout and the batch plan."""
import json
import re
from collections import Counter

THAI = re.compile(r"[฀-๿]")
FENCE = re.compile(r"^\s*(```|~~~)")


def frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            return text[: end + 5]
    return ""


def md_check(old: str, new: str, frontmatter_frozen: bool = False) -> dict:
    """Layout checks for an in-place translation of one Markdown file."""
    ol, nl = old.split("\n"), new.split("\n")
    r = {"lines_old": len(ol), "lines_new": len(nl), "line_count_same": len(ol) == len(nl),
         "thai_chars_old": len(THAI.findall(old)), "thai_chars_new": len(THAI.findall(new))}
    if frontmatter_frozen:
        r["frontmatter_identical"] = frontmatter(old) == frontmatter(new)
    if len(ol) == len(nl):
        nonthai = [i for i, line in enumerate(ol) if not THAI.search(line)]
        changed = [i + 1 for i in nonthai if ol[i] != nl[i]]
        r["non_thai_lines"] = len(nonthai)
        r["non_thai_lines_changed"] = changed[:30]
        struct = []
        for i, (a, b) in enumerate(zip(ol, nl)):
            sa = (a.lstrip()[:1] in "#-*|>" and a.lstrip()[:1], a.count("|"), a.count("`"), bool(FENCE.match(a)),
                  len(a) - len(a.lstrip()), a.strip() == "")
            sb = (b.lstrip()[:1] in "#-*|>" and b.lstrip()[:1], b.count("|"), b.count("`"), bool(FENCE.match(b)),
                  len(b) - len(b.lstrip()), b.strip() == "")
            if sa != sb:
                struct.append(i + 1)
        r["structure_diff_lines"] = struct[:30]
        r["structure_diff_count"] = len(struct)
    r["thai_lines_left"] = [f"{i + 1}: {line.strip()[:110]}" for i, line in enumerate(nl) if THAI.search(line)][:60]
    return r


def batch_check(rows_jsonl: str, batches_md: str) -> dict:
    rows = [json.loads(x) for x in rows_jsonl.splitlines() if x.strip()]
    scope = {r["path"]: r for r in rows if r["repo"] == "Agents-Core" and ("doc" in r["kinds"] or "comment" in r["kinds"])}
    mentions = Counter()
    for p in scope:
        mentions[p] = len(re.findall(r"(?<![\w./-])" + re.escape(p) + r"(?![\w/-])", batches_md))
    missing = sorted(p for p, n in mentions.items() if n == 0)
    multi = sorted(p for p, n in mentions.items() if n > 1)
    # batch sizes: split on headings, count in-scope paths per section
    sections = re.split(r"\n(?=#{2,4} )", batches_md)
    sizes = []
    for s in sections:
        head = s.split("\n", 1)[0][:80]
        n = sum(1 for p in scope if re.search(r"(?<![\w./-])" + re.escape(p) + r"(?![\w/-])", s))
        if n:
            sizes.append((head, n))
    return {"in_scope_files": len(scope), "in_scope_translate_chars": sum(r["translate"] for r in scope.values()),
            "missing": len(missing), "missing_sample": missing[:15], "listed_more_than_once": len(multi),
            "multi_sample": multi[:15], "sections_with_files": len(sizes),
            "sections_over_20_files": [s for s in sizes if s[1] > 20][:10],
            "largest_sections": sorted(sizes, key=lambda s: -s[1])[:5]}
