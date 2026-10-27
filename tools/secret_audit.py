#!/usr/bin/env python3
"""Who read which secret? Names only, never a value (HQSecurity, order O-20261027-1347-4e62).

    who NAME [--since 30d] [--host H] [--json]
        Every audit row (hub events kind=secret_read, plus the local spool) whose variable names
        contain NAME (case-insensitive): when (Asia/Bangkok), host, user, role, session, task,
        PH project, Run card, command.
    flush
        Upload the spool to the hub (one transaction), then drop it. Needs ORG_DB_URL.
    lookback [--since 30d] [--out /root/hqsecurity/lookback-<date>.md]
        What we can say about the past from records that ALREADY exist: hub events, Claude Bash
        tool_use inputs on this host (never tool results), the Run ledger, Infisical's own log.
        Prints to stdout; --out writes a new 0600 file. The report maps where credential literals may
        sit (file:line): keep it out of every repo.

The rows are written by tools/infisical_setup.py (`run`, `last4`); the hub needs ORG_DB_URL, so run
this as `bash scripts/hub/org-python.sh tools/secret_audit.py who NAME`. Without ORG_DB_URL, `who`
reads the local spool only and says so. ORG_SECRET_AUDIT=off in a caller's environment skips its row.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infisical_setup as inf  # noqa: E402  (stdlib-only sibling; owns the audit writer)

BKK = dt.timezone(dt.timedelta(hours=7))          # Thailand has no DST
TRANSCRIPT_GLOBS = ("/root/.claude/projects/*/*.jsonl", "/home/*/.claude/projects/*/*.jsonl")
RUN_LEDGER = "/opt/MoonieXHQ/Projects/MoonieX/Console/data/run-ledger.jsonl"
DOORS = ("infisical run", "infisical export", "infisical_setup.py", "with-org-db-env.sh",
         "org-python.sh", "/etc/infisical")
_ENV_FILE = re.compile(r"\.env(?![A-Za-z0-9_])")
_ASSIGN = re.compile(r"\b([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)="
                     r"(?!\s|$|[\"']?\$|[\"']{2}|[\"']?<)(\S+)")
_BENIGN_VALUE = {"off", "on", "0", "1", "true", "false", "yes", "no"}      # a switch, not a credential
_LONG_RUN = re.compile(r"[A-Za-z0-9_\-+/=.]{32,}")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_RUN_SUB = re.compile(r"infisical_setup\.py\s+(run|last4|put|import-env|perms|status|plan|apply|mkdir|save)"
                      r"(?:\s+([A-Za-z][A-Za-z0-9_-]*)\s+(prod|dev))?")


def parse_since(text: str) -> dt.datetime:
    m = re.fullmatch(r"(\d+)([dhm])", text.strip())
    if not m:
        sys.exit(f"--since: want 30d / 12h / 90m, got {text!r}")
    unit = {"d": "days", "h": "hours", "m": "minutes"}[m.group(2)]
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(**{unit: int(m.group(1))})


def _iso(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def bkk(ts: str) -> str:
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(BKK).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts or "?"


# --- reading the rows --------------------------------------------------------------------------

def hub_query(sql: str, args: tuple = (), url: str | None = None) -> list[tuple]:
    """One read-only query against the hub; raises if there is no URL, psycopg or connection."""
    url = url or os.environ.get("ORG_DB_URL")
    if not url:
        raise RuntimeError("ORG_DB_URL is not set")
    import psycopg
    with psycopg.connect(url, connect_timeout=5,
                         options="-c default_transaction_read_only=on -c statement_timeout=30000") as conn:
        return conn.execute(sql, args).fetchall()


def open_regular(path: str):
    """A text file object for a regular file, else None. Never follows a symlink, never blocks on a
    FIFO, never opens a directory or device: state/ and /home/*/.claude are writable by other users
    and this tool may run as root (CTO_Gate_MergeChecklist 2b)."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            return None
        return os.fdopen(fd, "r", encoding="utf-8", errors="replace")
    except OSError:
        os.close(fd)
        return None


def spool_files() -> list[str]:
    """Regular spool files of an audit dir that is ours and closed to others; else nothing."""
    d = inf.audit_dir()
    if inf.audit_dir_unsafe(d):
        return []
    out = []
    for p in sorted(glob.glob(os.path.join(d, "spool-*.jsonl"))):
        try:
            if stat.S_ISREG(os.lstat(p).st_mode):
                out.append(p)
        except OSError:
            pass
    return out


def _parse_line(line: str) -> dict | None:
    try:
        rec = json.loads(line)
    except ValueError:
        return None
    return rec if isinstance(rec, dict) and rec.get("ts") and isinstance(rec.get("names"), list) else None


def load_records(since: dt.datetime, host: str | None = None, url: str | None = None) -> tuple[list[dict], list[str]]:
    """(audit rows oldest first, notes about sources that could not be read)."""
    cut, notes, out = _iso(since), [], {}
    try:
        for (payload,) in hub_query("SELECT payload FROM events WHERE kind=%s AND ts>=%s ORDER BY ts",
                                    (inf.AUDIT_KIND, cut), url):
            rec = _parse_line(payload or "")
            if rec:
                out.setdefault(_key(rec), {**rec, "source": "hub"})
    except Exception as exc:                                  # no hub is a note, not a failure
        notes.append(f"hub not read ({exc.__class__.__name__}: {str(exc)[:120]}); spool only")
    for path in spool_files():
        fh = open_regular(path)
        if fh is None:
            continue
        with fh:
            for line in fh:
                rec = _parse_line(line)
                if rec and rec["ts"] >= cut:
                    out.setdefault(_key(rec), {**rec, "source": "spool"})
    rows = [r for r in out.values() if not host or r.get("host") == host]
    return sorted(rows, key=lambda r: r["ts"]), notes


def _key(rec: dict) -> tuple:
    return (rec.get("ts"), rec.get("host"), rec.get("pid"), rec.get("session"), tuple(rec.get("names") or ()))


# --- who ---------------------------------------------------------------------------------------

def cmd_who(args: argparse.Namespace) -> int:
    rows, notes = load_records(parse_since(args.since), args.host)
    want = args.name.upper()
    rows = [r for r in rows if any(want in str(n).upper() for n in r["names"])]
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print(f"no audit row names {args.name} since {args.since} (rows only exist from the day the audit shipped)")
        return 0
    print(f"{len(rows)} read(s) of *{args.name}* since {args.since} (time is Asia/Bangkok)")
    for r in rows:
        print(f"{bkk(r['ts'])}  {r.get('host') or '?'}  {r.get('user') or '?'}  role={r.get('role') or '-'}  "
              f"session={r.get('session') or '-'}  task={r.get('task_id') or '-'}  ph={r.get('ph_project') or '-'}  "
              f"card={r.get('run_card') or '-'}  {r.get('project')}/{r.get('env')}  [{r['source']}]")
        print(f"    $ {(r.get('cmd') or r.get('argv0') or '')[:160]}")
    return 0


# --- flush -------------------------------------------------------------------------------------

def _append(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)


def cmd_flush(args: argparse.Namespace, url: str | None = None) -> int:
    url = url or os.environ.get("ORG_DB_URL")
    if not url:
        print("flush: ORG_DB_URL is not set; run it as `bash scripts/hub/org-python.sh tools/secret_audit.py flush`",
              file=sys.stderr)
        return 2
    import psycopg
    sent = files = 0
    for path in spool_files():
        taken = f"{path}.flushing-{os.getpid()}"
        os.rename(path, taken)                    # atomic: a writer meanwhile starts a fresh spool file
        fh = open_regular(taken)                  # re-checked after the move: a swapped-in link is dropped, not read
        if fh is None:
            os.remove(taken)
            continue
        with fh:
            text = fh.read()
        good, keep = [], []
        for line in text.splitlines():
            rec = _parse_line(line)
            (good if rec and rec.get("user") and rec.get("host") else keep).append(rec or line)
        try:
            with psycopg.connect(url, connect_timeout=5) as conn:     # one transaction, committed on exit
                with conn.cursor() as cur:
                    cur.executemany(inf.AUDIT_INSERT_SQL, [inf.audit_row(r) for r in good])
        except Exception as exc:
            _append(path, text)                   # nothing lost: the whole file goes back
            os.remove(taken)
            print(f"flush: hub refused ({exc.__class__.__name__}); {os.path.basename(path)} kept", file=sys.stderr)
            return 1
        if keep:                                  # lines that are not audit rows stay for a human
            _append(path, "".join((json.dumps(k) if isinstance(k, dict) else k) + "\n" for k in keep))
        os.remove(taken)
        sent, files = sent + len(good), files + 1
    print(f"flushed {sent} row(s) from {files} spool file(s)")
    return 0


# --- lookback ----------------------------------------------------------------------------------

def _looks_like_token(run: str) -> bool:
    if _UUID.match(run) or (re.fullmatch(r"[0-9a-f]+", run) and len(run) in (32, 40, 64)):
        return False
    if run.startswith(("-", "/", "./", "../", "~/")):
        return False                              # a flag, or a path (the long dir names are project names)
    if "/" in run and "+" not in run and "=" not in run:
        return False                              # owner/repo/pull/1, scripts/hub/x.sh: base64 would carry + or =
    return (any(c.isupper() for c in run) and any(c.islower() for c in run) and any(c.isdigit() for c in run)) \
        or bool(re.fullmatch(r"[0-9a-f]+", run))


def leak_hint(command: str) -> str | None:
    """'assign:NAME' or 'token' when a command carries something credential-shaped. Never the value."""
    for m in _ASSIGN.finditer(command):
        if m.group(2).strip("\"';)").lower() not in _BENIGN_VALUE:
            return f"assign:{m.group(1)}"
    for word in command.split():
        assign = re.match(r"-*[A-Za-z_][\w-]*=(.*)$", word)
        if assign:
            word = assign.group(1)                   # --flag=VALUE or NAME=VALUE: judge the value
        if any(_looks_like_token(r) for r in _LONG_RUN.findall(word)):
            return "token"
    return None


def transcript_commands(since: dt.datetime):
    """(file, line no, session id, project dir, ts, command) for every Bash tool_use input that
    touches a secret door. Tool RESULTS are never read: only message.content[type=tool_use].input."""
    cut = since.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    for pattern in TRANSCRIPT_GLOBS:
        for path in sorted(glob.glob(pattern)):
            if os.path.islink(os.path.dirname(path)):
                continue                          # a project dir that is a link may point anywhere
            fh = open_regular(path)
            if fh is None:
                continue
            with fh:
                if dt.datetime.fromtimestamp(os.fstat(fh.fileno()).st_mtime, dt.timezone.utc) < since:
                    continue
                for n, line in enumerate(fh, 1):
                    if '"tool_use"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    ts = str(obj.get("timestamp") or "")
                    parts = (obj.get("message") or {}).get("content") if isinstance(obj.get("message"), dict) else None
                    if ts[:19] < cut or not isinstance(parts, list):
                        continue
                    for part in parts:
                        if not (isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "Bash"):
                            continue
                        cmd = (part.get("input") or {}).get("command")
                        if isinstance(cmd, str) and (any(d in cmd for d in DOORS) or _ENV_FILE.search(cmd)):
                            yield path, n, Path(path).stem, Path(path).parent.name, ts, cmd


def door_label(cmd: str) -> list[str]:
    labels = []
    for m in _RUN_SUB.finditer(cmd):
        labels.append(f"infisical_setup.py {m.group(1)}" + (f" {m.group(2)}/{m.group(3)}" if m.group(2) else ""))
    labels += [d for d in DOORS if d != "infisical_setup.py" and d in cmd]
    if _ENV_FILE.search(cmd):
        labels.append(".env")
    return sorted(set(labels)) or ["infisical_setup.py"]


def build_lookback(since_text: str, url: str | None = None) -> tuple[str, dict]:
    since = parse_since(since_text)
    now = dt.datetime.now(BKK)
    counts: dict = {}
    # a) the audit rows and older hub events
    rows, notes = load_records(since, None, url)
    per_name: dict[str, dict] = {}
    for r in rows:
        who = r.get("session") or f"{r.get('user')}@{r.get('host')}"
        for name in r["names"]:
            d = per_name.setdefault(name, {"reads": 0, "who": set(), "roles": set(), "hosts": set(), "ts": []})
            d["reads"] += 1
            d["who"].add(who)
            d["roles"].add(r.get("role") or "-")
            d["hosts"].add(r.get("host") or "?")
            d["ts"].append(r["ts"])
    older: list[tuple] = []
    try:
        older = hub_query("SELECT kind, count(*), count(DISTINCT actor), min(ts), max(ts) FROM events "
                          "WHERE kind <> %s AND ts >= %s AND (payload ILIKE %s OR payload ILIKE %s) "
                          "GROUP BY kind ORDER BY 2 DESC LIMIT 30",
                          (inf.AUDIT_KIND, _iso(since), "%infisical%", "%ORG_DB_URL%"), url)
    except Exception as exc:
        notes.append(f"older hub events not read ({exc.__class__.__name__})")
    # b) transcripts
    doors: dict[str, dict] = collections.defaultdict(lambda: {"n": 0, "sessions": set(), "first": "~", "last": ""})
    sessions: dict[str, dict] = {}
    leaks: list[str] = []
    n_cmds = 0
    for path, line_no, session, proj, ts, cmd in transcript_commands(since):
        n_cmds += 1
        for label in door_label(cmd):
            d = doors[label]
            d["n"] += 1
            d["sessions"].add(session)
            d["first"], d["last"] = min(d["first"], ts), max(d["last"], ts)
        s = sessions.setdefault(session, {"project": proj, "n": 0, "first": "~", "last": ""})
        s["n"] += 1
        s["first"], s["last"] = min(s["first"], ts), max(s["last"], ts)
        hint = leak_hint(cmd)
        if hint:
            leaks.append(f"possible leak: {path}:{line_no} ({hint})")
    # c) Run ledger
    ledger = "not reachable on this host"
    fh = open_regular(RUN_LEDGER)
    if fh is not None:
        cards, states = set(), collections.Counter()
        cut = _iso(since)
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and str(rec.get("ts") or "") >= cut:
                    cards.add(rec.get("id"))
                    states[rec.get("state")] += 1
        ledger = (f"{len(cards)} card(s) with a ledger line in the window ({dict(states)}). The ledger keeps id, ts, "
                  f"state, sha256, exit, ms and NO command text, so a card cannot be tied to a secret from it.")
    counts.update(audit_rows=len(rows), door_commands=n_cmds, leaks=len(leaks), names=len(per_name),
                  sessions=len(sessions))
    L = [f"# HQSecurity lookback: who touched secrets, last {since_text}",
         "",
         f"Generated {now:%Y-%m-%d %H:%M} Asia/Bangkok on this host. Names only: no value is in this file.",
         "",
         "## Top line",
         f"- Audit rows (hub + spool): **{len(rows)}** covering **{len(per_name)}** variable name(s). Rows exist only "
         f"from the day the audit shipped, so for the earlier part of the window this is 0 by construction.",
         f"- Bash commands in Claude transcripts that touch a secret door: **{n_cmds}** across **{len(sessions)}** session(s).",
         f"- Possible credential literals in those commands: **{len(leaks)}** (a heuristic lead, not a verdict).",
         "- Infisical's own audit log: **none on the free plan** (below)."]
    for n in notes:
        L.append(f"- Note: {n}")
    L += ["", "## A. Hub audit rows, per variable name",
          "", "| Variable | Reads | Distinct sessions/users | Roles | Hosts | First seen | Last seen |",
          "|---|---|---|---|---|---|---|"]
    for name, d in sorted(per_name.items(), key=lambda kv: (-kv[1]["reads"], kv[0])):
        L.append(f"| `{name}` | {d['reads']} | {len(d['who'])} | {', '.join(sorted(d['roles']))} | "
                 f"{', '.join(sorted(d['hosts']))} | {bkk(min(d['ts']))} | {bkk(max(d['ts']))} |")
    if not per_name:
        L.append("| (no audit rows yet) | | | | | | |")
    L += ["", "### Older hub events that mention infisical or ORG_DB_URL (counts only, payloads not printed)", "",
          "| Event kind | Rows | Distinct actors | First | Last |", "|---|---|---|---|---|"]
    L += [f"| {k} | {c} | {a} | {bkk(lo)} | {bkk(hi)} |" for k, c, a, lo, hi in older] or ["| (none read) | | | | |"]
    L += ["", "## B. Claude session transcripts on this host (Bash tool_use inputs only)", "",
          "Which door was used, not which variable: a command that goes through the wrapper does not list names.",
          "", "| Door | Commands | Sessions | First | Last |", "|---|---|---|---|---|"]
    for label, d in sorted(doors.items(), key=lambda kv: -kv[1]["n"]):
        L.append(f"| `{label}` | {d['n']} | {len(d['sessions'])} | {bkk(d['first'])} | {bkk(d['last'])} |")
    if not doors:
        L.append("| (none found) | | | | |")
    L += ["", "### Top sessions by door commands", "", "| Session (file name) | Project dir | Commands | First | Last |",
          "|---|---|---|---|---|"]
    for sid, s in sorted(sessions.items(), key=lambda kv: -kv[1]["n"])[:25]:
        L.append(f"| {sid} | {s['project']} | {s['n']} | {bkk(s['first'])} | {bkk(s['last'])} |")
    L += ["", "### Possible leaks (file:line only, value withheld)", ""]
    L += [f"- {x}" for x in leaks[:200]] or ["- none found"]
    if len(leaks) > 200:
        L.append(f"- ... and {len(leaks) - 200} more")
    L += ["", "## C. Run Inbox cards", "", f"- Run ledger: {ledger}.",
          "- Cards run with a whitelisted environment that carries no card id, so an audit row written during a "
          "card has `run_card` empty today (Console executor change needed: export `RUN_ID`).",
          "", "## D. Infisical's own audit log", "",
          "- docs/design/secrets-infisical/PLAN.md §2: Cloud Free has **no audit log** (Pro: 30-day log, about "
          "$80-92/month, CEO decision). No paid API was called. The log of who read what is therefore ours alone: "
          "the audit rows in section A.", ""]
    return "\n".join(L), counts


def write_private(path: str, text: str) -> None:
    """Create `path` (mode 0600), refusing an existing file and a symlink. The report is a map of where
    credential literals may sit: it must never land in a repo or through a link."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)


def cmd_lookback(args: argparse.Namespace) -> int:
    """Report to stdout, or to --out as a new private file. Never a default path inside a repo."""
    text, counts = build_lookback(args.since)
    summary = ", ".join(f"{k}={v}" for k, v in counts.items())
    if not args.out:
        print(text)
        print(f"({summary})", file=sys.stderr)
        return 0
    try:
        write_private(args.out, text)
    except OSError as exc:
        print(f"lookback: not written to {args.out} ({exc.__class__.__name__}: it must be a new file, not a link)",
              file=sys.stderr)
        return 1
    print(f"wrote {args.out}: {summary}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("who", help="who read a variable")
    w.add_argument("name")
    w.add_argument("--since", default="30d")
    w.add_argument("--host")
    w.add_argument("--json", action="store_true")
    sub.add_parser("flush", help="upload the spool to the hub, then drop it")
    lb = sub.add_parser("lookback", help="report from records that already exist")
    lb.add_argument("--since", default="30d")
    lb.add_argument("--out", help="write here as a NEW 0600 file (refuses an existing path or a link); "
                                  "default is stdout. Keep it out of any repo: it maps where credential "
                                  "literals may sit")
    args = ap.parse_args(argv)
    return {"who": cmd_who, "flush": cmd_flush, "lookback": cmd_lookback}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
