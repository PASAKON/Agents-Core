"""tools/machine_doctor.py — registry vs disk, per machine (ADR 0031, IRON §58,
docs/ops/briefs/machine-contract-phase1.md). Reuses the walk-and-fail idiom of
/opt/MoonieXHQ/scripts/hq.py `doctor`: load a manifest, walk the disk, print
one "  ✗ ..." line per disagreement, exit 1 if any. `hq.py` maps HQ project
folders; this maps OS / Claude-profile / toolkit paths — config/machine-
contract.yaml, CTO-maintained, never edited by this tool (§58 rule: proposals
go to state/machine-discovered-<machine>.yaml instead).

Verbs:
    python tools/machine_doctor.py --machine contabo snapshot
    python tools/machine_doctor.py --machine contabo check
    python tools/machine_doctor.py --machine contabo report
    python tools/machine_doctor.py --machine contabo --on-version-change

snapshot  every registry row for `--machine`, expanded from placeholders,
          with exists?/size -> state/machine-snapshot-<machine>.json.
check     exit 1 when (a) an IRREPLACEABLE row exists on disk with no
          `restore` line; (b) a registry row already carries `class:
          UNCLASSIFIED` (a human hasn't classified it yet — e.g. the seed
          row /root/restore); (c) a directory over `unknown_growth.min_mb`
          under $HOME, $CLAUDE_CONFIG_DIR, /opt or /var/lib/docker/volumes
          matches no row — printed DISCOVERED and appended (first sighting
          only) to state/machine-discovered-<machine>.yaml, never to the
          registry itself; (d) an already-logged discovered row whose
          `first_seen` is older than `unknown_growth.classify_within_days`
          — printed CANDIDATE. (b)/(d) are the only rules independent of
          current disk truth (an UNCLASSIFIED row, or a past-window log
          entry, stays reported until a human reclassifies it — IRON §58
          rule 2: "no agent deletes it without an explicit human go"); (a)
          and the live half of (c) are re-checked fresh every run, so a
          since-removed path stops being reported (nothing here ever
          deletes anything — only the reporting is live).
report    one line per class with its total GB (applicable rows only).

Placeholders in a row's `path`: $CLAUDE_CONFIG_DIR (env, default
~/.claude), $HOME (env), <hq> (from machines.<machine>.hq in the
registry). A Windows %VAR% placeholder makes the row inapplicable on a
non-Windows machine (skipped, not an error). Any other <...> token (e.g.
<task-id>) stands for "any value" and is treated as a glob `*`. A `{a,b}`
group anywhere in the path is a registry-native OR-list and is expanded
into one alternative per member (bash brace-expansion, not a real glob
feature) before each alternative is globbed independently; a row's
exists/bytes are the OR/SUM across its alternatives.

Machine detection (`--machine`, else auto): try the current hostname
against each machine's key (substring, case-insensitive) — works if a box
is ever literally hostnamed "contabo"/"mac"/"winbox" — else fall back to
this process's OS matched against the unique `machines.<m>.os` in the
registry (today's three machines each have a distinct OS, so this is
deterministic without needing a hostname literal in the registry, which
the brief's schema does not carry).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import platform
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

# The report uses ✗ / → glyphs; a Windows console (cp1252) raised UnicodeEncodeError on the first
# winbox `check` (2026-09-24, scheduled-task account passg). Force UTF-8 with replacement instead.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATE_DIR = ROOT / "state"
DEFAULT_REGISTRY_PATH = ROOT / "config" / "machine-contract.yaml"

_WINDOWS_PLACEHOLDER_RE = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%")
_ANGLE_PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
_OS_BY_PLATFORM_SYSTEM = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}


# --------------------------------------------------------------------- load

def load_registry(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_REGISTRY_PATH
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data or {}


def detect_machine(registry: dict, *, hostname: str | None = None) -> str:
    """`--machine`'s fallback when the flag is omitted — see module
    docstring. Raises SystemExit with the available keys when neither
    signal resolves to exactly one machine."""
    machines = registry.get("machines") or {}
    host = (hostname if hostname is not None else platform.node()) or ""
    for key in machines:
        if key and key.lower() in host.lower():
            return key
    current_os = _OS_BY_PLATFORM_SYSTEM.get(platform.system())
    matches = [k for k, v in machines.items() if (v or {}).get("os") == current_os]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(
        f"machine_doctor: cannot auto-detect the machine (hostname={host!r}, "
        f"platform={platform.system()}); pass --machine explicitly "
        f"(known machines: {', '.join(sorted(machines)) or 'none in registry'})"
    )


# ---------------------------------------------------------------- resolution

def build_context(registry: dict, machine: str, *, home: str | Path | None = None,
                   claude_config_dir: str | Path | None = None) -> dict:
    """The three named placeholders' values for `machine`, plus `_os` (used
    to decide whether a Windows %VAR% row applies here)."""
    minfo = (registry.get("machines") or {}).get(machine) or {}
    home_val = str(home) if home is not None else os.environ.get("HOME", str(Path.home()))
    ccd_val = (
        str(claude_config_dir) if claude_config_dir is not None
        else os.environ.get("CLAUDE_CONFIG_DIR", str(Path(home_val) / ".claude"))
    )
    return {
        "HOME": home_val,
        "CLAUDE_CONFIG_DIR": ccd_val,
        "hq": minfo.get("hq", ""),
        "_os": minfo.get("os", ""),
    }


def _substitute(raw: str, ctx: dict) -> str | None:
    """None means "not applicable on this machine" (a %VAR% Windows
    placeholder while ctx['_os'] != 'windows')."""
    if _WINDOWS_PLACEHOLDER_RE.search(raw) and ctx.get("_os") != "windows":
        return None
    out = raw.replace("$CLAUDE_CONFIG_DIR", str(ctx["CLAUDE_CONFIG_DIR"]))
    out = out.replace("$HOME", str(ctx["HOME"]))
    out = out.replace("<hq>", str(ctx["hq"]))
    if ctx.get("_os") == "windows":
        out = _expand_windows_vars(out, ctx.get("_env"))
    out = _ANGLE_PLACEHOLDER_RE.sub("*", out)  # <task-id> etc. -> wildcard
    return out


def _expand_windows_vars(s: str, env: dict | None = None) -> str:
    """%USERPROFILE% / %LOCALAPPDATA% / %APPDATA% ... -> their values, looked up
    case-insensitively in `env` (default os.environ). An unset name is left as
    written so the row simply never matches instead of matching everything.
    First winbox run (2026-09-24) proved the gap: the raw "%USERPROFILE%/cookierun-bot/**"
    was compared literally, so the bot's own clone was reported DISCOVERED."""
    src = env if env is not None else os.environ
    lookup = {k.upper(): v for k, v in src.items()}

    def _one(m: re.Match) -> str:
        return lookup.get(m.group(1).upper(), m.group(0))

    return re.sub(r"%([A-Za-z_][A-Za-z0-9_()]*)%", _one, s)


