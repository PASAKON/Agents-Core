---
name: ALL_Rules_Secrets
kind: rules
description: "RULES — One rule set for every credential: where it lives, its name, scope and expiry, how it is read, and what a leak sets off. Trigger on /ALL_Rules_Secrets, \"key หลุด\", \"สร้าง key\", \"API key\", \"secret\", \"rotate\", \"revoke\", \".env\". Do NOT use for the fetch steps (CTO_Procedure_KeyFetch) or the login (relay-login)."
owner: CTO
audience: [all]
created_by: agent
author: {role: security_engineer, date: "2026-10-27"}
improved_by: []
aka: []
---

# Secrets: one home, named, scoped, expiring; a leak is rotated

These rules bind every session and every worker on every machine whenever a credential is created, stored,
read, rotated, revoked or seen: API keys, tokens, passwords, client secrets, private keys and webhook
secrets. They gather what the CEO ruled into one place: `CLAUDE.md` §Secrets (CEO 2026-09-25/26), the design
`docs/design/secrets-infisical/PLAN.md` (approved 2026-09-25, "ok ทั้ง 5"), Q-20261026-0814-e94a (a C-level
creates or deletes a provider key itself, through KeyFetch) and Q-20261026-1118-4d3d (stay on the free plan;
each repo's project is the wall). This skill does not decide who approves a secret action. That is
`ALL_Rules_Approvals` rule 2. The steps for fetching a key are in `CTO_Procedure_KeyFetch`. Draft IRON
section: `docs/plans/hqsecurity-rules-draft/IRON-65.md`.

## Rules

1. **HARD — One home per key: the Infisical project named after its GitHub repo.** Infisical project name
   = repo name (`MoonieX-ClaudeFlow`), plus `Agents-Core` for the org runtime (PLAN §3). A new key goes into
   its own repo's project (e94a). `Org-Infra` holds only org-wide keys that change an account (DNS, deploys,
   repo admin, tailnet, the Postgres superuser; PLAN §3b). **Only the CEO enters Org-Infra values**, by hand
   in the Infisical web page. `capture_key.mjs` and `infisical_setup.py put` refuse it, and nothing moves into
   it while we are on the free plan (4d3d: "ฟรี: แยก project ต่อ repo เป็นกำแพง, keyfetch-writer แทนที่นั่ง setup
   (แนะนำ)"). Never create a new `.env` and never add a line to an existing one: the target home is
   Infisical, read through rule 5.
   **Why hard:** scope — on the free plan the project is the only permission wall, so a writer on Org-Infra
   could read every org-wide credential. A `.env` is a second copy that never rotates: PLAN §1 finding 5 counted
   9 live env files and 10 archived copies on Contabo alone.
   IRON §34 item 5 still says "in every project including Org-Infra" (e94a, the morning of 2026-10-26). 4d3d
   replaced that at 18:53 TH the same day, and the IRON-65 draft amends it.

2. **HARD — A key is named and labelled before it exists.** Three names, three places (PLAN §4):

   | Where | Pattern | Example |
   |---|---|---|
   | Variable (Infisical secret name) | `<PROVIDER>_[<WHICH>_]<KIND>[_<ACCESS>]`, KIND and ACCESS from the closed lists in §4b | `FAL_BILLING_API_KEY_RO` |
   | Provider page | `<brand>-<project>-<env>-<access>-exp<YYYY-MM-DD>[-<host>]`, ≤40 characters | `ag-core-prod-ro-exp2027-10-14` |
   | Infisical metadata | comment = purpose; `provider_name` `console_url` `scope` `expires` `owner` required, `created` stamped by `put` | `scope=BILLING-preset` |

   A provider with no name field still gets a §4d name in `provider_name`. The metadata is then the only
   place it is recorded. The KeyFetch gate (`scripts/keyfetch/keyfetch_lib.mjs` `checkKeyMeta`) refuses with
   exit 64 any planned write that lacks these. It checks before anything is clicked, so a refusal never
   leaves a live key at the provider. `put` lints the variable name and refuses a new secret without the
   metadata.
   **Why hard:** safety — when a key leaks, the person revoking it must find the right one in the
   provider's list. When it expires, someone must see the date first. PLAN §1: one variable name held three
   different bots' tokens (finding 1), and three keys expired unseen (finding 7).

3. **HARD — Least privilege, one key per project.** Use the smallest scope the provider offers: one zone,
   one repo, one bucket, one preset. Use read-only (`ro`) unless the job writes. Use `admin` only for a key
   that creates or deletes keys or touches billing. Set a spend cap when the provider offers one. Each project
   gets its own key. Never share one value across projects: a provider that can issue several named keys
   issues one per project. A value that exists only once (a bot token) lives in the project that owns it, and
   the other project calls that project's API (ADR 0028). Where that API does not exist yet, the copy carries
   tag `shared` and `also_in` metadata. A wider key carries tag `wide` and `why_wide`.
   **Why hard:** safety — PLAN §1 finding 2: at least seven values sat in two projects each. One leak hits
   both projects at once, and spend cannot be traced to a project.

4. **HARD — Every key that can expire does.** Set the expiry at the provider whenever it offers one. The
   default is one year. Org-Infra uses ≤90 days for `admin` and ≤1 year for `rw`/`ro` (PLAN §3b rule 3).
   `expires` is the provider's date, and it equals the `exp` in the page name. A provider that offers no
   expiry gets the literal `expires=none-offered`. The page name's `exp` is then our rotate-by date, and the
   report says so (the script prints that line).
   **Why hard:** safety — a leaked key with no expiry keeps working for whoever holds it. PLAN §1 finding 6
   lists seven leaked keys that stayed live for weeks.
   *How the date reaches the CEO (advice, partly UNBUILT):* the expiry radar (PLAN §6 phase 5) is
   **UNBUILT**. It will read `expires` (or, for `none-offered`, the `exp` in `provider_name`) from Infisical
   metadata, names only. It will then file a LungNote to-do 14 days before the date. Until it exists, the
   C-level who ran the fetch files that to-do by hand. The text is
   `[key-expiry] rotate <project>/<env> <NAME> (expires <date>)` with `due_at` = the date minus 14 days. The
   SessionStart deadline hook then shows it from 7 days ahead. `tools/email_ceo.py deadlines` (kind
   `deadline`) puts it in the CEO's 08:00 digest when it is due within 24 hours.

5. **HARD — A secret is read only by the process that uses it, through Infisical.** Use `infisical run`,
   `infisical_setup.py run <project> <env> -- <cmd>`, or the org wrappers `scripts/hub/with-org-db-env.sh` and
   `scripts/hub/org-python.sh`. Never read `/etc/infisical/*` (a machine identity's credential, root-only),
   `/proc/*/environ`, `ps e…`, or `docker inspect`/`exec` env of a service. Never `infisical export` to disk
   (tmpfs only, PLAN §5). Never `echo`, `cat`, `printenv` or `grep` a secret variable. A stub or fake binary
   that runs under a wrapper prints its argc only, never its argv or environment.
   **Why hard:** irreversible — a value in tool output is in the transcript for good. On 2026-10-26 a fake
   `psql` under `with-org-db-env.sh` received the real `ORG_DB_URL` through the wrapper's Infisical fallback,
   and its log was printed. The hub password had to be rotated (PH ProjectTrack #40fefb4e).

6. **HARD — A worker or browser operator fetches a key only through `CTO_Procedure_KeyFetch`.** The CEO
   logs in through the relay (`relay-login`, IRON §60). The value goes from the page straight into Infisical
   (`put --stdin`). No model sees it: no screenshot, no DOM read and no tool output once the key exists. Learn
   a page on a dummy key, or with a listener that prints names and types only. Every fetch leaves its replay
   in `docs/ops/keyfetch/<provider>.md` (`BROWSER_OPERATOR_Protocol_Playbook`). A value someone pasted or
   typed to you is not a fetch. It is a leak: rule 7.
   **Why hard:** irreversible — KeyFetch rule 1. PLAN §1 finding 6: seven keys had to be rotated after
   chat pastes and a screenshot.

7. **HARD — A leak is rotated forward, at once.** It counts as a leak when the value, or enough of it to
   search for, has been in any of these places: a chat; a screenshot or screencast; a log or tool output; a
   commit on any branch (pushed or not, reverted or not; Agents-Core and Agents-Rules are public, so a push
   is a publication); a Run or question card; a mailbox letter; a prompt or brief; a transcript; any file
   outside Infisical. Then do these steps in order:
   - (1) Tag the secret `leaked` in Infisical (the §4c status tag).
   - (2) Mint a new key at the provider through KeyFetch, with a new `exp` in its name.
   - (3) Put it into Infisical (`put` updates the secret in place).
   - (4) Verify the consumer: restart it from Infisical, check that it is green, and run one status-only
     authenticated call.
   - (5) Revoke the old key at the provider (rule 8).
   - (6) Look back: list every place that held the value (sessions, transcripts, repos and forks, cards, logs,
     Drive) and say which ones can be cleaned and which cannot. Write one registry Changelog line (IRON §34
     item 2).

   On the free plan Infisical keeps no version history, so a value that was overwritten is gone. Mint
   first and never overwrite a value that cannot be issued again. Report the leak by place (`path:line`,
   scanner rule id), never by value, prefix or last4 (`CTO_Procedure_KeyFetch` rule 7).
   **Why hard:** irreversible and safety — a leaked value cannot be un-leaked. Rotating is the only fix, and
   every hour it waits is an hour someone else can use the key.

8. **HARD — Revoke only after the replacement is verified, and tell the other lane first.** The old key
   stays live until its consumer runs green on the new one. If another lane's service uses the key, tell
   that PH or C-level (`send_to_cxo`) and wait for their consumer to go green. Then revoke. Exception: a key
   that is being abused right now (spend rising, unknown calls in the provider's log) is revoked first.
   Accept the outage, tell the owner, and say so in the report.
   **Why hard:** irreversible — a revoked key cannot be restored, and revoking first takes a service down
   with nothing to replace the key.

9. **HARD — Leak guards stay on, and none is bypassed.** Never use `--no-verify`, `SECRET_ENV_GUARD=off`
   (except a repair the hook's own docstring allows) or `ALLOW_NO_GITLEAKS=1` to get a commit or command
   through. A guard that fires is either a leak (rule 7) or a false positive, which you report by place.
   Before pushing a branch of a public repo, run `gitleaks git --no-banner --redact` on it.
   **Why hard:** safety — each guard is the last check before a value becomes public. State on 2026-10-27:

   | Guard | Where | State |
   |---|---|---|
   | gitleaks pre-commit | `scripts/install-git-hooks.sh` → `.git/hooks/pre-commit` (`gitleaks protect --staged --redact`) | BUILT; warns when gitleaks is not on PATH |
   | gitleaks pre-push | none in the repo | **UNBUILT** |
   | gitleaks in CI | `.github/workflows/ci.yml` job `gitleaks` | BUILT |
   | GitHub secret scanning + push protection | Agents-Core, Agents-Rules (both public) | **OFF**: `gh api repos/PASAKON/<repo>` shows `secret_scanning` and `secret_scanning_push_protection` = `disabled`. Free on public repos; turning it on is a repo-settings change for the CTO/CEO |
   | Session hook | `scripts/hook-secret-env-guard.py` | BUILT for `/proc/*/environ`, `ps e`, docker read verbs on chatudo, and Infisical `/chatudo` reads. **UNBUILT** for `/etc/infisical/*` reads |
   | Run card redaction | `tools/ask_run.py` (refuses a secret-shaped value, exit 2; the hub answers 400 `secret_shaped_value`) | BUILT |
   | KeyFetch metadata gate | `scripts/keyfetch/keyfetch_lib.mjs` `checkKeyMeta` | BUILT 2026-10-27 |
   | `put` gate | `tools/infisical_setup.py` (Org-Infra refused, §4b name lint, §4c metadata on a new secret) | BUILT |

## Leak report (the format)

```
LEAK · <project>/<env> <NAME> · seen in: <place>, <place> · found <YYYY-MM-DD HH:MM TH> by <session>
tagged leaked · new key <provider-page name> · consumer <service> green <time> · old key revoked <time>
look-back: <who/what saw it> · cleanable: <…> · not cleanable: <…> · Changelog line: <link>
```

## When the CEO changes a rule

Write his words verbatim here, keep the old line as `[SUPERSEDED <date>]` with his message as the evidence,
and change `ALL_Rules_Approvals` rule 2, `CTO_Procedure_KeyFetch` and IRON in the same commit if they
repeat it.

## Field notes
