# Caveman: standalone hooks → plugin, default mode → ultra (2026-09-25, task-9c6daaf7)

CEO 2026-09-25 (verbatim): "cave man เราติดตั้งตัวเต็มดีกว่านะ และปรับ mode
เป็น ตอบกระชับที่สุด เพราะฉันต้องมานั่งอ่านข้อความยาวๆ ทั้งที่เนื้อหามีนิดเดียว
ต้องการสิ่งที่เรียกว่าสรุปสั้นที่สุดเท่าที่จะเป็นได้ โดยบริบทความหมายคงเดิม"

## What changed

1. **Plugin installed** — [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) v2.7.0, via the standard two-step:
   ```bash
   claude plugin marketplace add JuliusBrussee/caveman
   claude plugin install caveman@caveman
   ```
   Declared in `claude-home/plugins.txt` (`marketplace caveman=JuliusBrussee/caveman`, `plugin caveman@caveman`) so `scripts/install-claude-home.sh` reproduces it on a fresh machine. Verify: `claude plugin list` should show `caveman@caveman ... Status: ✔ enabled`.

2. **`claude-home/settings.json`**:
   - Removed the two standalone caveman hook entries — `SessionStart` → `node "/Users/gob/.claude/hooks/caveman-activate.js"` and `UserPromptSubmit` → `node "/Users/gob/.claude/hooks/caveman-mode-tracker.js"`. The plugin's own `.claude-plugin/plugin.json` wires the equivalent `SessionStart`/`UserPromptSubmit` hooks (same script names, `$CLAUDE_PLUGIN_ROOT/src/hooks/*.js`) automatically once the plugin is enabled — no manual hook entry needed.
   - Every other hook (wiki-pull SessionStart, `allowlist-notify.mjs`/`allowlist-tracker.mjs`, GateGuard, cost-guardian, tab-guard, skill-log) is untouched.
   - `statusLine` untouched (still `scripts/statusline.sh` — see "Known regression" below).
   - `"model": "opus[1m]"` line untouched.
   - Added `"caveman@caveman": true` to `enabledPlugins` and a `caveman` entry to `extraKnownMarketplaces` (source: github, repo `JuliusBrussee/caveman`) — same shape as the existing `ecc`/`cost-guardian`/`meigen` entries.

3. **`git rm`'d** the four standalone files: `claude-home/hooks/{caveman-activate.js,caveman-config.js,caveman-mode-tracker.js,caveman-statusline.sh}` (dated 2026-04-20). Repo-wide grep after removal found no other referencing file except `scripts/statusline.sh` (see below).

4. **`~/.config/caveman/config.json`** (outside the repo — `scripts/install-claude-home.sh`'s `ENTRIES` array only covers `~/.claude/*`, there is no installer-managed place for this file) set from `{"defaultMode":"lite"}` to:
   ```json
   {"defaultMode":"ultra"}
   ```
   This is a **manual step per machine** — re-run it on winbox/Contabo if caveman is ever installed there.

## Mode names + how default resolves

Modes: `lite`, `full` (default per plugin, overridden by our config), `ultra`, `wenyan-lite`, `wenyan-full` (alias `wenyan`), `wenyan-ultra`, plus independent skills `commit`/`review`/`compress` (not intensity levels — each has its own skill).

Resolution order (highest priority first), per `skills/caveman-help/SKILL.md`:
1. `CAVEMAN_DEFAULT_MODE` env var
2. `~/.config/caveman/config.json` → `defaultMode`
3. hardcoded default `full`

## Switching mode mid-session

`/caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra|off` — sticks until changed or session end. `/caveman-help` prints the reference card without changing mode. "stop caveman" / "normal mode" also works.

## Known regression: statusline badge

`scripts/statusline.sh` (untouched, per task instructions) looks for a badge
script at `$CLAUDE_CONFIG_DIR/hooks/caveman-statusline.sh` — that was the
standalone file we just removed. The plugin ships its own
`caveman-statusline.sh`, but at `$CLAUDE_PLUGIN_ROOT/src/hooks/` (e.g.
`~/.claude/plugins/cache/caveman/caveman/<version>/src/hooks/`), never linked
into `~/.claude/hooks/`. Net effect: the `[CAVEMAN:xxx]` badge in the terminal
statusline goes silently empty (the script already guards with `[ -f ... ]`,
so nothing breaks — the SID tag still renders). Flagged for CTO; not fixed
here since the task said not to touch `scripts/statusline.sh`.

## Rollback

1. `/caveman lite` — or any mode — to change behavior for the current session only.
2. To fully revert to the standalone install:
   ```bash
   git checkout <commit-before-this-change> -- claude-home/hooks/caveman-activate.js \
     claude-home/hooks/caveman-config.js claude-home/hooks/caveman-mode-tracker.js \
     claude-home/hooks/caveman-statusline.sh
   ```
   Then restore the two `hooks.SessionStart`/`hooks.UserPromptSubmit` entries in
   `claude-home/settings.json` (see git history for the exact JSON), and either
   leave the plugin installed-but-superseded or `claude plugin uninstall caveman@caveman`
   (removes `enabledPlugins`/`extraKnownMarketplaces` entries and the
   `plugins.txt` rows by hand).
3. `~/.config/caveman/config.json` → `{"defaultMode":"lite"}` to restore the prior default (this file is not restored by git — it's outside the repo).
