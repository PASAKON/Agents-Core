"""Thai-text inventory — where the org's Thai lives, what kind it is, and what loads every session.

No model is involved: every number comes from lexing files. CEO order 2026-10-14 (relayed by
SomPong): internal text (skills, code comments, docs, role files, CLAUDE.md) moves to English to
save tokens, and language-specific content stays in its own language. This tool is step 1 of that
order: it finds the Thai and sorts it so the always-loaded files come first.

## What it measures

For every tracked text file in each root (``git ls-files``, or a plain walk for the rsync
snapshots that have no ``.git``), it counts characters in the Thai block (U+0E00–U+0E7F) and
splits them into kinds:

    translate  doc · skill_body · always_loaded · comment        (internal text → English)
    keep       ceo_quote · trigger_phrase · quoted_phrase · title_name · user_facing
               source_material · runtime_string · data · test_fixture (stays Thai)

A quoted Thai span is a quote (kept): on a line that names the CEO it is ``ceo_quote``, inside a
SKILL.md ``description`` it is ``trigger_phrase`` (Thai input has to match it), and anywhere else
``quoted_phrase``. ``«…»`` is a page/film title. Code is lexed per language: comments and
docstrings are ``comment``, other string literals are ``runtime_string``. The kind split is a
heuristic, and the summary says so; the per-file translate/keep numbers say what to read, not what
to change.

## Load tiers (what a session pays for, every time)

    T0_session  injected into every C-level session: CLAUDE.md files, C-level role files,
                MEMORY.md, SKILL.md description lines
    T0_worker   injected into every worker: roles/_worker_*.md, worker role files, DEV-PROMPT*
    T1_start    read at start by rule: IRON-RULES.md, INDEX.md, company/vision.md
    T2_trigger  loaded when triggered: SKILL.md bodies, playbooks, memory files
    T3_demand   everything else

## Tokens

``est_tokens`` = Thai chars × 0.85 + other chars ÷ 4. This is an ESTIMATE: 0.85 tok/char is the
Thai rate measured on Haiku 5.5 on 2026-10-13 (memory reference_measure_tokens_free_claude_p_delta,
``chars/4`` under-counts Thai 3.4×), and ``chars/4`` is the usual rough English rate. Real counts
for the always-loaded set come from the ``claude -p`` delta method and are written in the report.

## Privacy

Agents-Core is a public repo. Per-file rows are written to ``--out`` only for repos listed in
``--public``; every other repo appears in the summary as totals by kind and tier. Use
``--detail-out`` to write the private rows somewhere that is not committed.

Usage::

    .venv/bin/python tools/thai_inventory.py --hq /opt/MoonieXHQ \\
        --out docs/ops/thai-inventory-2026-10-14 --detail-out state/thai-inventory
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import tokenize
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

THAI = re.compile(r"[฀-๿]")
THAI_TOK_PER_CHAR = 0.85  # measured, Haiku 5.5, 2026-10-13
OTHER_CHARS_PER_TOK = 4.0  # rough English rate (estimate)

TRANSLATE_KINDS = ("always_loaded", "skill_body", "doc", "comment")
KEEP_KINDS = ("ceo_quote", "trigger_phrase", "quoted_phrase", "title_name",
              "user_facing", "source_material", "runtime_string", "data", "test_fixture")
TIERS = ("T0_session", "T0_worker", "T1_start", "T2_trigger", "T3_demand")

C_LEVEL_ROLES = {"cto", "cmo", "cgo", "cfo", "coo", "cto-windows"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next", "__pycache__",
             ".pytest_cache", "coverage", ".turbo", "vendor"}
SKIP_SUFFIXES = {".lock", ".min.js", ".map", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp",
                 ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".pdf", ".zip", ".gz", ".ttf", ".otf",
                 ".woff", ".woff2", ".ico", ".db", ".sqlite", ".bin", ".pt", ".onnx", ".npy"}
MAX_BYTES = 5_000_000

CODE_PY = {".py"}
CODE_C = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".swift", ".go", ".rs", ".java", ".kt",
          ".c", ".h", ".cpp", ".css", ".scss"}
CODE_HASH = {".sh", ".bash", ".zsh", ".ps1", ".rb", ".toml", ".ini", ".cfg", ".conf"}
DATA_EXT = {".json", ".jsonl", ".yaml", ".yml", ".csv", ".tsv", ".sql", ".env", ".xml",
            ".patch", ".diff"}
MARKUP = {".md", ".mdx", ".txt", ".rst", ""}
HTML = {".html", ".htm", ".vue", ".svelte"}
SUBTITLE = {".srt", ".vtt", ".ass"}

TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|fixtures?|testdata|spec)(/|$)|(^|/)test_[^/]*$"
                       r"|\.(test|spec)\.[a-z]+$|_test\.[a-z]+$")
# Thai that is the product or the material, not internal text: captions, scripts, spoken lines,
# reply packs, posts, Thai-language pages, contracts for outside parties.
USER_FACING_PATH = re.compile(
    r"(^|/)(captions?|subtitles?|tts|voices?|personas?|prompts?|templates?|locales?|i18n|lang|"
    r"copy|replies|messages|reply-packs?|posts?|geo|youtube-scripts|docs/scripts|docs/promo|"
    r"output/content|scripts/(film|ep|lakorn)[^/]*)(/|$)"
    r"|persona|caption|reply[-_]voice|reply-packs?/|\.prompt\.|script[^/]*\.(md|txt)$|spoken[^/]*$|contract"
    r"|[-_]th\.(md|txt|html)$|(^|/)[^/]*-th/", re.I)
# Source material quoted for study: video transcripts, raw research text. Kept as it is.
SOURCE_PATH = re.compile(r"(^|/)(transcripts?|raw|sources?)(/|$)|(^|/)output/research/.+\.txt$",
                         re.I)
CEO_NEAR = re.compile(r"\bCEO\b|ซีอีโอ|\(CEO|CEO's|the CEO|ceo:", re.I)
# A quote may wrap onto the next line (markdown is hard-wrapped) but stays inside one paragraph
# and under 600 chars, so a stray inch mark cannot swallow a page.
QUOTE_SPAN = re.compile(r'“[^”]{0,600}?”|"[^"\n]{0,600}?(?:\n[^"\n]{0,600}?)?"|«[^»]{0,200}?»'
                        r'|„[^“]{0,600}?“|「[^」]{0,600}?」|‘[^’\n]{0,600}?’')

# Skill descriptions also list triggers in plain single quotes: 'ตรวจคลิป', 'audit the film'.
DESC_QUOTE = re.compile(QUOTE_SPAN.pattern + r"|'[^'\n]{1,80}'")


def thai(s: str) -> int:
    return len(THAI.findall(s))


# ── tiers ─────────────────────────────────────────────────────────────────────

def tier_of(repo: str, rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    parts = rel.split("/")
    if name == "CLAUDE.md" and len(parts) == 1:
        return "T0_session"
    if repo == "Agents-Memory" and rel == "MEMORY.md":
        return "T0_session"
    # Only Agents-Core roles/ is injected (scripts/cto-claude.sh, cxo-claude.sh: $ROOT/roles).
    if repo == "Agents-Core" and parts[0] == "roles" and len(parts) == 2 and name.endswith(".md"):
        return "T0_session" if name[:-3] in C_LEVEL_ROLES else "T0_worker"
    if repo == "Agents-Rules" and name.startswith("DEV-PROMPT"):
        return "T0_worker"
    if rel in ("IRON-RULES.md", "INDEX.md", "company/vision.md"):
        return "T1_start"
    if name == "SKILL.md" or "/playbooks/" in f"/{rel}" or repo == "Agents-Memory":
        return "T2_trigger"
    return "T3_demand"


# ── lexers: return list of (kind, text) segments ──────────────────────────────

def _split_quotes(text: str, line_kind: str, quote_kind_for_line,
                  pattern: re.Pattern = QUOTE_SPAN) -> list[tuple[str, str]]:
    """Split text into quoted spans (kept) and the rest (line_kind)."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            out.append((line_kind, text[pos:m.start()]))
        span = m.group(0)
        out.append(("title_name" if span.startswith("«") else quote_kind_for_line(text), span))
        pos = m.end()
    out.append((line_kind, text[pos:]))
    return out


