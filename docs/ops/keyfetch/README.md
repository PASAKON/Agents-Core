# keyfetch — one file per provider, the flags that worked

Skill: `.claude/skills/CTO_Procedure_KeyFetch/SKILL.md` · script: `scripts/keyfetch/capture_key.mjs` ·
sink: `tools/infisical_setup.py put` (value on stdin only).

Each `<provider>.md` here records, after the first successful run: the console deep link (the key page),
`--tab`, `--click`, and either `--match` + `--field` (wire) or `--dom` (page), plus the provider's expiry and
scope quirks. The next key on that provider is a replay of those flags — no exploration, no model.
No file here ever holds a value, a last4, or a screenshot.

**Copying a key that already sits in Infisical into a second project** (no provider page involved):
`node scripts/infisical/copy_secret.mjs http://127.0.0.1:9281 --from <Project>:<env>:<name-regex> --to <Project>:<env>:<NAME> --comment … --meta provider_name=… --meta console_url=… --meta scope=… --meta expires=…`
borrows the CEO's session from the Browser Home `infisical`, needs exactly one source name, refuses an existing target and any
Org-Infra target, writes `source` / `rotate_with=source` metadata and prints only MATCH or MISMATCH. Run `--dry` first and
put its match line in the brief: on 2026-10-12 (task-5b2a7baa) the dry run showed Org-Infra/prod holds no secret at all.
