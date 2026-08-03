"""Wiki content-split migrator (ADR 0013 §"Rollout" Phase 4).

Moves the 51 (+1) pages listed in config/wiki-split-manifest.yaml out of
MoonieX-Wikis into Agents-Wikis / LungNote-Wikis, and rewrites every
relative link / Obsidian `[[wikilink]]` that crosses the new repo boundary
into the two-part form ADR 0013 §"Cross-wiki link format" specifies:

    [Session discipline](https://github.com/PASAKON/Agents-Wikis/blob/main/playbooks/session-discipline.md) (`org:playbooks/session-discipline.md`)

Usage:
    python scripts/wiki_split.py --plan          # default: print plan, change nothing
    python scripts/wiki_split.py --apply         # perform the move
    python scripts/wiki_split.py --verify        # scan for dangling links, exit 1 if any

--plan is read-only: it shares the exact same scan_wiki() pass --verify
uses and never calls a write/git-mutating function. --apply is resumable —
see `_dirty_reason()` and `cmd_apply()` docstrings for exactly what that
means for the dirty-tree refusal and the already-moved-is-a-no-op guarantee.

Roots for the `org` / `mooniex` namespaces come from config/wikis.yaml,
never hardcoded here (ADR 0013's own multi-root registry). LungNote's path
is NOT in that registry (it isn't a namespace the wiki tools serve) — it
lives in config/wiki-split-manifest.yaml's `destinations` section instead,
per the task brief.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parent.parent
WIKIS_CONFIG = ROOT / "config" / "wikis.yaml"
MANIFEST_PATH = ROOT / "config" / "wiki-split-manifest.yaml"

# GitHub URL bases for the two namespaces registered in config/wikis.yaml.
# These are literal per ADR 0013 §"Cross-wiki link format" — not paths, so
# not subject to the "roots come from config/wikis.yaml" rule (that rule is
# about where the repos live on THIS disk, not the public GitHub URL used
# in a human-facing link).
REPO_URL_BASES = {
    "org": "https://github.com/PASAKON/Agents-Wikis/blob/main/",
    "mooniex": "https://github.com/PASAKON/MoonieX-Wikis/blob/main/",
}


class WikiSplitError(Exception):
    pass


# --------------------------------------------------------------------------
# Loading config/wikis.yaml + config/wiki-split-manifest.yaml
# --------------------------------------------------------------------------

def load_registry(wikis_config: Path = WIKIS_CONFIG) -> dict[str, Path]:
    """ns -> resolved root Path, from config/wikis.yaml's `wikis:` list."""
    reg = yaml.safe_load(wikis_config.read_text(encoding="utf-8"))
    return {w["ns"]: Path(w["path"]).resolve() for w in reg["wikis"]}


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict:
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))


def repo_roots(registry: dict[str, Path], manifest: dict) -> dict[str, Path]:
    """Every namespace this run touches -> resolved Path. Registered wiki
    namespaces (org, mooniex) come from `registry`; any `to:` namespace in
    the manifest that ISN'T registered (lungnote) comes from
    manifest['destinations'] instead."""
    out = dict(registry)
    for ns, dest in manifest.get("destinations", {}).items():
        out[ns] = Path(dest["path"]).resolve()
    return out


def moves_index(manifest: dict) -> dict[tuple[str, str], str]:
    """(from_ns, rel_path) -> to_ns, for every entry in manifest['moves']."""
    return {(m["from"], m["path"]): m["to"] for m in manifest.get("moves", [])}


def dest_ns_of(ns: str, rel_path: str, idx: dict[tuple[str, str], str]) -> str:
    """Final namespace `rel_path` (currently living in `ns`) lands in after
    --apply. Anything not in the moves index — including everything in
    manifest['out_of_scope'] — simply stays in its current namespace."""
    return idx.get((ns, rel_path), ns)


def url_base_for(ns: str, manifest: dict) -> str:
    if ns in REPO_URL_BASES:
        return REPO_URL_BASES[ns]
    dest = manifest.get("destinations", {}).get(ns)
    if dest and "github_url_base" in dest:
        return dest["github_url_base"]
    raise WikiSplitError(f"no GitHub URL base configured for namespace {ns!r}")


def link_ns_for(ns: str, manifest: dict) -> str | None:
    """The backticked ns: prefix a crossing link into `ns` should carry, or
    None if that namespace isn't served by the wiki tools (LungNote)."""
    dest = manifest.get("destinations", {}).get(ns)
    if dest is not None and "namespace" in dest:
        return dest["namespace"]
    return ns


