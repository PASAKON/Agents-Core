# hook-research-gate.py + hook-cwd-guard.py

ADR 0028 §6 (session cto-0e8d80b8, 2026-09-22): two rules a doc could not
enforce, so they became hooks (memory: put the rule in the tool, not the doc).

## hook-research-gate.py — PreToolUse, matcher `WebSearch|WebFetch|mcp__org__wiki_search|Read|Grep|Bash`

Blocks `WebSearch` / `WebFetch` (exit 2) while the session hasn't checked the
research cache (`Agents/Wikis/research/`, contract in its README). Every
other matched call passes through silently — they only ever arm the gate.

**Arms** `~/.gateguard/research-gate-<session_id>.ok` (valid 12h) when the
session calls `mcp__org__wiki_search` (any query), Reads/Greps a path
containing `/research/` or `RESEARCH-INDEX.md`, or runs a Bash command
mentioning `research/` or `RESEARCH-INDEX`.

Escape hatch: `RESEARCH_GATE=off`. Fails open on bad/missing stdin fields.

## hook-cwd-guard.py — PreToolUse, matcher `Bash`

Simulates where a Bash command would leave the shell's cwd before it runs.
Splits the command into top-level segments (on `;`, `&&`, `||`, `|`,
newlines), ignoring quotes, `( ... )` / `$( ... )` subshell depth, and
heredoc bodies. A segment whose first word is `cd`/`pushd` moves the
simulated cwd; `popd`/`cd -` return to the previous one; a variable in the
path (`cd "$W"`) makes the result UNKNOWN.

Home = `$CLAUDE_PROJECT_DIR` (hooks get it) → fallback: the event's `cwd`.
Simulated end == home → allow (exit 0). Anywhere else, or UNKNOWN → block
(exit 2) with a fix: `git -C <path>`, absolute paths, a subshell
`(cd X && ...)`, or `&& cd <home>` at the end.

Escape hatch: `CWD_GUARD=off`. Fails open on non-JSON stdin, no `command`,
or no resolvable home.

## Testing by hand

```bash
echo '{"session_id":"s1","tool_name":"WebSearch","tool_input":{"query":"x"}}' \
  | python3 scripts/hook-research-gate.py; echo "exit=$?"

echo '{"tool_name":"Bash","tool_input":{"command":"cd /a && x; cd /b && y"},"cwd":"/repo"}' \
  | CLAUDE_PROJECT_DIR=/repo python3 scripts/hook-cwd-guard.py; echo "exit=$?"
```

Both print their block message on stderr and exit 2 when blocking, exit 0
and silent otherwise.

## Automated tests

```bash
pytest scripts/test_hook_research_gate.py scripts/test_hook_cwd_guard.py -q
```