def lex_markdown(text: str, body_kind: str) -> list[tuple[str, str]]:
    """Paragraph by paragraph, so a quote that wraps onto the next line is still one quote.

    A quoted span in a paragraph that names the CEO is ``ceo_quote``. A blockquote paragraph that
    follows a paragraph naming the CEO (``## Rule (CEO 2026-09-18)`` then ``> "…"``) is the CEO's
    words as a whole.
    """
    segs: list[tuple[str, str]] = []
    prev_ceo = False
    for para in re.split(r"\n[ \t]*\n", text):
        names_ceo = bool(CEO_NEAR.search(para))
        is_quote_block = para.lstrip().startswith(">")
        if is_quote_block and thai(para) and (prev_ceo or names_ceo):
            segs.append(("ceo_quote", para))
        else:
            kind_for = (lambda _p: "ceo_quote") if names_ceo else (lambda _p: "quoted_phrase")
            segs.extend(_split_quotes(para, body_kind, kind_for))
        prev_ceo = names_ceo or (prev_ceo and is_quote_block)
    return segs


def lex_skill(text: str) -> tuple[list[tuple[str, str]], str]:
    """SKILL.md: description lines are T0 (trigger phrases kept), the body is skill_body.

    Returns (segments, description_text). Segments tagged ``desc:`` belong to the description.
    """
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return lex_markdown(text, "skill_body"), ""
    fm, body = m.group(1), text[m.end():]
    desc = ""
    try:
        meta = yaml.safe_load(fm) or {}
        desc = str(meta.get("description") or "")
    except yaml.YAMLError:
        dm = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", fm, re.S | re.M)
        desc = dm.group(1) if dm else ""
    segs = [("desc:" + k, s) for k, s in _split_quotes(desc, "always_loaded",
                                                        lambda _l: "trigger_phrase", DESC_QUOTE)]
    segs += lex_markdown(body, "skill_body")
    return segs, desc


