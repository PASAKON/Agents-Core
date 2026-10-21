"""whois — is this message from my owner? Read-only (OrgMesh P8, CEO 18 Oct; P8c after the second review).

A Project Head started over the mesh gets its brief "by message from its owner", and any session can
rename itself "CTO Main". The `from-name` on a message is chosen by the sender, so it proves nothing.
This checks the message's TRANSPORT address (the `from=` attribute of its header) against the hub's
live_sessions rows (every host, the rows tools/live_sessions.py publishes).

    bash scripts/hub/org-python.sh -m tools.whois --owner <full owner UUID> [--role cto] --from '<from attribute>' [--json]
    bash scripts/hub/org-python.sh -m tools.whois [--json] -- '<name or address>'      (information only)
    bash scripts/hub/org-python.sh -m tools.whois [--json] --id <8 or more hex>        (information only)

  --owner UUID  the owner's FULL session UUID (36 characters), as the brief prints it. Compared for equality.
  --role ROLE   the owner's C-level role (the brief's lane); default: any C-level.
  --from ADDR   the message's `from=` attribute. Only two shapes are accepted, anything else exits 2:
                  uds:/tmp/cc-socks(-<digits>)?/<pid>.sock   a session on THIS host: the pid is the claude
                                                             process that owns the socket, which is the pid
                                                             the hub row stores (checked 2026-10-21)
                  bridge:session_<letters and digits>        a Remote Control sender, usually on another
                                                             host: the one hub row, on any host, whose
                                                             bridge_id is that id (the `bridgeSessionId`
                                                             in its registry record, P8d)

Exit 0: the sender is the owner: the one row (for uds: on this host with that pid; for bridge: on any host with
that bridge id) has the owner's full UUID, is alive, is tmux-claimed by a launcher and holds the owner's C-level
role; a row on this host is also named by the launcher's .uuid lock (a row on another host cannot be: the lock is
a file there), and the owner's UUID is on no other live row.
Exit 1: not verified (no match, id differs, not alive, not claimed, role differs, ambiguous, hub unreachable).
Exit 2: usage error. Exit 0 comes from the verdict, never from the parser: there is no -h / --help, options
are never abbreviated, and every parser exit is mapped to 2.

The information modes print what the hub knows about a name or an id and can never say "owner".
A name is what a session can forge: nothing in the verdict looks at one.

No writes anywhere.
See docs/ops/live-sessions.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

from lib import session_names
from tools import live_sessions as ls

_HEX_DASH = r"[0-9a-f-]{8,36}"
_ID_RE = re.compile(rf"^#?(?:[a-z][a-z_]*-)?(?P<id>[0-9a-f]{{8}})$|^#?(?P<full>{_HEX_DASH})$")
MIN_ID = 8
# [0-9] and [A-Za-z0-9], never \d or \w: those match other scripts' digits and letters. fullmatch only.
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_ROLE_RE = re.compile(r"[a-z][a-z_]{1,30}")
_UDS_RE = re.compile(r"uds:/tmp/cc-socks(?:-[0-9]{1,10})?/(?P<pid>[0-9]{1,10})\.sock")
_BRIDGE_RE = re.compile(r"bridge:session_(?P<id>[A-Za-z0-9]{1,100})")


class Usage(Exception):
    """A bad command line: exit 2."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def parse_id(text: str) -> str | None:
    """The hex id inside "#671f688f", "cto-671f688f" or a UUID (or its prefix), lowercase; None when
    `text` is not an id of at least MIN_ID characters. Used by `--id` only, never on a sender."""
    m = _ID_RE.match((text or "").strip().lower())
    got = (m.group("id") or m.group("full")) if m else None
    return got if got and len(got.replace("-", "")) >= MIN_ID else None


