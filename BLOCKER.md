# BLOCKER task-5b2a7baa
Org-Infra/prod holds no secret at all, so there is no fal key there to copy into MoonieX-Bedrock/prod FAL_API_KEY. Which project, env and name is it?

**What is blocking.** `copy_secret.mjs --dry --from 'Org-Infra:prod:^FAL'` borrowed the CEO's session (signed in), walked Org-Infra/prod
and listed every folder. Result: one env (`prod`), exactly the 7 §3b folders (`/ /dns /deploy /repo /net /db /vault`) and
**0 names in each**. A control with the same session and listing on MoonieX-Bedrock/prod returned `1 names`, so
the listing works. Per the brief I stopped: nothing written, steps 3–4 not run, FAL_API_KEY not created. **The Lumina Skies
sound batch cannot run yet.**

**What is done.** `scripts/infisical/copy_secret.mjs` plus 17 node tests (17/17 on node 22 and node 20, 3 of 3 planted bugs caught), a
pytest wrapper, the keyfetch README line and the KeyFetch Field note are committed on this branch. The Browser Home `infisical` was quit
(profile and login kept). No value, length, last 4 or token was printed. Full report: `docs/reports/task-5b2a7baa/REPORT.md`.

**What I need.** The real `<Project>:<env>:<name-regex>` of "MoonieX's fal key". Then the run is:
1. `(cd /opt/MoonieXHQ/Projects/MoonieX/Console && node scripts/relay-home.mjs launch infisical)`
2. `node --experimental-websocket scripts/infisical/copy_secret.mjs http://127.0.0.1:9281 --from '<P>:<env>:<regex>' --to 'MoonieX-Bedrock:prod:FAL_API_KEY' --dry`
   must print `source match: … (exactly one)` and `absent (HTTP 404)`
3. the brief's step 3 command with that `--from` must print `MATCH`, then the brief's step 4 must print `last4=<present>`, then `relay-home.mjs quit infisical`.

If no fal key exists in Infisical at all, a new one is a provider-side create (KeyFetch, §34 registry-first) and needs the CEO's go. This
task does not do that.