def lex_python(text: str) -> list[tuple[str, str]]:
    segs: list[tuple[str, str]] = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return lex_hash(text)
    prev = tokenize.NEWLINE
    for i, t in enumerate(toks):
        if t.type == tokenize.COMMENT:
            segs.append(("comment", t.string))
        elif t.type == tokenize.STRING or t.type == getattr(tokenize, "FSTRING_START", -1):
            nxt = toks[i + 1].type if i + 1 < len(toks) else tokenize.NEWLINE
            is_doc = (t.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.INDENT,
                      tokenize.DEDENT, tokenize.NL, tokenize.ENCODING)
                      and nxt in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER))
            segs.append(("comment" if is_doc else "runtime_string", t.string))
        elif t.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            segs.append(("runtime_string", t.string))
        if t.type not in (tokenize.COMMENT, tokenize.NL):
            prev = t.type
    return segs


def lex_clike(text: str) -> list[tuple[str, str]]:
    """// and /* */ comments vs '…' "…" `…` strings, for JS/TS/CSS/Swift and friends."""
    segs: list[tuple[str, str]] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            segs.append(("comment", text[i:j]))
            i = j
        elif two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            segs.append(("comment", text[i:j]))
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                elif c != "`" and text[j] == "\n":
                    break
                j += 1
            segs.append(("runtime_string", text[i:j + 1]))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in "'\"`/":
                j += 1
            if j == i:
                j = i + 1
            segs.append(("runtime_string", text[i:j]))  # bare Thai in code = JSX text etc.
            i = j
    return segs


def lex_hash(text: str) -> list[tuple[str, str]]:
    """# comments outside quotes (shell, toml, ini); everything else is a runtime string."""
    segs: list[tuple[str, str]] = []
    for line in text.splitlines():
        q = None
        cut = None
        for k, ch in enumerate(line):
            if q:
                if ch == q:
                    q = None
            elif ch in "'\"":
                q = ch
            elif ch == "#" and (k == 0 or line[k - 1] in " \t;"):
                cut = k
                break
        if cut is None:
            segs.append(("runtime_string", line))
        else:
            segs.append(("runtime_string", line[:cut]))
            segs.append(("comment", line[cut:]))
    return segs


