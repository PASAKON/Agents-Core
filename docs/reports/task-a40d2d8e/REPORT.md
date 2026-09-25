# REPORT — task-a40d2d8e — cache-cold-warn hook

## Files changed
- `scripts/hook-cache-cold-warn.py` (new) — fail-open UserPromptSubmit hook.
- `.claude/settings.json` — added the hook as the first entry in `UserPromptSubmit`, every existing hook kept.
- `tests/test_hook_cache_cold_warn.py` (new) — 9 cases, all pass.
- `.claude/skills/session-save/SKILL.md` — added a "When to park" paragraph to the rule body; promoted the 2026-09-25 field note's status.
- `docs/ops/cache-cold-guard-2026-09-25.md` (new) — thresholds, exemptions, manual test, rollback.
- `state/cache-cold/.gitignore` (new, force-added — see Notes) — `*`.
- `WORKLOG.md` (new).

## Commits
- `994fb4b2` — hook: cache-cold-warn — one blocking warning on stale >1h/>300k C-level sessions

## Tests
- ran: `.venv/bin/python -m pytest tests -q -x` → **exit 1** (stops on first failure, which is pre-existing and unrelated — see below)
- ran: `.venv/bin/python -m pytest tests -q` (full, no `-x`) → **exit 1**; **1125 passed, 2 failed, 16 skipped**
  - `tests/test_machine_doctor.py::test_detect_machine_by_unique_os_when_hostname_does_not_match` — the test's own comment says "This suite runs on Linux (Contabo, per the brief)"; this Mac is Darwin, so the os-fallback picks `macbox` instead of the expected `linuxbox`. Pre-existing, unrelated to this task (I never touched `tools/machine_doctor.py` or that test file — confirmed via `git status`/`git diff --stat` before my changes).
  - `tests/test_multihost.py::test_browser_operator_cap_reached_sets_conflict` — fails because this Mac's real free disk is 3.9GB (`disk red: 3.9 GB free < 5.0 GB floor`), which routes through the disk-floor-queue path instead of the conflict path the test expects. Pre-existing, disk-state-dependent, unrelated to this task.
- ran: `.venv/bin/python -m pytest tests/test_hook_cache_cold_warn.py -q` → **exit 0**, 9 passed.

## Manual proof (real transcript, read-only)
Ran against `~/.claude/projects/-Users-gob-MoonieXHQ-Agents-Core/be1db289-ef3b-477b-b323-86b6ce3535eb.jsonl` (live CTO session; its own idle time is ~1 min so `ORG_COLD_IDLE_MIN=0` was used to demonstrate against real, still-fresh data — its real context, 371k tokens, already clears the default `ORG_COLD_CTX_TOKENS=300000`):

```
$ env -u WORKER_TASK_ID ORG_COLD_STATE_DIR=$TMP ORG_COLD_IDLE_MIN=0 \
  bash -c 'echo "{...}" | python3 scripts/hook-cache-cold-warn.py'; echo exit=$?
idle 0h0m · context 371k tokens · เทิร์นนี้จะ re-write cache ทั้งหมดที่ราคา 2x
(API-equivalent ≈ $7.41 ที่ Fable 5.1 $20/MTok cache-write) · ตัวเลือก: /clear
(เริ่มใหม่), /session-save (พักไว้ก่อน resume แบบย่อ), หรือส่งข้อความเดิมซ้ำเพื่อไปต่อตามเดิม
exit=2

$ # same session_id, resent immediately (within default 10-min grace)
exit=0
```
File was only ever opened for read; the hook writes exclusively to its own state dir.

## Exemption markers found
- Worker: env var **`WORKER_TASK_ID`** — exported by `runners/worker_init.py` (`env["WORKER_TASK_ID"] = task_id`, line 492) on every worker spawn; the same marker `lib/notify.py` and `scripts/hook-inbox.py` already use to recognize a worker process.
- Mailbox wake prompt: literal prefix **`"[New message from "`**, from `tools/agent_transport.py`'s `_WAKE_MARKER_TEMPLATE = "[New message from {label}]"` (line 126) — this is the exact text `attempt_wake()` types into a tmux pane and submits as a real prompt.
- Slash commands: prompt starts with `/`.
- **Beyond the literal spec**: an extra exemption, `_has_pending_mail()` (non-destructive `lib.mailbox.peek`) for whenever this session's own mailbox has letters waiting. See "Facts verified" below for why.

