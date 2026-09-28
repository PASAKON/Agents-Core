# keyfetch — one file per provider, the flags that worked

Skill: `.claude/skills/CTO_Procedure_KeyFetch/SKILL.md` · script: `scripts/keyfetch/capture_key.mjs` ·
sink: `tools/infisical_setup.py put` (value on stdin only).

Each `<provider>.md` here records, after the first successful run: the console deep link (the key page),
`--tab`, `--click`, and either `--match` + `--field` (wire) or `--dom` (page), plus the provider's expiry and
scope quirks. The next key on that provider is a replay of those flags — no exploration, no model.
No file here ever holds a value, a last4, or a screenshot.