def lex_html(text: str) -> list[tuple[str, str]]:
    segs: list[tuple[str, str]] = []
    pos = 0
    for m in re.finditer(r"<!--.*?-->", text, re.S):
        segs.append(("user_facing", text[pos:m.start()]))
        segs.append(("comment", m.group(0)))
        pos = m.end()
    segs.append(("user_facing", text[pos:]))
    return segs


# ── per file ──────────────────────────────────────────────────────────────────

@dataclass
class FileRow:
    repo: str
    path: str
    ext: str
    tier: str
    chars: int
    thai: int
    kinds: dict = field(default_factory=dict)
    desc_chars: int = 0
    desc_thai: int = 0

    @property
    def translate(self) -> int:
        return sum(v for k, v in self.kinds.items() if k in TRANSLATE_KINDS)

    @property
    def keep(self) -> int:
        return self.thai - self.translate

    @property
    def est_tokens(self) -> int:
        return round(self.thai * THAI_TOK_PER_CHAR + (self.chars - self.thai) / OTHER_CHARS_PER_TOK)

    def as_dict(self) -> dict:
        return {"repo": self.repo, "path": self.path, "ext": self.ext, "tier": self.tier,
                "chars": self.chars, "thai": self.thai, "translate": self.translate,
                "keep": self.keep, "est_tokens": self.est_tokens, "kinds": self.kinds,
                **({"desc_chars": self.desc_chars, "desc_thai": self.desc_thai}
                   if self.desc_chars else {})}


def _ext(rel: str) -> str:
    name = Path(rel).name
    return ".min.js" if name.endswith(".min.js") else Path(rel).suffix.lower()


def segments_for(rel: str, text: str, tier: str) -> list[tuple[str, str]]:
    """(kind, text) segments of one file. ``desc:`` prefixes mark SKILL.md description text."""
    name, ext = Path(rel).name, _ext(rel)
    if TEST_PATH.search(rel):
        return [("test_fixture", text)]
    if SOURCE_PATH.search(rel):
        return [("source_material", text)]
    if name == "SKILL.md":
        segs = lex_skill(text)[0]
    elif ext in SUBTITLE:
        return [("user_facing", text)]
    elif ext in DATA_EXT:
        return [("data", text)]
    elif ext in CODE_PY:
        segs = lex_python(text)
    elif ext in CODE_C:
        segs = lex_clike(text)
    elif ext in CODE_HASH:
        segs = lex_hash(text)
    elif ext in HTML:
        segs = lex_html(text)
    else:
        segs = lex_markdown(text, "always_loaded" if tier.startswith("T0") else "doc")
    # A path that is plainly user-facing (captions, prompts, personas, film scripts) keeps its
    # Thai prose and strings; its code comments are still internal text.
    if USER_FACING_PATH.search(rel):
        segs = [("user_facing" if k.split(":", 1)[-1] in
                 ("doc", "always_loaded", "skill_body", "runtime_string") else k, s)
                for k, s in segs]
    return segs


def classify(repo: str, rel: str, text: str) -> FileRow:
    tier = tier_of(repo, rel)
    row = FileRow(repo, rel, _ext(rel), tier, len(text), thai(text))
    if not row.thai:
        return row
    kinds: Counter = Counter()
    for k, seg in segments_for(rel, text, tier):
        t = thai(seg)
        if t:
            kinds[k.split(":", 1)[-1]] += t
    if Path(rel).name == "SKILL.md":
        desc = lex_skill(text)[1]
        row.desc_chars, row.desc_thai = len(desc), thai(desc)
    # Lexer rounding: attribute any leftover to the file's main kind so totals add up.
    gap = row.thai - sum(kinds.values())
    if gap:
        main = kinds.most_common(1)[0][0] if kinds else "doc"
        kinds[main] += gap
    row.kinds = dict(sorted(kinds.items(), key=lambda kv: -kv[1]))
    return row


# ── roots ─────────────────────────────────────────────────────────────────────