def _expand_braces(s: str) -> list[str]:
    """"a/{x,y}/b" -> ["a/x/b", "a/y/b"]; a no-op when there is no {...}
    group. Recurses so more than one group (not seen in the registry today)
    still expands correctly."""
    m = re.search(r"\{([^{}]*)\}", s)
    if not m:
        return [s]
    prefix, body, suffix = s[: m.start()], m.group(1), s[m.end():]
    out: list[str] = []
    for alt in body.split(","):
        out.extend(_expand_braces(prefix + alt + suffix))
    return out


_REPARSE_POINT = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT — junctions and symlinks alike on NTFS


def _is_link(p: Path) -> bool:
    """A symlink anywhere, or a junction / any other reparse point on Windows.
    Python < 3.12 reports a junction as neither symlink nor link, so
    os.walk(followlinks=False) walks straight into it: on the first winbox
    run (2026-09-24) `AppData\\Local\\Application Data` → `AppData\\Local` and
    `Local Settings` → `AppData\\Local` looped until the doctor measured
    98.7 GB for a 10 GB tree. Same guard as scripts/stream_backup_to_drive.py."""
    try:
        if p.is_symlink():
            return True
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT)


def _prune_links(dirpath: str, dirnames: list[str]) -> None:
    """Drop reparse-point children in place so os.walk never descends into them."""
    dirnames[:] = [d for d in dirnames if not _is_link(Path(dirpath) / d)]


