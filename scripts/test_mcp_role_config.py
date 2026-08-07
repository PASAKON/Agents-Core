#!/usr/bin/env python3
"""Guards for the per-role MCP split (audit 2026-08-07).

Three defects motivated this file, and each one has a test here that fails if
it comes back:

  G1  A role loaded servers whose tools were NOT on --allowed-tools. Both
      launchers carried a hand-copied string naming org + lungnote only, while
      role cto also loaded supabase — so supabase paid its process and schema
      cost on every launch, then prompted on every call. Fixed by deriving
      --allowed-tools from the same generator that emits the server set.
  G2  mooniex-coord sat in BASE_SERVERS for every role on the strength of 2
      calls out of 6,478 logged. Fixed by making it opt-in.
  G3  CXO_EXTRA_MCP / CXO_SKIP_MCP were documented per-launch overrides that
      silently did nothing through spawn-cto.sh / spawn-cxo.sh, because
      osascript `write text` starts a fresh login shell that does not inherit
      the caller's exports. Fixed by re-exporting them inside CHAT_CMD.

Also pinned: supabase runs --read-only by default (the only reason execute_sql
is safe to pre-approve), and the org tool names come from lib/org_tools_registry
so the shell launchers cannot fall behind the registry the way test_tool_parity's
three Python surfaces cannot.

Run via:  python scripts/test_mcp_role_config.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

import cxo_mcp_config as cfg  # noqa: E402

GEN = str(ROOT / "scripts" / "lib" / "cxo_mcp_config.py")
LAUNCHERS = ("scripts/cto-claude.sh", "scripts/cxo-claude.sh")
SPAWNERS = ("scripts/spawn-cto.sh", "scripts/spawn-cxo.sh")

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _gen(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the generator with the system python3, exactly as the launchers do."""
    return subprocess.run(
        ["python3", GEN, "--root", str(ROOT), *args],
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def _allowed(role: str) -> list[str]:
    proc = _gen("--role", role, "--print-allowed")
    assert proc.returncode == 0, f"--print-allowed failed for {role}: {proc.stderr}"
    return proc.stdout.split()


def test_g2_coord_is_opt_in() -> None:
    print("G2: mooniex-coord is opt-in, not in every role")
    _mark("mooniex-coord" not in cfg.BASE_SERVERS, "not in BASE_SERVERS")
    for role, servers in cfg.ROLE_SERVERS.items():
        _mark("mooniex-coord" not in servers, f"not in ROLE_SERVERS[{role}]")
    _mark("mooniex-coord" not in cfg._names_for("cto"), "absent from role cto by default")
    # Demotion, not removal: opt-in has to actually work.
    os.environ["CXO_EXTRA_MCP"] = "mooniex-coord"
    try:
        _mark(
            "mooniex-coord" in cfg._names_for("cto"),
            "CXO_EXTRA_MCP=mooniex-coord brings it back",
        )
    finally:
        del os.environ["CXO_EXTRA_MCP"]


def test_g1_allowed_matches_servers() -> None:
    print("G1: the allowlist names exactly the servers that got loaded")
    for role in sorted(cfg.ROLE_SERVERS):
        allowed = _allowed(role)
        # A server whose binary is missing on this box is skipped, and its
        # tools must be skipped with it.
        emitted = [n for n in cfg._names_for(role) if cfg._build(n, str(ROOT))]
        named = {t.split("__")[1] for t in allowed if t.startswith("mcp__")}
        _mark(
            named == set(emitted),
            f"{role}: {sorted(named)} == emitted {sorted(emitted)}",
        )
        for builtin in cfg.BUILTIN_TOOLS:
            _mark(builtin in allowed, f"{role}: keeps built-in {builtin}")


def test_org_tools_come_from_registry() -> None:
    print("org tool names are the registry's, not a copy")
    sys.path.insert(0, str(ROOT))
    from lib.org_tools_registry import REGISTRY  # noqa: PLC0415

    expected = {f"mcp__org__{s.name}" for s in REGISTRY}
    got = {t for t in _allowed("cto") if t.startswith("mcp__org__")}
    _mark(got == expected, f"all {len(expected)} registry tools present, no extras")


def test_launchers_derive_allowed() -> None:
    print("G1: neither launcher hardcodes a tool list any more")
    for rel in LAUNCHERS:
        text = (ROOT / rel).read_text()
        # Capture to end-of-line, not to the next quote: the derived form nests
        # quotes ("$ROOT/...") and a [^"]* group would truncate before the flag
        # this test is looking for, passing the "no hand-copied names" check for
        # the wrong reason.
        m = re.search(r"^ALLOWED=(.*)$", text, re.M)
        _mark(m is not None, f"{rel}: has an ALLOWED assignment")
        if m:
            body = m.group(1)
            _mark(
                "cxo_mcp_config.py" in body and "--print-allowed" in body,
                f"{rel}: ALLOWED is derived from the generator",
            )
            _mark(
                "mcp__org__wiki_read" not in body,
                f"{rel}: no hand-copied tool names remain",
            )


def test_g3_spawn_forwards_env() -> None:
    print("G3: spawn scripts forward per-launch env into the new login shell")
    for rel in SPAWNERS:
        text = (ROOT / rel).read_text()
        _mark("ENV_PREFIX" in text, f"{rel}: builds ENV_PREFIX")
        _mark(
            re.search(r'CHAT_CMD="\$\{ENV_PREFIX\}', text) is not None,
            f"{rel}: ENV_PREFIX is prepended to CHAT_CMD",
        )
        for var in ("CXO_EXTRA_MCP", "CXO_SKIP_MCP", "CXO_STRICT_MCP"):
            _mark(var in text, f"{rel}: forwards {var}")

        # Execute the real loop text out of the script, so this tests shipped
        # code rather than a paraphrase. Extracting beats invoking spawn-cto.sh,
        # which would take locks and open an iTerm window.
        loop = re.search(r"(ENV_PREFIX=\"\"\nfor v in .*?\ndone)", text, re.S)
        _mark(loop is not None, f"{rel}: ENV_PREFIX loop is extractable")
        if loop:
            proc = subprocess.run(
                ["bash", "-uc", loop.group(1) + '\nprintf "%s" "$ENV_PREFIX"'],
                capture_output=True,
                text=True,
                env={**os.environ, "CXO_EXTRA_MCP": "meigen", "CXO_SKIP_MCP": ""},
            )
            out = proc.stdout
            _mark(
                "export CXO_EXTRA_MCP=meigen &&" in out,
                f"{rel}: loop exports a set var ({out.strip() or '<empty>'})",
            )
            _mark("CXO_SKIP_MCP" not in out, f"{rel}: loop skips an empty var")


def test_supabase_read_only_by_default() -> None:
    print("supabase is read-only unless explicitly told otherwise")
    entry = cfg._build("supabase", str(ROOT))
    if entry is None:
        _mark(True, "supabase CLI not installed here — skipped")
        return
    _mark("--read-only" in entry["args"], "default args carry --read-only")
    allowed = _allowed("cto")
    _mark(
        "mcp__supabase__execute_sql" in allowed,
        "execute_sql is pre-approved (safe only because of --read-only)",
    )
    _mark(
        "mcp__supabase__apply_migration" not in allowed,
        "apply_migration stays off the allowlist",
    )
    os.environ["CXO_SUPABASE_WRITE"] = "1"
    try:
        _mark(
            "--read-only" not in cfg._build("supabase", str(ROOT))["args"],
            "CXO_SUPABASE_WRITE=1 drops --read-only",
        )
    finally:
        del os.environ["CXO_SUPABASE_WRITE"]


def test_borrow_mode() -> None:
    print("--servers borrow mode is isolated from role config and env")
    os.environ["CXO_EXTRA_MCP"] = "supabase"
    try:
        _mark(
            cfg._names_for("", "meigen") == ["meigen"],
            "explicit --servers ignores CXO_EXTRA_MCP",
        )
    finally:
        del os.environ["CXO_EXTRA_MCP"]
    proc = _gen("--servers", "lungnote", "--print-allowed", "--no-builtins")
    tools = proc.stdout.split()
    _mark(proc.returncode == 0 and bool(tools), "borrow allowlist is non-empty")
    _mark(
        all(t.startswith("mcp__lungnote__") for t in tools),
        "--no-builtins yields MCP tools only (no Read/Bash)",
    )


if __name__ == "__main__":
    for fn in (
        test_g2_coord_is_opt_in,
        test_g1_allowed_matches_servers,
        test_org_tools_come_from_registry,
        test_launchers_derive_allowed,
        test_g3_spawn_forwards_env,
        test_supabase_read_only_by_default,
        test_borrow_mode,
    ):
        fn()
        print()
    print(f"{'FAILED' if _failures else 'OK'} — {_failures} failure(s)")
    sys.exit(1 if _failures else 0)
