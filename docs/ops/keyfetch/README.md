# keyfetch — one file per provider, the flags that worked

Skill: `.claude/skills/CTO_Procedure_KeyFetch/SKILL.md` · script: `scripts/keyfetch/capture_key.mjs` ·
sink: `tools/infisical_setup.py put` (value on stdin only).

The default write identity is `keyfetch-writer` (org `no-access`, project `member`
only for `config/keyfetch-writer.yaml`). See [seat setup, mint and revoke](infisical-setup-identity.md).
Mint a one-day client secret immediately before a run and revoke after the last put verifies.

Each `<provider>.md` here records, after the first successful run: the console deep link (the key page),
`--tab`, `--click`, and either `--match` + `--field` (wire) or `--dom` (page), plus the provider's expiry and
scope quirks. The next key on that provider is a replay of those flags — no exploration, no model.
No file here ever holds a value, a last4, or a screenshot.

**Copying a key that already sits in Infisical into a second project** (no provider page involved):
`node scripts/infisical/copy_secret.mjs http://127.0.0.1:9281 --from <Project>:<env>:<name-regex> --to <Project>:<env>:<NAME> --comment … --meta provider_name=… --meta console_url=… --meta scope=… --meta expires=…`
borrows the CEO's session from the Browser Home `infisical`, needs exactly one source name, refuses an existing target and any
Org-Infra target, writes `source` / `rotate_with=source` metadata and prints only MATCH or MISMATCH. Run `--dry` first and
put its match line in the brief: on 2026-10-12 (task-5b2a7baa) the dry run showed Org-Infra/prod holds no secret at all.

**Finding where a key already sits** (before any copy or create, §34 rule 1):
`node --experimental-websocket scripts/infisical/copy_secret.mjs http://127.0.0.1:9281 --find '/FAL/i'`
walks every project the CEO's session sees, every env and every folder, and writes nothing. Stdout holds one
`<Project>/<env>[/<path>]/<NAME>` line per matching shared secret, `<Project>[/<env>/<path>]: HTTP <status>` for
anything unreadable (the walk goes on, exit 13), a `scanned:` line and `values identical across matches: yes|no|n/a`
(on `no`, `value group <n>:` lines say which names share a value; equality only, compared in memory). Progress is on
stderr. Copy only on one match or `yes`: on 2026-10-12 (task-eb8bcf81) it found the only fal key in
`MoonieX-ComfyRunpod/prod/FAL_API_KEY` (22 projects, 37 envs, 0 unreadable), and the copy into MoonieX-Bedrock/prod printed MATCH.