## Facts verified
- Hook stdin fields confirmed against a real transcript AND `code.claude.com/docs/en/hooks` (fetched live): `session_id`, `transcript_path`, `cwd`, `prompt`, plus `permission_mode`/`hook_event_name` (not needed here). Exit 2 blocks + erases the prompt, stderr shown as the reason.
- **Important finding not in the task brief**: UserPromptSubmit hooks configured in the same settings array run **in parallel**, not sequentially — confirmed via the same doc fetch. This means array placement gives no ordering guarantee: if `hook-cache-cold-warn.py` blocks a prompt, `hook-inbox.py` (also on UserPromptSubmit) can still run in the same tick, destructively drain the session's mailbox via `lib.mailbox.drain()`, and have its own stdout discarded along with the rest of the erased turn — losing a letter that was never actually the wake-marker prompt itself. I added the mailbox-peek exemption (`_has_pending_mail()`) to close this gap for every prompt, not just the literal wake-marker text, since the task's Goal section states "never eats an org letter" unconditionally.
- Transcript structure (`message.usage.{input_tokens,cache_creation_input_tokens,cache_read_input_tokens}`, `message.model`, `timestamp`) confirmed against a real 2026-09-25 line in the live CTO session's own transcript.

## Issues / Blockers
- none — task complete. The 2 pre-existing test failures above are environment-dependent (macOS vs assumed-Linux; low real disk space) and outside this task's touches/scope; not introduced by this change.

## Notes for Reviewer
- `state/cache-cold/.gitignore` containing a bare `*` self-ignores (git matches the file against its own directory's `*` rule) — had to `git add -f` it to get it tracked at all. `state/browser-tabs/.gitignore` in this repo works around the same gotcha differently (`*.json` + `!.gitignore`), but the task explicitly specified the `.gitignore`'s content as `*`, so I kept that content and force-added instead of changing the content to self-exempt.
- The task's Field-notes rewrite instruction said verbatim to set the status to `` `promoted (CEO ruling 2026-09-25)` ``, which I did exactly. The repo's pre-commit skill-lint (`cto-merge-checklist`) flagged this as `field-note-malformed` because its canonical regex only accepts a bare `pending|promoted|rejected|superseded` token, not an annotated one — the lint explicitly says "this is a lint, not a gate — it does not block authoring", and did not block the commit. Followed the task's literal instruction over the lint; flagged below.

## Skill learning
- WRONG [cto-merge-checklist §field-note-format] : the canonical field-note regex (`... · status: pending|promoted|rejected|superseded`) rejects an annotated status value like `promoted (CEO ruling 2026-09-25)`, even though a CEO ruling is exactly the kind of thing worth recording in-line rather than as a separate note · evidence: `git commit` output on sha `994fb4b2`, `.claude/skills/session-save/SKILL.md:174` · fix: either the regex should allow a trailing parenthetical on `promoted`, or the convention should be "status: promoted" with the ruling reference moved into the evidence clause instead.
- MISSING [dev-spawn-protocol or a hooks-authoring skill §UserPromptSubmit] : nothing in the org's own hook-authoring guidance (nor the task brief) flagged that hooks in the same settings array execute in PARALLEL rather than sequentially — this is easy to get wrong when writing a new blocking hook that must coexist with `hook-inbox.py`'s destructive mailbox drain on the same event · evidence: WebFetch of `code.claude.com/docs/en/hooks` this session, `scripts/hook-cache-cold-warn.py`'s `_has_pending_mail()`.
- COSTLY [no owner] : figuring out that array order does not protect against `hook-inbox.py`'s drain (i.e. that a plain wake-marker-text exemption alone was insufficient) took a live WebFetch plus re-reading `lib/mailbox.py` and `scripts/hook-inbox.py` end to end · evidence: this session's transcript · prevented by: a one-line note in whichever skill owns hook-authoring guidance stating "UserPromptSubmit hooks run in parallel; never assume array order = execution order."