def _path_bytes(p: Path) -> int:
    """Total file bytes under `p` (0 for a symlink/junction or a missing path).
    os.walk(followlinks=False) plus a reparse-point prune, matching
    workdir.py/hq.py's convention — never follows a link into a loop."""
    if _is_link(p):
        return 0
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    if not p.is_dir():
        return 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(p, followlinks=False):
        _prune_links(dirpath, dirnames)
        for name in filenames:
            fp = Path(dirpath) / name
            if fp.is_symlink():
                continue
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def _anchor_starstar(alt: str, hq: str) -> str:
    """A brace alternative that starts bare with "**/" (the registry's own
    venvs row has "**/node_modules") has no rooted anchor — resolving it
    against the process's cwd would be arbitrary and unbounded. Anchor it
    to <hq> instead: a real, bounded root matching this registry's scope."""
    if alt.startswith("**/") and hq:
        return f"{hq.rstrip('/')}/{alt}"
    return alt


def _glob_single_segments(head: str) -> list[Path]:
    """`head` has no "**" — only literal segments and single */?/[...]
    wildcards (e.g. "/root/.claude/projects/*/memory"). Resolved one
    directory level at a time with os.scandir, which is bounded and
    symlink-loop-safe by construction: it can never recurse past the
    number of segments actually written in the pattern."""
    parts = Path(head).parts
    if parts and parts[0] == "/":
        candidates, rest = [Path("/")], parts[1:]
    else:
        candidates, rest = [Path(".")], parts
    for seg in rest:
        if not any(ch in seg for ch in "*?["):
            candidates = [c / seg for c in candidates]
            continue
        nxt: list[Path] = []
        for c in candidates:
            if not c.is_dir() or c.is_symlink():
                continue
            try:
                with os.scandir(c) as it:
                    nxt.extend(Path(e.path) for e in it if fnmatch.fnmatch(e.name, seg))
            except OSError:
                pass
        candidates = nxt
    return candidates


def _starstar_anywhere(head: str) -> list[Path]:
    """`head` contains a "**" path segment that is not a trailing "/**"
    (handled separately) — e.g. "<hq>/**/node_modules". Only the bare
    "**/<name>" shape (anchored, nothing after <name>) is supported; any
    other shape is reported unresolved (empty list) rather than guessed at.
    os.walk(followlinks=False) — never follows a symlink into a loop, unlike
    glob.glob(pattern, recursive=True), which measured >20s hung (and did
    not return within 60s) on this box's own /opt/MoonieXHQ/Projects/**,
    stuck on a single venv's `lib64 -> lib` symlink. Prunes descent into
    each match, so a node_modules nested inside another is never re-summed
    on top of its parent's already-recursive total."""
    if "/**/" not in head:
        return []
    anchor_str, target_name = head.split("/**/", 1)
    if "/" in target_name or not anchor_str:
        return []  # more path after <name>, or no anchor: unsupported shape
    anchor = Path(anchor_str)
    if not anchor.is_dir() or anchor.is_symlink():
        return []
    matches: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(anchor, followlinks=False):
        _prune_links(dirpath, dirnames)
        found = [d for d in dirnames if d == target_name]
        matches.extend(Path(dirpath) / d for d in found)
        dirnames[:] = [d for d in dirnames if d != target_name]
    return matches


def _resolve_and_measure(pattern: str) -> tuple[bool, int]:
    """(exists, bytes) for one already-substituted, brace-free, anchored
    alternative (may still contain glob wildcards). Never uses glob.glob —
    see _starstar_anywhere for why."""
    if not any(ch in pattern for ch in "*?["):
        p = Path(pattern)
        return (p.exists(), _path_bytes(p) if p.exists() else 0)

    recurse_all = pattern.endswith("/**")
    head = pattern[: -len("/**")] if recurse_all else pattern

    dirs = _starstar_anywhere(head) if "**" in head else _glob_single_segments(head)

    exists = False
    total = 0
    for d in dirs:
        if d.is_symlink():
            continue
        if d.is_dir():
            exists = True
            if recurse_all:
                total += _path_bytes(d)
            # else: a bare directory match with no trailing /** contributes
            # existence only — matches the registry's own row shapes today
            # (every mid-path "*" row this tool sees ends in "/**").
        elif d.is_file():
            exists = True
            try:
                total += d.stat().st_size
            except OSError:
                pass
    return exists, total


def _row_applies(row: dict, machine: str) -> bool:
    return row.get("machine") in ("all", machine)