def parse_from(text: str) -> tuple[str, str] | None:
    """("uds", pid) or ("bridge", session id) for a `from=` attribute of exactly one of the two accepted
    shapes; None for anything else (no shell metacharacter, no space, no path trick can be in a match)."""
    if not isinstance(text, str):
        return None
    m = _UDS_RE.fullmatch(text)
    if m:
        pid = int(m.group("pid"))
        return ("uds", str(pid)) if 0 < pid < 2 ** 31 else None
    m = _BRIDGE_RE.fullmatch(text)
    return ("bridge", m.group("id")) if m else None


def _norm(text: str) -> str:
    """A name or address to compare: NFKC, host emoji and leading symbols dropped, lowercase, one space."""
    s = session_names.strip_host(unicodedata.normalize("NFKC", text or ""))
    return " ".join(re.sub(r"^[\W_]+", "", s).casefold().split())


def _uuid_has(row: dict, want: str) -> bool:
    uuid = str(row.get("uuid") or "").lower()
    return bool(want) and (uuid == want or uuid.startswith(want) or uuid.endswith(want))


def resolve(rows, query: str = "", ident: str | None = None) -> list[dict]:
    """Information only. `ident` (from --id) matches the session UUID; `query` matches a row's address
    or name, host emoji and case ignored. A query is never read as an id. Stale rows are included."""
    if ident:
        return [r for r in rows if _uuid_has(r, ident)]
    want = _norm(query)
    return [r for r in rows if want and want in (_norm(r.get("address", "")), _norm(r.get("name", "")))]


def describe(row: dict) -> dict:
    return {
        "host": row["host"], "role": row["role"], "sid": row["sid"], "uuid": row["uuid"],
        "title": row["name"], "alive": not row.get("stale"), "c_level": ls.is_c_level(row["role"]),
        "tmux_claimed": bool(row.get("verified")), "claims": ls.reserved_claim(row),
        "pid": row.get("pid"),
    }


def _owner_role(role: str) -> bool:
    """A C-level session role. "ceo" matches the pattern but is no session: the CEO is never an owner."""
    return ls.is_c_level(role) and role != "ceo"


def _where(row: dict) -> str:
    return f"{row['host']} #{row['sid']}"


def lookup(rows, query: str = "", ident: str | None = None) -> dict:
    """{"ok", "why", "matches", "mode": "info"}: information about a name or an id. `ok` means "found
    exactly one row", not that anyone sent anything."""
    matches = resolve(rows, query, ident)
    out = {"mode": "info", "ok": False, "why": "", "matches": [describe(r) for r in matches]}
    if not matches:
        out["why"] = "no match: no live session answers to that name or id"
    elif len(matches) > 1:
        out["why"] = (f"ambiguous: {len(matches)} live sessions answer to that name or id ("
                      + ", ".join(_where(r) for r in matches) + ")")
    else:
        out.update(ok=True, why="one live session (information only: this is not a sender check)")
    return out


def owner_candidates(rows, role: str, sid: str) -> list[dict]:
    """The live, tmux-claimed rows of C-level `role` whose session id is `sid` and whose UUID ends in it
    (the launchers make it end in the short id). spawn_ph uses it to turn the owner's 8-hex id into the
    full UUID the brief carries."""
    return [r for r in rows
            if r.get("verified") and not r.get("stale") and r.get("role") == role
            and r.get("sid") == sid and str(r.get("uuid") or "").endswith(sid)]


