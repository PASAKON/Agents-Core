"""whois — who is this sender? Read-only (OrgMesh P8, CEO 18 Oct).

A Project Head started over the mesh gets its brief "by message from its owner", and any session can
rename itself "CTO Main". This checks a sender against the hub's live_sessions rows (every host, the
rows tools/live_sessions.py publishes) before the message is taken as an order.

    bash scripts/hub/org-python.sh -m tools.whois <name|address|session-id> [--owner <sid>] [--json]

  <query>      a session's address or name (host emoji and case ignored), or an id: 8 or more hex, a "#" or
               "<role>-" in front allowed ("cto-671f688f"), matched against the session UUID
  --owner SID  exit 0 only when the query resolves to exactly ONE live session whose UUID starts or ends
               with SID (8 or more characters; "cto-<8 hex>" is read too). Exit 1 otherwise, with why.

Exit 0: one session resolved (and, with --owner, it is the owner). Exit 1: no match, ambiguous, the id
differs, not alive, or the hub could not be read (cannot verify = not verified). Usage errors exit 2.

The id is compared with the UUID, never the row's `sid`: for a row no launcher tmux claims, `sid` is
parsed from the session's own name, and a name is what a session can forge.

No writes anywhere.
See docs/ops/live-sessions.md.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata

from lib import session_names
from tools import live_sessions as ls

_HEX_DASH = r"[0-9a-f-]{8,36}"
_ID_RE = re.compile(rf"^#?(?:[a-z][a-z_]*-)?(?P<id>[0-9a-f]{{8}})$|^#?(?P<full>{_HEX_DASH})$")
MIN_ID = 8


def parse_id(text: str) -> str | None:
    """The hex id inside "#671f688f", "cto-671f688f" or a UUID (or its prefix), lowercase; None when
    `text` is not an id of at least MIN_ID characters. Seen as a name instead, it simply matches nothing."""
    m = _ID_RE.match((text or "").strip().lower())
    got = (m.group("id") or m.group("full")) if m else None
    return got if got and len(got.replace("-", "")) >= MIN_ID else None


def _norm(text: str) -> str:
    """A name or address to compare: NFKC, host emoji and leading symbols dropped, lowercase, one space."""
    s = session_names.strip_host(unicodedata.normalize("NFKC", text or ""))
    return " ".join(re.sub(r"^[\W_]+", "", s).casefold().split())


def _uuid_has(row: dict, want: str) -> bool:
    uuid = str(row.get("uuid") or "").lower()
    return bool(want) and (uuid == want or uuid.startswith(want) or uuid.endswith(want))


def resolve(rows, query: str) -> list[dict]:
    """Every row `query` names: an id matches the session UUID; anything else matches a row's address
    or name. Stale rows are included: a silent host is not proof its session ended."""
    ident = parse_id(query)
    if ident:
        return [r for r in rows if _uuid_has(r, ident)]
    want = _norm(query)
    return [r for r in rows if want and want in (_norm(r.get("address", "")), _norm(r.get("name", "")))]


def describe(row: dict) -> dict:
    return {
        "host": row["host"], "role": row["role"], "sid": row["sid"], "uuid": row["uuid"],
        "title": row["name"], "alive": not row.get("stale"), "c_level": ls.is_c_level(row["role"]),
        "tmux_claimed": bool(row.get("verified")), "claims": ls.reserved_claim(row),
    }


def _where(row: dict) -> str:
    return f"{row['host']} #{row['sid']}"


def check(rows, query: str, owner: str | None = None) -> dict:
    """{"ok", "why", "matches"}: `ok` is the exit code's meaning. Without `owner` it is "exactly one
    session"; with it, that one session is the owner and alive. `why` is one line, fixed text plus ids."""
    matches = resolve(rows, query)
    out = {"ok": False, "why": "", "matches": [describe(r) for r in matches]}
    if not matches:
        out["why"] = "no match: no live session answers to that name or id"
    elif len(matches) > 1:
        out["why"] = (f"ambiguous: {len(matches)} live sessions answer to that name or id ("
                      + ", ".join(_where(r) for r in matches) + ")")
    elif owner is None:
        out.update(ok=True, why="one live session")
    else:
        want = parse_id(owner)
        row = matches[0]
        if want is None:
            out["why"] = f"owner id must be at least {MIN_ID} hex characters, got {owner[:40]!r}"
        elif not _uuid_has(row, want):
            out["why"] = f"id differs: the session called that is {_where(row)}, not the owner {want}"
        elif row.get("stale"):
            out["why"] = f"not alive: {_where(row)} is the owner's id but its host stopped reporting"
        else:
            out.update(ok=True, why=f"owner confirmed: {_where(row)}")
    return out


def format_text(result: dict, owner: str | None = None) -> str:
    lines = []
    for m in result["matches"]:
        lines += [f"host: {m['host']}", f"role: {m['role']}" + (" (C-level)" if m["c_level"] else ""),
                  f"sid: {m['sid']}", f"uuid: {m['uuid']}", f"title: {m['title']}",
                  f"alive: {'yes' if m['alive'] else 'no (its host stopped reporting)'}",
                  "tmux-claimed: " + ("yes" if m["tmux_claimed"]
                                      else "no (name only: the role is read from the name)")]
        if m["claims"]:
            lines.append(f"WARNING: the title says {m['claims']} but the role is {m['role']}")
        lines.append("")
    verdict = "owner" if owner is not None else "whois"
    lines.append(f"{verdict}: {'YES' if result['ok'] else 'NO'} — {result['why']}")
    return "\n".join(lines)


def _snapshot() -> list[dict]:
    conn = ls._open_hub()
    try:
        return ls._snapshot_from_hub(conn, ls.DEFAULT_TTL_S)["rows"]
    finally:
        conn.close()


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m tools.whois", description=__doc__.splitlines()[0])
    ap.add_argument("query", help="a session's name, address or id")
    ap.add_argument("--owner", metavar="SID", help="exit 0 only if the query is this session")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        rows = _snapshot()
    except Exception as exc:   # the class only: a connect error can name the host
        result = {"ok": False, "matches": [],
                  "why": f"hub unreachable ({type(exc.__cause__ or exc).__name__}): cannot verify"}
    else:
        result = check(rows, args.query, args.owner)
    print(json.dumps(result, ensure_ascii=False) if args.json else format_text(result, args.owner))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