def resolve_rows(registry: dict, machine: str, ctx: dict) -> list[dict]:
    """One dict per registry row applicable to `machine` (row's own fields
    plus resolved/applicable/exists/bytes/alt_templates)."""
    out: list[dict] = []
    for row in registry.get("entries", []) or []:
        if not _row_applies(row, machine):
            continue
        raw = row.get("path", "")
        substituted = _substitute(raw, ctx)
        if substituted is None:
            out.append({**row, "resolved": raw, "applicable": False,
                        "exists": False, "bytes": 0, "alt_templates": []})
            continue
        alts = [_anchor_starstar(a, ctx["hq"]) for a in _expand_braces(substituted)]
        exists = False
        total = 0
        for alt in alts:
            e, b = _resolve_and_measure(alt)
            exists = exists or e
            total += b
        out.append({**row, "resolved": substituted, "applicable": True,
                    "exists": exists, "bytes": total, "alt_templates": alts})
    return out


def _segments(path_str: str) -> list[str]:
    # normcase: a no-op on POSIX; on Windows it lower-cases and unifies the
    # separators, so "C:/Users/passg/x" and "C:\\Users\\PASSG\\x" compare equal.
    return [os.path.normcase(seg) for seg in Path(path_str).parts if seg != "/"]


def _is_prefix(a: list[str], b: list[str]) -> bool:
    return len(a) <= len(b) and b[: len(a)] == a


def _covered(candidate: Path, row_templates: list[str]) -> bool:
    """True if `candidate` sits inside, or wholly contains, some row's
    (placeholder-substituted, brace-expanded, still-possibly-globby)
    template — a lexical path-segment containment test, not a real glob
    match. Either direction counts: a row nested under `candidate` means
    `candidate` is already explained by known rows; `candidate` nested
    under a row means it is that row's own territory."""
    cand_segs = _segments(str(candidate))
    for tmpl in row_templates:
        t_segs = _segments(tmpl)
        if _is_prefix(cand_segs, t_segs) or _is_prefix(t_segs, cand_segs):
            return True
    return False