# --------------------------------------------------------------------------
# Link scanning: fenced code blocks and inline code spans are never touched
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for a line that is a fence delimiter or inside a fenced block —
    those lines are never scanned for links (real example: CONTRIBUTING.md
    has a shell snippet containing literal `](` that is not a markdown
    link)."""
    mask = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            mask.append(True)
            in_fence = not in_fence
        else:
            mask.append(in_fence)
    return mask


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    return [m.span() for m in _INLINE_CODE_RE.finditer(line)]


def _in_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def _resolve_relative(file_rel_dir: str, target: str) -> str:
    """Resolve `target` (possibly containing `../`) against the directory
    containing the link, purely lexically (no filesystem access), returning
    a root-relative POSIX path. `../IRON-RULES.md` from `playbooks/foo.md`
    -> `IRON-RULES.md`."""
    base = PurePosixPath(file_rel_dir) if file_rel_dir else PurePosixPath(".")
    combined = base / target
    parts: list[str] = []
    for part in combined.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part in (".", ""):
            continue
        else:
            parts.append(part)
    return "/".join(parts)


def _find_by_stem(root: Path, stem: str) -> str | None:
    """Vault-wide lookup for a bare `[[pagename]]` wikilink (no slash) —
    Obsidian's "unique note name" resolution. None if zero or >1 matches
    (ambiguous is treated the same as not-found: report dangling, don't
    guess)."""
    matches = sorted(
        p for p in root.rglob(f"{stem}.md") if ".git" not in p.parts
    )
    if len(matches) == 1:
        return matches[0].relative_to(root).as_posix()
    return None


@dataclass
class Dangling:
    file: str  # "ns:relpath"
    line: int
    target: str  # the raw, unresolved link text found in the file


@dataclass
class Crossing:
    file: str
    line: int
    old: str
    new: str


def _link_targets(line: str, file_rel_dir: str, root: Path):
    """Yield (kind, match, resolved_relpath_or_None, anchor, caption) for
    every markdown link / wikilink on `line` that denotes a same-repo .md
    page (external URLs, mailto:, same-page anchors, and non-.md targets
    are not yielded — they are never rewritten and never counted as
    dangling)."""
    code_spans = _inline_code_spans(line)
    matches: list[tuple[str, re.Match]] = []
    for m in _MD_LINK_RE.finditer(line):
        matches.append(("md", m))
    for m in _WIKILINK_RE.finditer(line):
        matches.append(("wiki", m))
    matches.sort(key=lambda t: t[1].start())

    for kind, m in matches:
        if _in_span(m.start(), code_spans):
            continue

        if kind == "md":
            caption, raw_target = m.group(1), m.group(2)
            path_part, _, anchor = raw_target.partition("#")
            if path_part == "" or path_part.startswith(("http://", "https://", "mailto:")):
                continue
            if not path_part.endswith(".md"):
                continue
            resolved = _resolve_relative(file_rel_dir, path_part)
        else:
            content = m.group(1)
            target_part, sep, label = content.partition("|")
            path_part, _, anchor = target_part.partition("#")
            caption = label if sep else path_part
            if "/" not in path_part:
                resolved = _find_by_stem(root, path_part)
            else:
                page = path_part if path_part.endswith(".md") else path_part + ".md"
                if page.startswith("../") or page.startswith("./"):
                    resolved = _resolve_relative(file_rel_dir, page)
                else:
                    resolved = _resolve_relative("", page)  # vault-root-relative

        yield kind, m, resolved, anchor, caption


def scan_file(
    text: str,
    ns: str,
    rel_path: str,
    root: Path,
    moves_idx: dict[tuple[str, str], str],
    manifest: dict,
    all_roots: dict[str, Path],
) -> tuple[str, list[Dangling], list[Crossing]]:
    """Pure — no filesystem writes. Returns (rewritten_text, dangling,
    crossing). rewritten_text == text unless at least one crossing link was
    found.

    `all_roots` (every registered + destination-only namespace -> Path) is
    needed for the existence check below: a link can legitimately resolve
    to a page that a PRIOR --apply run already relocated out of `root` into
    a different namespace's root. Checking only `root` made such links look
    dangling instead of already-crossed (blind spot flagged during ADR 0013
    phase 4)."""
    file_label = f"{ns}:{rel_path}"
    file_rel_dir = str(PurePosixPath(rel_path).parent)
    if file_rel_dir == ".":
        file_rel_dir = ""
    dest_ns_file = dest_ns_of(ns, rel_path, moves_idx)

    raw_lines = text.splitlines(keepends=True)
    fence_mask = _fence_mask([l.rstrip("\r\n") for l in raw_lines])

    out_lines: list[str] = []
    all_dangling: list[Dangling] = []
    all_crossing: list[Crossing] = []

    for i, raw_line in enumerate(raw_lines, start=1):
        if fence_mask[i - 1]:
            out_lines.append(raw_line)
            continue

        if raw_line.endswith("\r\n"):
            content, ending = raw_line[:-2], "\r\n"
        elif raw_line.endswith("\n"):
            content, ending = raw_line[:-1], "\n"
        else:
            content, ending = raw_line, ""

        pieces: list[str] = []
        cursor = 0
        for kind, m, resolved, anchor, caption in _link_targets(content, file_rel_dir, root):
            if resolved is None:
                all_dangling.append(Dangling(file_label, i, m.group(0)))
                continue

            target_dest_ns = dest_ns_of(ns, resolved, moves_idx)
            target_root = all_roots.get(target_dest_ns)
            exists = (
                (target_root is not None and (target_root / resolved).is_file())
                or (root / resolved).is_file()  # not yet moved — still at its current root
            )
            if not exists:
                all_dangling.append(Dangling(file_label, i, m.group(0)))
                continue

            if target_dest_ns == dest_ns_file:
                continue  # same side after the move — leave unchanged

            url = url_base_for(target_dest_ns, manifest) + resolved
            if anchor:
                url += f"#{anchor}"
            ns_prefix = link_ns_for(target_dest_ns, manifest)
            new_text = (
                f"[{caption}]({url}) (`{ns_prefix}:{resolved}`)"
                if ns_prefix
                else f"[{caption}]({url})"
            )
            pieces.append(content[cursor:m.start()])
            pieces.append(new_text)
            cursor = m.end()
            all_crossing.append(Crossing(file_label, i, m.group(0), new_text))

        pieces.append(content[cursor:])
        out_lines.append("".join(pieces) + ending)

    # Detection-only pass: a markdown/wiki link whose `[...]` or `(...)` got
    # split by a line break is invisible to the per-line scan above (it
    # can't match on either half alone) — undercounting the true dangling
    # total (blind spot flagged during ADR 0013 phase 4). Never rewritten —
    # only per-line output is trusted for writes — just surfaced so a human
    # can fix the two physical lines by hand.
    for i in range(len(raw_lines) - 1):
        if fence_mask[i] or fence_mask[i + 1]:
            continue
        line_a = raw_lines[i].rstrip("\r\n")
        line_b = raw_lines[i + 1].rstrip("\r\n")
        boundary = len(line_a) + 1
        joined = line_a + " " + line_b
        already_seen = {mm.group(0) for _, mm, *_ in _link_targets(line_a, file_rel_dir, root)}
        already_seen |= {mm.group(0) for _, mm, *_ in _link_targets(line_b, file_rel_dir, root)}
        for kind, m, resolved, anchor, caption in _link_targets(joined, file_rel_dir, root):
            if not (m.start() < boundary <= m.end()):
                continue  # doesn't actually straddle the break
            if m.group(0) in already_seen:
                continue
            all_dangling.append(Dangling(file_label, i + 1, f"[multi-line] {m.group(0)}"))

    return "".join(out_lines), all_dangling, all_crossing


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)


@dataclass
class ScanResult:
    dangling: list[Dangling]
    crossing: list[Crossing]
    rewrites: dict[tuple[str, str], str]  # (ns, rel_path) -> new_text (only entries that changed)


def scan_wiki(registry: dict[str, Path], manifest: dict, roots: dict[str, Path] | None = None) -> ScanResult:
    """Read-only pass over every .md file in every REGISTERED wiki root
    (org, mooniex — never lungnote, which isn't wiki-tools-served and has
    no content to scan pre-move). Used by both --plan and --verify, and as
    phase 1 of --apply. Never writes anything.

    `roots` (defaults to `registry` if omitted) is the FULL repo_roots dict
    including destination-only namespaces (e.g. lungnote) — needed so
    scan_file can correctly check existence of a link target that already
    lives in a destination namespace from a prior --apply run."""
    if roots is None:
        roots = registry
    moves_idx = moves_index(manifest)
    dest_only_ns = set(manifest.get("destinations", {}).keys())
    dangling: list[Dangling] = []
    crossing: list[Crossing] = []
    rewrites: dict[tuple[str, str], str] = {}

    for ns, root in registry.items():
        # Destination-only namespaces (lungnote) may now also be registered
        # in config/wikis.yaml for unrelated wiki_read/write CLI access —
        # that must not pull them into THIS migration tool's source-side
        # scan (never content to migrate FROM; scanning them here would
        # surface their own internal links, e.g. template placeholders, as
        # noise unrelated to this split).
        if ns in dest_only_ns:
            continue
        if not root.exists():
            continue
        for md_file in iter_markdown_files(root):
            rel_path = md_file.relative_to(root).as_posix()
            text = md_file.read_text(encoding="utf-8")
            new_text, file_dangling, file_crossing = scan_file(
                text, ns, rel_path, root, moves_idx, manifest, roots
            )
            dangling.extend(file_dangling)
            crossing.extend(file_crossing)
            if new_text != text:
                rewrites[(ns, rel_path)] = new_text

    return ScanResult(dangling=dangling, crossing=crossing, rewrites=rewrites)


# --------------------------------------------------------------------------
# git plumbing
# --------------------------------------------------------------------------

def _git(root: Path, args: list[str]) -> tuple[int, str]:
    r = subprocess.run(
        ["git", "-C", str(root)] + args, capture_output=True, text=True
    )
    return r.returncode, r.stdout + r.stderr


def _dirty_reason(root: Path) -> str | None:
    """None if `root`'s working tree is clean enough to --apply on top of;
    otherwise a description of what's dirty.

    Deliberately NOT a plain `git status --porcelain` non-empty check:
    --apply's own contract requires it to be safely re-runnable on top of a
    PRIOR --apply's own output (staged `git rm` / `git add`, left
    uncommitted on purpose — "leave both repos staged so the CTO reviews
    before committing"). A naive dirty check would see that staged state
    and permanently refuse to ever run again until the CTO commits, which
    contradicts "running it twice must not corrupt anything."

    So: refuse only on changes NOT already staged — unstaged modifications/
    deletions and untracked files (git status porcelain's working-tree
    column, i.e. character index 1, non-space; or a bare "??"). Fully
    staged changes (index differs from HEAD, working tree matches index)
    are treated as this tool's own resumable state, not "dirty".
    """
    rc, out = _git(root, ["status", "--porcelain"])
    if rc != 0:
        raise WikiSplitError(f"git status failed in {root}: {out.strip()}")
    bad_lines = [
        line for line in out.splitlines()
        if line and (line[:2] == "??" or (len(line) > 1 and line[1] != " "))
    ]
    return "\n".join(bad_lines) if bad_lines else None


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_plan(registry: dict[str, Path], manifest: dict, *, out=sys.stdout) -> int:
    moves = manifest.get("moves", [])
    out_of_scope = manifest.get("out_of_scope", [])

    print("=== Wiki split plan (--plan is read-only; nothing is written) ===\n", file=out)
    print(f"Moves ({len(moves)}):", file=out)
    for m in moves:
        print(f"  {m['path']:<55} {m['from']} -> {m['to']}", file=out)

    print(f"\nOut of scope — stays in place, links only ({len(out_of_scope)}):", file=out)
    for p in out_of_scope:
        print(f"  {p}", file=out)

    print("\nScanning for links...", file=out)
    result = scan_wiki(registry, manifest, repo_roots(registry, manifest))
    print(f"Crossing links found: {len(result.crossing)} (would be rewritten by --apply)", file=out)
    print(f"Dangling links found: {len(result.dangling)} (left untouched; run --verify for the full list)", file=out)

    if result.crossing:
        print("\nSample crossing rewrites (first 10):", file=out)
        for c in result.crossing[:10]:
            print(f"  {c.file}:{c.line}", file=out)
            print(f"    - {c.old}", file=out)
            print(f"    + {c.new}", file=out)

    print(
        "\nRun --apply to perform this move (refuses on a dirty tree). "
        "Run --verify after to confirm zero dangling links.",
        file=out,
    )
    return 0


def cmd_verify(registry: dict[str, Path], manifest: dict, *, out=sys.stdout) -> int:
    result = scan_wiki(registry, manifest, repo_roots(registry, manifest))
    for d in result.dangling:
        print(f"{d.file}:{d.line} -> {d.target}", file=out)
    print(f"\n{len(result.dangling)} dangling link(s)", file=out)
    return 1 if result.dangling else 0


def cmd_apply(registry: dict[str, Path], manifest: dict, *, out=sys.stdout) -> int:
    roots = repo_roots(registry, manifest)
    touched_ns = {m["from"] for m in manifest.get("moves", [])} | {
        m["to"] for m in manifest.get("moves", [])
    }

    dirty = {}
    for ns in sorted(touched_ns):
        root = roots.get(ns)
        if root is None or not root.exists():
            raise WikiSplitError(f"wiki namespace {ns!r} not available on disk")
        reason = _dirty_reason(root)
        if reason:
            dirty[ns] = reason
    if dirty:
        print("Refusing to apply — dirty working tree:", file=out)
        for ns, reason in dirty.items():
            print(f"\n[{ns}] {roots[ns]}", file=out)
            print(reason, file=out)
        return 1

    # Phase 1: scan the CURRENT (pre-move) layout — resolution must happen
    # against where files live NOW, not where they're about to land, or a
    # moved file's link to something that stays put would wrongly resolve
    # against its new root and get reported as dangling.
    result = scan_wiki(registry, manifest, roots)

    move_keys = {(m["from"], m["path"]) for m in manifest.get("moves", [])}

    # Phase 2: perform the moves, writing each moved file's REWRITTEN
    # content straight to its destination (never write the old location —
    # it's about to be git rm'd).
    moved: list[str] = []
    noop: list[str] = []
    for m in manifest.get("moves", []):
        from_ns, to_ns, rel = m["from"], m["to"], m["path"]
        src_root, dst_root = roots[from_ns], roots[to_ns]
        src_file, dst_file = src_root / rel, dst_root / rel

        if dst_file.exists() and not src_file.exists():
            noop.append(rel)  # already moved by a prior run
            continue
        if not src_file.exists():
            raise WikiSplitError(f"manifest entry missing on both sides: {rel}")

        content = result.rewrites.get((from_ns, rel), src_file.read_text(encoding="utf-8"))
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        dst_file.write_text(content, encoding="utf-8")

        rc, gout = _git(src_root, ["rm", "-q", "--", rel])
        if rc != 0:
            raise WikiSplitError(f"git rm failed for {rel} in {src_root}: {gout.strip()}")
        # LungNote isn't a git-tracked wiki-tools namespace concern here,
        # but it's still a git repo — stage the new file there too.
        rc, gout = _git(dst_root, ["add", "--", rel])
        if rc != 0:
            raise WikiSplitError(f"git add failed for {rel} in {dst_root}: {gout.strip()}")
        moved.append(rel)

    # Phase 3: write rewritten content for every STATIONARY file whose links
    # changed (out_of_scope pages + anything else not in the moves list).
    rewritten_stationary: list[str] = []
    for (ns, rel), new_text in result.rewrites.items():
        if (ns, rel) in move_keys:
            continue  # handled in phase 2
        root = roots[ns]
        (root / rel).write_text(new_text, encoding="utf-8")
        rc, gout = _git(root, ["add", "--", rel])
        if rc != 0:
            raise WikiSplitError(f"git add failed for {rel} in {root}: {gout.strip()}")
        rewritten_stationary.append(f"{ns}:{rel}")

    print(f"Moved: {len(moved)}", file=out)
    print(f"Already moved (no-op): {len(noop)}", file=out)
    print(f"Stationary files with rewritten links: {len(rewritten_stationary)}", file=out)
    print(f"Dangling links (left untouched): {len(result.dangling)}", file=out)
    print("\nBoth repos are staged, nothing committed. Review with `git status` / `git diff --cached`.", file=out)
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true", help="print plan, change nothing (default)")
    group.add_argument("--apply", action="store_true", help="perform the move")
    group.add_argument("--verify", action="store_true", help="scan for dangling links, exit 1 if any")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    registry = load_registry()
    manifest = load_manifest()

    if args.verify:
        return cmd_verify(registry, manifest)
    if args.apply:
        return cmd_apply(registry, manifest)
    return cmd_plan(registry, manifest)


if __name__ == "__main__":
    sys.exit(main())
