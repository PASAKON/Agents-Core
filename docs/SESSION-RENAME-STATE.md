# Session Rename State (task-460f3eaf)

`scripts/session-rename.sh` sets a C-level session's Claude display name (the
third naming layer — the one the mobile app and Remote Control show) by
typing a literal `/rename ...` into the session's own tmux pane, because
`/rename` is TUI-only and an agent cannot call it as a tool. Before this
change the script was write-only: it queued the keystroke every time and
recorded nothing, so nobody could tell whether a rename had landed, and the
script could not be called routinely (every call retyped the command). This
doc covers the record it now keeps.

## Where the state lives

```
state/locks/<role>-<session_id>.topic
```

Same file, same naming, as every other `.topic` sibling in this repo — see
`tools/session_name.py`'s `LOCK_SUFFIXES` (the full family a launcher drops
per session: `.lock .run .tty .winid .watcher-pid .topic`) and
`tools/send_to_cxo.py`'s ephemeral-spawn dedupe slug, a different *use* of
the same suffix on a different id shape (`req-xxxxxxxx` vs. a plain 8-hex C-
level session id, so the two never collide).

`<role>` is `${CXO_ROLE:-cto}` (lowercase — `cto`/`cmo`/`cgo`/`cfo`/`cxo`).
`<session_id>` is `${CTO_SESSION_ID:-$CXO_SESSION_ID}`. If neither is set
(an ad-hoc invocation with no live session id), persistence is disabled
entirely — the script degrades to its old always-send behaviour rather than
guessing at a shared filename.

## Format

Plain text, no trailing newline, one value: the topic string exactly as it
was sent — i.e. **after** the existing 40-char trim, before it's wrapped into
the full `<MACHINE> <ROLE> #<id> (<topic>)` display name. Example content
(synthetic, not a real session):

```
ปิด PR #42
```

## The no-op rule

On every invocation (other than `--show`) the script trims the requested
topic to 40 chars, then compares it against the recorded value:

| requested vs. recorded | effect |
|---|---|
| same, no `--force` | prints `unchanged: <topic>`, exits 0, sends **no** keys |
| different, or no record yet | sends `/rename ...` as before, then writes the record |
| `--force` | sends regardless of the comparison, then writes the record |
| no `$TMUX` | prints the would-run line, exits 0 — **never writes the record**, because nothing was actually applied (see Guards below) |

This is what makes it safe to call routinely: `/session-worktree` and
`/session-close` now call it on every run, and it is silent
(`unchanged: ...`) on the overwhelming majority of those calls because the
session's topic usually hasn't drifted since the last send.

`--show` is read-only: it prints `recorded: <topic>` (or `recorded: (none)`
/ the no-session-id variant) and never touches the pane or the file.

## Guards (unchanged from the original script, still load-bearing)

- **No `$TMUX`** (Windows phase-1, a plain terminal) → prints what *would*
  run and exits 0. Never a hard failure — the CEO can `/rename` manually.
  Because nothing was actually applied in this branch, the record is left
  untouched: a later call with the same topic will print the would-run line
  again rather than falsely claiming `unchanged`.
- Topic is still trimmed to 40 chars so the mobile app's session list stays
  scannable.

## Recovery when a resume wipes the name out of band

A `claude -r` / session resume is documented to reset the Claude display
name to its default — the record in `state/locks/<role>-<id>.topic` does
**not** know this happened, so the next ordinary call (same topic as before)
will report `unchanged: <topic>` and skip sending, even though the actual
displayed name has reverted. Two ways to resync:

1. **Check first:** `bash scripts/session-rename.sh --show` — read-only,
   confirms what this script *thinks* is set (it cannot see the actual live
   display name; only the CEO or the mobile app can).
2. **Force it back:** `bash scripts/session-rename.sh --force "<topic>"` —
   resends unconditionally and refreshes the record, regardless of whether
   the requested topic matches what's on file.

`/session-open` step 3 also calls this script as part of every fresh
charter, so a brand-new session always gets a correct first send (there is
no prior record to falsely match against).