def verify_owner(rows, owner_uuid: str, transport: tuple[str, str], here: str,
                 role: str | None = None) -> dict:
    """{"ok", "why", "matches", "mode": "owner"}: is the sender at `transport` (from parse_from) the
    session whose full UUID is `owner_uuid`? `here` is the host this runs on: a uds socket is a path on
    this host. The name of the sender is not an input."""
    out = {"mode": "owner", "ok": False, "why": "", "matches": []}
    kind, ident = transport
    if kind == "bridge":
        return _verify_bridge(rows, owner_uuid, "session_" + ident, here, role, out)
    pid = int(ident)
    hits = [r for r in rows if r.get("host") == here and r.get("pid") == pid]
    out["matches"] = [describe(r) for r in hits]
    if not hits:
        out["why"] = f"no match: no live session on {here} has pid {pid}"
        return out
    if len(hits) > 1:
        out["why"] = f"ambiguous: {len(hits)} rows on {here} claim pid {pid}"
        return out
    row = hits[0]
    if str(row.get("uuid") or "").lower() != owner_uuid:
        out["why"] = f"id differs: pid {pid} on {here} is {row['role']} #{row['sid']}, not the owner"
    elif row.get("stale"):
        out["why"] = f"not alive: {_where(row)} is the owner's id but its host stopped reporting"
    elif not row.get("verified"):
        out["why"] = "not verified: no launcher tmux claims that session's role (it is read from the name)"
    elif (row["role"] != role) if role else not _owner_role(row["role"]):
        out["why"] = (f"role differs: that session is {row['role']}, the owner is "
                      + (f"a {role}" if role else "a C-level"))
    elif not ls._launcher_uuid(row["role"], row["uuid"]):
        out["why"] = "not verified: the launcher's .uuid lock does not name that session"
    else:
        out.update(ok=True, why=f"owner confirmed: {here} pid {pid} is {row['role']} #{row['sid']}")
    return out


def _verify_bridge(rows, owner_uuid: str, bridge_id: str, here: str, role: str | None, out: dict) -> dict:
    """verify_owner for a `bridge:` sender: the one row, on any host, whose bridge_id is `bridge_id`.
    A bridge id is issued by the Remote Control service to one session and a message carries the
    sender's own, but a publisher can write any value into its rows, so a second row for the same
    id, or a second live row for the owner's UUID, fails closed (a forged row beside the real one
    cannot pass). The `.uuid` lock is a file on the row's own host: checked only when that is here."""
    hits = [r for r in rows if r.get("bridge_id") == bridge_id]
    out["matches"] = [describe(r) for r in hits]
    if not hits:
        out["why"] = "no match: no live session on any host has that bridge session id"
        return out
    if len(hits) > 1:
        out["why"] = f"ambiguous: {len(hits)} rows claim that bridge session id ({', '.join(_where(r) for r in hits)})"
        return out
    row = hits[0]
    twins = [r for r in rows if str(r.get("uuid") or "").lower() == owner_uuid and not r.get("stale")]
    if str(row.get("uuid") or "").lower() != owner_uuid:
        out["why"] = f"id differs: that bridge session is {row['role']} #{row['sid']} on {row['host']}, not the owner"
    elif row.get("stale"):
        out["why"] = f"not alive: {_where(row)} is the owner's id but its host stopped reporting"
    elif len(twins) > 1:
        out["why"] = (f"ambiguous: {len(twins)} live rows carry the owner's UUID ("
                      + ", ".join(_where(r) for r in twins) + ")")
    elif not row.get("verified"):
        out["why"] = "not verified: no launcher tmux claims that session's role (it is read from the name)"
    elif (row["role"] != role) if role else not _owner_role(row["role"]):
        out["why"] = (f"role differs: that session is {row['role']}, the owner is "
                      + (f"a {role}" if role else "a C-level"))
    elif row["host"] == here and not ls._launcher_uuid(row["role"], row["uuid"]):
        out["why"] = "not verified: the launcher's .uuid lock does not name that session"
    else:
        out.update(ok=True, why=f"owner confirmed: bridge session is {row['role']} #{row['sid']} on {row['host']}")
    return out