def _read_claude_version(last_update_path: Path) -> str | None:
    try:
        data = json.loads(last_update_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("version_to") or data.get("version") or None


# ------------------------------------------------------------------ snapshot

def snapshot(machine: str, *, registry: dict | None = None,
             registry_path: str | Path | None = None,
             state_dir: str | Path | None = None,
             home: str | Path | None = None,
             claude_config_dir: str | Path | None = None) -> dict:
    registry = registry if registry is not None else load_registry(registry_path)
    ctx = build_context(registry, machine, home=home, claude_config_dir=claude_config_dir)
    rows = resolve_rows(registry, machine, ctx)
    claude_version = _read_claude_version(Path(ctx["CLAUDE_CONFIG_DIR"]) / ".last-update-result.json")

    data = {
        "machine": machine,
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "claude_version": claude_version,
        "entries": [
            {
                "path": r["path"],
                "resolved": r["resolved"],
                "class": r.get("class"),
                "applicable": r["applicable"],
                "exists": r["exists"],
                "bytes": r["bytes"],
            }
            for r in rows
        ],
    }
    sd = Path(state_dir) if state_dir else STATE_DIR
    sd.mkdir(parents=True, exist_ok=True)
    out_path = sd / f"machine-snapshot-{machine}.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


# --------------------------------------------------------------------- check

def _discovered_path(state_dir: Path, machine: str) -> Path:
    return state_dir / f"machine-discovered-{machine}.yaml"


def _load_discovered(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("entries") or [])


def _write_discovered(path: Path, entries: list[dict]) -> None:
    header = (
        "# state/machine-discovered-<machine>.yaml — proposals from tools/machine_doctor.py's\n"
        "# unknown-growth scan (ADR 0031, IRON §58). NEVER the registry itself: a human reviews\n"
        "# each row and either promotes it into config/machine-contract.yaml with a real class,\n"
        "# or removes it here once handled. Safe to hand-edit.\n"
    )
    body = yaml.safe_dump({"entries": entries}, allow_unicode=True, sort_keys=False)
    path.write_text(header + body, encoding="utf-8")


def check(machine: str, *, registry: dict | None = None,
          registry_path: str | Path | None = None,
          state_dir: str | Path | None = None,
          home: str | Path | None = None,
          claude_config_dir: str | Path | None = None,
          opt_dir: str | Path | None = None,
          docker_volumes_dir: str | Path | None = None,
          now: datetime | None = None) -> dict:
    registry = registry if registry is not None else load_registry(registry_path)
    ctx = build_context(registry, machine, home=home, claude_config_dir=claude_config_dir)
    rows = resolve_rows(registry, machine, ctx)
    now = now or datetime.now(timezone.utc)
    sd = Path(state_dir) if state_dir else STATE_DIR
    sd.mkdir(parents=True, exist_ok=True)

    problems: list[dict] = []

    # Rule (a): IRREPLACEABLE, exists, no restore line.
    for r in rows:
        if (r.get("class") == "IRREPLACEABLE" and r["applicable"] and r["exists"]
                and not (r.get("restore") or "").strip()):
            problems.append({"kind": "MISSING_RESTORE", "path": r["resolved"]})

    # Rule (b): a registry row nobody has classified yet — reported until a
    # human reclassifies it, independent of whether its path exists today
    # (e.g. the seed row /root/restore/**).
    for r in rows:
        if r.get("class") == "UNCLASSIFIED":
            problems.append({"kind": "UNCLASSIFIED", "path": r["path"]})

    # Rule (c)+(d): unknown-growth scan.
    unknown_growth = registry.get("unknown_growth") or {}
    min_mb = float(unknown_growth.get("min_mb", 500))
    classify_within_days = float(unknown_growth.get("classify_within_days", 14))

    roots = {
        "HOME": Path(ctx["HOME"]),
        "CLAUDE_CONFIG_DIR": Path(ctx["CLAUDE_CONFIG_DIR"]),
        "OPT": Path(opt_dir) if opt_dir is not None else Path("/opt"),
        "DOCKER_VOLUMES": Path(docker_volumes_dir) if docker_volumes_dir is not None
                           else Path("/var/lib/docker/volumes"),
    }
    all_templates: list[str] = []
    for r in rows:
        all_templates.extend(r.get("alt_templates") or [])

    disc_path = _discovered_path(sd, machine)
    discovered_log = _load_discovered(disc_path)
    logged_by_path = {e.get("path"): e for e in discovered_log}
    today_iso = now.date().isoformat() if hasattr(now, "date") else str(now)[:10]
    newly_added = False

    for root in roots.values():
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if _is_link(child) or not child.is_dir():
                continue
            size_mb = _path_bytes(child) / (1024 * 1024)
            if size_mb < min_mb or _covered(child, all_templates):
                continue
            cpath = str(child)
            entry = logged_by_path.get(cpath)
            if entry is None:
                entry = {"path": cpath, "machine": machine, "class": "UNCLASSIFIED",
                          "discovered": True, "owner": None, "review": None,
                          "restore": None, "first_seen": today_iso,
                          "mb_at_discovery": round(size_mb)}
                discovered_log.append(entry)
                logged_by_path[cpath] = entry
                newly_added = True
            first_seen = entry.get("first_seen") or today_iso
            try:
                age_days = (now.date() - date.fromisoformat(first_seen)).days
            except (ValueError, TypeError):
                age_days = 0
            kind = "CANDIDATE" if age_days >= classify_within_days else "DISCOVERED"
            problems.append({"kind": kind, "path": cpath, "mb": round(size_mb), "age_days": age_days})

    if newly_added:
        _write_discovered(disc_path, discovered_log)

    return {"machine": machine, "problems": problems}


# -------------------------------------------------------------------- report

def report(machine: str, *, registry: dict | None = None,
           registry_path: str | Path | None = None,
           home: str | Path | None = None,
           claude_config_dir: str | Path | None = None) -> list[tuple[str, float]]:
    registry = registry if registry is not None else load_registry(registry_path)
    ctx = build_context(registry, machine, home=home, claude_config_dir=claude_config_dir)
    rows = resolve_rows(registry, machine, ctx)

    totals: dict[str, int] = {}
    for r in rows:
        if not r["applicable"]:
            continue
        cls = r.get("class") or "UNCLASSIFIED"
        totals[cls] = totals.get(cls, 0) + r["bytes"]
    return sorted(((cls, b / (1024 ** 3)) for cls, b in totals.items()), key=lambda t: t[0])


# ------------------------------------------------------------- version-change

def check_on_version_change(machine: str, *, registry: dict | None = None,
                             registry_path: str | Path | None = None,
                             state_dir: str | Path | None = None,
                             home: str | Path | None = None,
                             claude_config_dir: str | Path | None = None,
                             opt_dir: str | Path | None = None,
                             docker_volumes_dir: str | Path | None = None) -> dict:
    """§58 / plan Phase 2: also run `check` when `claude --version` bumped
    since the last snapshot. Refreshes the snapshot afterwards so the same
    bump is not reported again next time."""
    registry = registry if registry is not None else load_registry(registry_path)
    ctx = build_context(registry, machine, home=home, claude_config_dir=claude_config_dir)
    sd = Path(state_dir) if state_dir else STATE_DIR
    snap_path = sd / f"machine-snapshot-{machine}.json"

    current_version = _read_claude_version(Path(ctx["CLAUDE_CONFIG_DIR"]) / ".last-update-result.json")
    recorded_version = None
    if snap_path.exists():
        try:
            recorded_version = (json.loads(snap_path.read_text(encoding="utf-8")) or {}).get("claude_version")
        except (OSError, ValueError):
            recorded_version = None

    changed = current_version != recorded_version
    result = {"changed": changed, "current_version": current_version, "recorded_version": recorded_version}
    if changed:
        result["check"] = check(machine, registry=registry, state_dir=sd,
                                 home=home, claude_config_dir=claude_config_dir,
                                 opt_dir=opt_dir, docker_volumes_dir=docker_volumes_dir)
        snapshot(machine, registry=registry, state_dir=sd, home=home, claude_config_dir=claude_config_dir)
    return result


# ------------------------------------------------------------------------ CLI

def _print_check(result: dict) -> None:
    labels = {
        "MISSING_RESTORE": "IRREPLACEABLE, no restore line",
        "UNCLASSIFIED": "registry row has no class yet",
        "DISCOVERED": "matches no registry row",
        "CANDIDATE": "past classify_within_days, still unclassified",
    }
    problems = result.get("problems", [])
    for p in problems:
        extra = []
        if "mb" in p:
            extra.append(f"~{p['mb']} MB")
        if "age_days" in p:
            extra.append(f"{p['age_days']}d old")
        extra_s = f" ({', '.join(extra)})" if extra else ""
        print(f"  ✗ {p['kind']}: {p['path']}{extra_s} — {labels.get(p['kind'], '')}")
    if problems:
        print(f"machine_doctor check: {len(problems)} problem(s)")
    else:
        print("machine_doctor check: clean — disk agrees with the registry")


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="tools/machine_doctor.py")
    parser.add_argument("--machine", default=None, help="machine key (default: auto-detect)")
    parser.add_argument("--registry", default=None, help="path to machine-contract.yaml")
    parser.add_argument("--state-dir", default=None, help="default: state/")
    parser.add_argument("--home", default=None, help="override $HOME for placeholder resolution/tests")
    parser.add_argument("--claude-config-dir", default=None, help="override $CLAUDE_CONFIG_DIR")
    parser.add_argument("--opt-dir", default=None, help="override the /opt scan root")
    parser.add_argument("--docker-volumes-dir", default=None, help="override the /var/lib/docker/volumes scan root")
    parser.add_argument("--on-version-change", action="store_true",
                         help="run check only if claude --version changed since the last snapshot")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("snapshot", help="write state/machine-snapshot-<machine>.json")
    sub.add_parser("check", help="registry vs disk; exit 1 on any problem")
    sub.add_parser("report", help="one line per class, in GB")
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    machine = args.machine or detect_machine(registry)
    kwargs = dict(registry=registry, home=args.home, claude_config_dir=args.claude_config_dir)
    state_dir = args.state_dir

    if args.on_version_change:
        result = check_on_version_change(machine, state_dir=state_dir, **kwargs,
                                          opt_dir=args.opt_dir, docker_volumes_dir=args.docker_volumes_dir)
        if result["changed"]:
            print(f"CLAUDE_VERSION_CHANGED: {result['recorded_version']} -> {result['current_version']}")
            _print_check(result["check"])
            return 1 if result["check"]["problems"] else 0
        print(f"claude version unchanged ({result['current_version']})")
        return 0

    if args.cmd == "snapshot":
        data = snapshot(machine, state_dir=state_dir, **kwargs)
        sd = Path(state_dir) if state_dir else STATE_DIR
        print(str(sd / f"machine-snapshot-{machine}.json"))
        print(f"{len(data['entries'])} row(s) for machine={machine}")
        return 0

    if args.cmd == "check":
        result = check(machine, state_dir=state_dir, **kwargs,
                        opt_dir=args.opt_dir, docker_volumes_dir=args.docker_volumes_dir)
        _print_check(result)
        return 1 if result["problems"] else 0

    if args.cmd == "report":
        for cls, gb in report(machine, **kwargs):
            print(f"{cls:<14} {gb:8.2f} GB")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