def list_files(root: Path) -> list[str]:
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True,
                             check=True).stdout.decode("utf-8", "replace")
        files = [f for f in out.split("\0") if f]
    else:
        files = []
        for p in root.rglob("*"):
            if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                files.append(str(p.relative_to(root)))
    keep = []
    for f in files:
        parts = f.split("/")
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        low = f.lower()
        if any(low.endswith(s) for s in SKIP_SUFFIXES):
            continue
        keep.append(f)
    return sorted(keep)


def read_text(path: Path) -> str | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:8192]:
        return None
    return raw.decode("utf-8", "replace")


def discover(hq: Path) -> list[tuple[str, Path]]:
    """(repo name, path) for every git repo under the HQ, plus the Rules/Wikis snapshots."""
    found: dict[Path, str] = {}
    if (hq / ".git").exists():  # the HQ map repo itself: CLAUDE.md, hq.yaml, MAP.md
        found[hq.resolve()] = repo_name(hq)
    for depth in ("*", "*/*", "*/*/*"):
        for p in hq.glob(depth):
            if p.name in SKIP_DIRS or "Archive" in p.parts or "External" in p.parts:
                continue
            if (p / ".git").exists() and p.resolve() != hq.resolve():
                found[p.resolve()] = repo_name(p)
    for snap in ("Agents/Rules", "Agents/Wikis"):
        p = hq / snap
        if p.is_dir():
            found[p.resolve()] = "Agents-" + snap.split("/")[1]
    return sorted(((n, p) for p, n in found.items()), key=lambda x: x[0])