def format_text(result: dict) -> str:
    owner = result.get("mode") == "owner"
    lines = []
    for m in result["matches"]:
        lines += [f"host: {m['host']}", f"role: {m['role']}" + (" (C-level)" if m["c_level"] else ""),
                  f"sid: {m['sid']}", f"uuid: {m['uuid']}"]
        if not owner:      # the title is whatever the session named itself: never shown beside a verdict
            lines.append(f"title: {m['title']}")
        lines += [f"alive: {'yes' if m['alive'] else 'no (its host stopped reporting)'}",
                  "tmux-claimed: " + ("yes" if m["tmux_claimed"]
                                      else "no (name only: the role is read from the name)")]
        if m["claims"] and not owner:
            lines.append(f"WARNING: the title says {m['claims']} but the role is {m['role']}")
        lines.append("")
    verdict = "owner" if owner else "info"
    flag = ("YES" if result["ok"] else "NO") if owner else ("FOUND" if result["ok"] else "NONE")
    lines.append(f"{verdict}: {flag} — {result['why']}")
    return "\n".join(lines)


def _snapshot() -> list[dict]:
    conn = ls._open_hub()
    try:
        return ls._snapshot_from_hub(conn, ls.DEFAULT_TTL_S)["rows"]
    finally:
        conn.close()


def _here() -> str:
    from lib import config
    return config.self_host()


def _parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="python3 -m tools.whois", add_help=False, allow_abbrev=False)
    ap.add_argument("query", nargs="?", help="information only: a session's name or address")
    ap.add_argument("--id", dest="ident", metavar="HEX", help="information only: 8 or more hex")
    ap.add_argument("--owner", metavar="UUID", help="the owner's full session UUID")
    ap.add_argument("--role", metavar="ROLE", help="the owner's C-level role")
    ap.add_argument("--from", dest="from_", metavar="ADDR", help="the message's from= attribute")
    ap.add_argument("--json", action="store_true")
    return ap


def parse_args(argv) -> argparse.Namespace:
    """The command line, or Usage. Everything the parser could do on its own (help, abbreviation, an
    exit code of 0) is switched off or mapped to Usage."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:      # nothing should exit here; if something does, it is not a verdict
        raise Usage(f"argument error (code {exc.code})") from None
    verdict = args.owner is not None or args.from_ is not None or args.role is not None
    if verdict:
        if args.query is not None or args.ident is not None:
            raise Usage("--owner / --role / --from cannot be combined with a name or --id")
        if args.owner is None or args.from_ is None:
            raise Usage("--owner and --from are both required")
        if not _UUID_RE.fullmatch(args.owner.lower()):
            raise Usage("--owner takes the owner's full session UUID (36 characters)")
        args.owner = args.owner.lower()
        if args.role is not None and not (_ROLE_RE.fullmatch(args.role) and _owner_role(args.role)):
            raise Usage("--role takes a C-level role such as cto")
        args.transport = parse_from(args.from_)
        if args.transport is None:
            raise Usage("--from takes uds:/tmp/cc-socks(-<digits>)?/<pid>.sock or bridge:session_<id>")
    else:
        if (args.query is None) == (args.ident is None):
            raise Usage("give one name, or --id <hex>, or --owner with --from")
        if args.ident is not None:
            args.ident = parse_id(args.ident)
            if args.ident is None:
                raise Usage(f"--id takes at least {MIN_ID} hex characters")
    return args


def main(argv=None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except Usage as exc:
        print(f"whois: usage error: {str(exc)[:200]}", file=sys.stderr)
        return 2
    mode = "owner" if args.owner else "info"
    result = {"mode": mode, "ok": False, "matches": [], "why": ""}
    try:
        here = _here() if args.owner else None
    except Exception as exc:   # an unknown host: a uds path cannot be placed, so nothing is verified
        result["why"] = f"host unknown ({type(exc).__name__}): cannot verify"
    else:
        try:
            rows = _snapshot()
        except Exception as exc:   # the class only: a connect error can name the host
            result["why"] = f"hub unreachable ({type(exc.__cause__ or exc).__name__}): cannot verify"
        else:
            result = (verify_owner(rows, args.owner, args.transport, here, args.role) if args.owner
                      else lookup(rows, args.query or "", args.ident))
    print(json.dumps(result, ensure_ascii=False) if args.json else format_text(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
