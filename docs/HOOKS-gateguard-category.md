# GateGuard Category-Bypass Hooks

Mooniex wrapper around ECC's `gateguard-fact-force` hook. Caches fact
presentation at the **category** level so batch operations (wiki migration,
config edits, memory writes) only trigger the fact gate once per session
instead of once per file.

## How it works

1. **Pre hook** (`hook-gateguard-category-pre.py`) runs before ECC GateGuard on every `Edit`/`Write`/`MultiEdit`. If all file paths in the tool input belong to already-presented categories, it emits `permissionDecision: allow` and ECC is never reached.
2. **Post hook** (`hook-gateguard-category-post.py`) runs after a successful `Edit`/`Write`/`MultiEdit`. It marks the file's category as presented so future edits in that category are auto-allowed.
3. Session state lives at `~/.claude/state/mooniex-gateguard-<session>.json` and expires after 30 minutes of idle (matching ECC's `SESSION_TIMEOUT_MS`).

## Install

Add the two entries below to `~/.claude/settings.json`. The Mooniex pre hook
**must come before** any ECC plugin hooks in the `PreToolUse` array so it can
short-circuit before ECC fires.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/gob/MoonieXHQ/Agents/Core/scripts/hook-gateguard-category-pre.py",
            "timeout": 5,
            "statusMessage": "GateGuard: category check..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/gob/MoonieXHQ/Agents/Core/scripts/hook-gateguard-category-post.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Merge these arrays with any existing `PreToolUse`/`PostToolUse` entries — do
not replace them. The Mooniex pre entry must be **first** in `PreToolUse`.

## Verify ECC is still active

After editing `settings.json`, confirm the ECC plugin entry (loaded via
`enabledPlugins`) is still present. The Mooniex pre hook only short-circuits
when a category is already presented; on the first edit of any category, ECC
still fires normally.

## Smoke test

1. Open a fresh Claude Code session.
2. Edit any file under `/Users/gob/MoonieXHQ/Agents/Wikis/` — ECC fact gate fires (expected).
3. Edit a second file under `/Users/gob/MoonieXHQ/Agents/Wikis/` — gate should NOT fire again.
4. Check `~/.claude/state/mooniex-gateguard-*.json` to confirm `wiki_edit` appears in `categories`.

## Add a new category

Append a `(name, regex)` tuple to `CATEGORIES` in
`scripts/gateguard_categories.py`:

```python
CATEGORIES = [
    # existing entries...
    ("my_new_category", re.compile(r"^/Users/gob/Projects/MyRepo/")),
]
```

Order matters — the first matching pattern wins, so put narrow patterns before
broad ones.

## Disable

**Temporary (one session):**

```bash
export MOONIEX_GATEGUARD_CATEGORY_OFF=1
```

The pre hook checks this env var and returns pass-through unconditionally,
leaving ECC's behavior unchanged.

**Permanent:** Remove the two hook entries from `~/.claude/settings.json`.