def repo_name(p: Path) -> str:
    try:
        url = subprocess.run(["git", "-C", str(p), "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
        return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    except subprocess.CalledProcessError:
        return p.name


def published_paths(root: Path) -> set[str] | None:
    """Paths tracked on the checkout's upstream branch, or None when it has none.

    A public repo's per-file rows are limited to these, so a local commit that has not been
    pushed (Contabo's Agents-Core main is held, 2026-10-10) never has its file names published.
    """
    if not (root / ".git").exists():
        return None
    r = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", "@{u}"],
                       capture_output=True, text=True)
    return set(r.stdout.splitlines()) if r.returncode == 0 else None


def not_on_box(hq: Path, present: set[str]) -> list[dict]:
    """Repos the HQ map knows that have no checkout on this box."""
    mp = hq / "hq.yaml"
    if not mp.exists():
        return []
    rows = (yaml.safe_load(mp.read_text(encoding="utf-8")) or {}).get("folders") or []
    out = []
    for r in rows:
        repo = (r.get("repo") or "").split("/")[-1]
        if not repo or r.get("status") in ("retired",) or r.get("kind") in ("group", "archive"):
            continue
        if repo in present or (hq / r.get("path", "")).joinpath(".git").exists():
            continue
        out.append({"repo": repo, "path": r.get("path"), "owner": r.get("owner"),
                    "status": r.get("status", "active")})
    return out


# ── report ────────────────────────────────────────────────────────────────────

def summarize(rows: list[FileRow], repos: list[tuple[str, Path]], public: set[str],
              missing: list[dict], totals: dict) -> str:
    L: list[str] = []
    a = L.append
    a("# Thai-text inventory")
    a("")
    a("Generated by `tools/thai_inventory.py` (no model). Thai = characters U+0E00–U+0E7F.")
    a("**translate** = internal text that moves to English (docs, skill bodies, always-loaded "
      "prose, code comments). **keep** = CEO quotes, trigger phrases, other quoted phrases, "
      "«titles», user-facing text, runtime strings, data, test fixtures. The kind split is a "
      "lexer heuristic: it says what to read, not what to change; every diff is still read by a "
      "C-level. `est tok` = Thai × 0.85 + other ÷ 4 — an **estimate** (0.85 = Haiku 5.5 Thai rate "
      "measured 2026-10-13); measured counts for the always-loaded set are in the report.")
    a("")
    a("## By repo")
    a("")
    a("| repo | files | chars | Thai | Thai % | files with Thai | translate | keep | detail |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    by_repo: dict[str, list[FileRow]] = defaultdict(list)
    for r in rows:
        by_repo[r.repo].append(r)
    for name, _p in repos:
        t = totals.get(name, {"files": 0, "chars": 0, "thai": 0})
        rs = by_repo.get(name, [])
        tr = sum(r.translate for r in rs)
        kp = sum(r.keep for r in rs)
        pct = 100 * t["thai"] / t["chars"] if t["chars"] else 0
        a(f"| {name} | {t['files']} | {t['chars']:,} | {t['thai']:,} | {pct:.1f} % | {len(rs)} "
          f"| {tr:,} | {kp:,} | {'per file below' if name in public else 'totals only (private)'} |")
    a("")
    a("## By tier (what a session pays for)")
    a("")
    a("| tier | files with Thai | Thai | translate | keep | est tok of those files |")
    a("|---|---:|---:|---:|---:|---:|")
    for tier in TIERS:
        rs = [r for r in rows if r.tier == tier]
        a(f"| {tier} | {len(rs)} | {sum(r.thai for r in rs):,} | {sum(r.translate for r in rs):,} "
          f"| {sum(r.keep for r in rs):,} | {sum(r.est_tokens for r in rs):,} |")
    skills = [r for r in rows if r.path.endswith("SKILL.md")]
    if skills:
        dt = sum(r.desc_thai for r in skills)
        dtr = sum(r.kinds.get("always_loaded", 0) for r in skills)
        a("")
        a(f"SKILL.md description lines (T0, part of the T2 files above): {len(skills)} skills with "
          f"Thai anywhere; {dt:,} Thai chars sit in descriptions, of which {dtr:,} are outside "
          f"quotes (a read found these are trigger phrases written without quotes, proper names "
          f"and UI labels — see the report).")
    a("")
    a("## By kind")
    a("")
    a("| kind | class | Thai chars | files |")
    a("|---|---|---:|---:|")
    kc: Counter = Counter()
    kf: Counter = Counter()
    for r in rows:
        for k, v in r.kinds.items():
            kc[k] += v
            kf[k] += 1
    for k in TRANSLATE_KINDS + KEEP_KINDS:
        if kc.get(k):
            a(f"| {k} | {'translate' if k in TRANSLATE_KINDS else 'keep'} | {kc[k]:,} | {kf[k]} |")
    a("")
    a("## Always-loaded files with Thai (T0 + T1), all repos")
    a("")
    a("| repo | file | tier | chars | Thai | translate | keep | top kinds |")
    a("|---|---|---|---:|---:|---:|---:|---|")
    hot = sorted((r for r in rows if r.tier in ("T0_session", "T0_worker", "T1_start")),
                 key=lambda r: (TIERS.index(r.tier), -r.translate, -r.thai))
    for r in hot:
        kinds = ", ".join(f"{k} {v}" for k, v in list(r.kinds.items())[:3])
        path = r.path if r.repo in public or r.path in ("CLAUDE.md", "MEMORY.md") else "(private path)"
        a(f"| {r.repo} | {path} | {r.tier} | {r.chars:,} | {r.thai:,} | {r.translate:,} "
          f"| {r.keep:,} | {kinds} |")
    a("")
    a("## Top translate backlog, public repos (T2/T3, by Thai to translate)")
    a("")
    a("| repo | file | tier | Thai | translate | keep |")
    a("|---|---|---|---:|---:|---:|")
    back = sorted((r for r in rows if r.repo in public and r.tier in ("T2_trigger", "T3_demand")
                   and r.translate), key=lambda r: -r.translate)
    for r in back[:60]:
        a(f"| {r.repo} | {r.path} | {r.tier} | {r.thai:,} | {r.translate:,} | {r.keep:,} |")
    if len(back) > 60:
        a(f"| … | {len(back) - 60} more in rows.jsonl | | | {sum(r.translate for r in back[60:]):,} | |")
    a("")
    a("## Not on Contabo (out of scope from this box)")
    a("")
    if missing:
        a("| repo | HQ path | owner | status |")
        a("|---|---|---|---|")
        for m in missing:
            a(f"| {m['repo']} | {m['path']} | {m['owner']} | {m['status']} |")
    else:
        a("(hq.yaml not found or every mapped repo is present)")
    a("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--hq", default="/opt/MoonieXHQ", help="HQ root to discover repos under")
    ap.add_argument("--root", action="append", default=[],
                    help="scan only these roots (repeatable); default: discover under --hq")
    ap.add_argument("--public", default="Agents-Core,Agents-Rules,Chatudo-Webapp",
                    help="repos whose per-file rows may be published (comma list)")
    ap.add_argument("--out", help="dir for summary.md + public rows.jsonl")
    ap.add_argument("--detail-out", help="dir for private repos' rows (keep it uncommitted)")
    ap.add_argument("--explain", metavar="FILE",
                    help="print each Thai segment of one file with the kind it was given")
    ap.add_argument("--repo-name", default="", help="with --explain: repo name, for the tier")
    ap.add_argument("--rel", default="", help="with --explain: repo-relative path, for the tier")
    args = ap.parse_args(argv)

    if args.explain:
        p = Path(args.explain)
        text = p.read_text(encoding="utf-8")
        rel = args.rel or str(p)
        row = classify(args.repo_name, rel, text)
        print(json.dumps(row.as_dict(), ensure_ascii=False))
        for kind, seg in segments_for(rel, text, row.tier):
            if thai(seg):
                one = " ".join(seg.split())
                print(f"{kind:15s} {thai(seg):5d}  {one[:160]}")
        return 0
    if not args.out:
        ap.error("--out is required unless --explain is given")

    hq = Path(args.hq)
    repos = ([(repo_name(Path(r)) if (Path(r) / ".git").exists() else Path(r).name, Path(r))
              for r in args.root] if args.root else discover(hq))
    public = {s.strip() for s in args.public.split(",") if s.strip()}
    rows: list[FileRow] = []
    totals: dict[str, dict] = {}
    published: dict[str, set[str] | None] = {n: published_paths(r) for n, r in repos
                                              if n in public}
    for name, root in repos:
        t = {"files": 0, "chars": 0, "thai": 0}
        for rel in list_files(root):
            text = read_text(root / rel)
            if text is None:
                continue
            row = classify(name, rel, text)
            t["files"] += 1
            t["chars"] += row.chars
            t["thai"] += row.thai
            if row.thai:
                rows.append(row)
        totals[name] = t

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    missing = not_on_box(hq, {n for n, _ in repos}) if not args.root else []

    def is_published(r: FileRow) -> bool:
        paths = published.get(r.repo)
        return r.repo in public and (paths is None or r.path in paths)

    unpublished = [r for r in rows if r.repo in public and not is_published(r)]
    shown = [r for r in rows if r.repo not in public or is_published(r)]
    text = summarize(shown, repos, public, missing, totals)
    if unpublished:
        text += (f"\n{len(unpublished)} files with Thai in public repos exist only in local, "
                 f"unpushed commits ({sum(r.thai for r in unpublished):,} Thai chars); they are "
                 f"left out of the per-file tables above and of rows.jsonl (repo totals include "
                 f"them).\n")
    (out / "summary.md").write_text(text, encoding="utf-8")
    pub = sorted((r for r in rows if is_published(r)),
                 key=lambda r: (TIERS.index(r.tier), -r.translate, r.repo, r.path))
    with (out / "rows.jsonl").open("w", encoding="utf-8") as fh:
        for r in pub:
            fh.write(json.dumps(r.as_dict(), ensure_ascii=False) + "\n")
    if args.detail_out:
        d = Path(args.detail_out)
        d.mkdir(parents=True, exist_ok=True)
        priv = sorted((r for r in rows if r.repo not in public or not is_published(r)),
                      key=lambda r: (TIERS.index(r.tier), -r.translate, r.repo, r.path))
        with (d / "rows-private.jsonl").open("w", encoding="utf-8") as fh:
            for r in priv:
                fh.write(json.dumps(r.as_dict(), ensure_ascii=False) + "\n")
    print(f"{len(repos)} roots, {sum(t['files'] for t in totals.values())} text files, "
          f"{len(rows)} with Thai, {sum(r.thai for r in rows):,} Thai chars "
          f"({sum(r.translate for r in rows):,} translate / {sum(r.keep for r in rows):,} keep)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
