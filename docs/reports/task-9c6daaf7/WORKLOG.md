# WORKLOG — task-9c6daaf7 (caveman plugin migration)

- 2026-09-25: read TASK.md, IRON-RULES.md (org wiki), scripts/install-claude-home.sh (installer mechanism), claude-home/plugins.txt + claude-home/settings.json (current state).
- 2026-09-25: `claude plugin marketplace add JuliusBrussee/caveman` — added marketplace, cloned to `~/.claude/plugins/marketplaces/caveman` (v2.7.0).
- 2026-09-25: read plugin README + `docs/technical/skills-hooks-and-plugins.md` + `skills/caveman-help/SKILL.md` + `.claude-plugin/plugin.json` for install commands, mode names, config resolution order, hook wiring.
- 2026-09-25: `claude plugin install caveman@caveman` — installed (scope: user), verified enabled via `claude plugin list`.
- 2026-09-25: measured SessionStart injection size: standalone hook (no SKILL.md, mode=lite fallback) = 1828 chars (~457 tokens) vs plugin hook (SKILL.md present, mode=ultra, filtered) = 5827 chars (~1457 tokens). Injection got bigger, not smaller — noted in REPORT.md.
- 2026-09-25: edited `claude-home/plugins.txt` — added `marketplace caveman=JuliusBrussee/caveman` + `plugin caveman@caveman` rows.
- 2026-09-25: edited `claude-home/settings.json` — removed the two standalone caveman hook entries (SessionStart `caveman-activate.js`, UserPromptSubmit `caveman-mode-tracker.js`), kept the wiki-pull SessionStart hook and `allowlist-notify.mjs` UserPromptSubmit hook untouched; added `caveman@caveman` to `enabledPlugins` and `caveman` to `extraKnownMarketplaces`; validated JSON with `python3 -c "import json; json.load(...)"`; confirmed `"model": "opus[1m]"` line unchanged.
- 2026-09-25: `git rm` the four standalone files: `claude-home/hooks/{caveman-activate.js,caveman-config.js,caveman-mode-tracker.js,caveman-statusline.sh}`. Grepped repo for other references — only `scripts/statusline.sh` still references `caveman-statusline.sh` (task says leave that file alone; it already has a graceful `[ -f ... ]` guard so the badge silently degrades to empty — flagged in REPORT.md).
- 2026-09-25: set `~/.config/caveman/config.json` to `{"defaultMode":"ultra"}` (was `{"defaultMode":"lite"}`). No installer mechanism exists for seeding arbitrary `~/.config/<tool>` files (checked `scripts/install-claude-home.sh`'s `ENTRIES` array — only covers `~/.claude/*`), so this stays a manual step, documented in the ops doc.
- 2026-09-25: ran 3 headless Thai smoke tests (`claude -p ... --model claude-sonnet-5`), replies pasted verbatim into REPORT.md. Confirmed `~/.claude/.caveman-active` read `ultra` during the runs.
- 2026-09-25: added `## Report length (CEO 2026-09-25)` block (add-only, after the existing Skill learning section) to `roles/cto.md`, `roles/cmo.md`, `roles/cgo.md`, `roles/cfo.md`.
- 2026-09-25: wrote `docs/ops/caveman-plugin-2026-09-25.md`.
- 2026-09-25: ran test suite, results in REPORT.md.
