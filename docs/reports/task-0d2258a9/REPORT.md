# REPORT task-0d2258a9

## Summary

Implemented bidirectional messaging and discovery between Claude sessions and Antigravity (AGY CLI on `contabo`, `mac`, `winbox`, and the AGY Desktop App on `mac`), reusing `tools/agy_card_run.py`, `tools/mail_wake.py`, `tools/agy_takeover.py`, `tools/send_to_cxo.py`, `lib/mailbox.py`, and `lib/notify.py`:

1. **`tools/send_to_agy.py`**:
   - `list [--host all|mac|contabo|winbox] [--limit N] [--local] [--json]`: discovers every AGY conversation across `mac`, `contabo`, and `winbox` (`box`, `host`, `conversation_id`/`uuid`, `cwd`, `last_activity`, `title`/`first_user_line`, `app_vs_cli` (`App` vs `CLI`)). Scans local `state/agy-sessions/*.json`, `state/ph-brains/*.json`, `~/.gemini/antigravity/{brain,conversations}` (`App`), and `~/.gemini/antigravity-cli/{brain,conversations}` (`CLI`), and probes remote hosts in parallel over SSH using `HOST_MAP` (`contabo -> mooniex-vps`, `mac -> mac`, `winbox -> winbox`).
   - `send <box|uuid> "<msg>" [--from <role>-<sid>] [--host <host>]`: writes the letter to `state/inbox/<box>/` (using the same letter envelope shape as `tools/send_to_cxo.py`), updates `state/agy-sessions/<box>.json` (`last_from`, `last_from_host`), logs the hop to the CTO event log (`state/logs/cto.log`), and resumes the conversation detached **on its own host** (`subprocess.Popen(..., start_new_session=True)` locally, or over `ssh mac` / `ssh winbox` / `ssh mooniex-vps` remotely) with `agy -p "<prompt>" --conversation <uuid>`. The prompt names the sender and tells AGY how to reply (`bash scripts/hub/org-python.sh tools/send_to_cxo.py <from> "<reply>"` and cross-host `bash scripts/hub/org-python.sh tools/send_to_agy.py reply <from> "<reply>" --from <box>`).
   - `reply <to_box> "<reply>" [--from <agy_box>] [--host <host>]`: AGY -> Claude reply command that works from an AGY conversation on `contabo`, `mac`, or `winbox`, resolves `<role>-<sid>` or bare `<role>`, determines the target Claude session's host (local locks/tmux, recorded `last_from_host`, or `contabo` for `cto`), writes the letter locally or over SSH, and wakes the recipient pane via `tools/mail_wake.py`.
   - `live-sessions`: renders `tools.live_sessions` output merged with live unparked AGY rows (`kind: "agy"`, status `agy`) in text, `--json`, and `--id <sid>` modes.
2. **`scripts/live-sessions.sh`**:
   - Delegates read queries to `bash "$ROOT/scripts/hub/org-python.sh" -m tools.send_to_agy live-sessions "$@"` (with `ORG_LIVE_SESSIONS_NO_AGY=1` fallback to `tools.live_sessions`), adding `agy` rows so senders can see and address AGY sessions from `bash scripts/live-sessions.sh`.
3. **AGY -> Claude reply route fixes (`tools/agy_card_run.py`, `tools/mail_wake.py`, `tools/send_to_agy.py`)**:
   - `tools/agy_card_run.py`: `format_wake_prompt()` now includes explicit reply commands when waking an AGY session for a peer mailbox letter; `_call_agy_cli()` injects `AGY_CONVERSATION_ID` and `ANTIGRAVITY_APP_DATA_DIR` into the child environment.
   - `tools/send_to_agy.py`: `_spawn_detached_local_agy()` and the remote SSH runner export `CXO_ROLE`, `CXO_SESSION_ID`, `AGY_CONVERSATION_ID`, `AGY_BOX`, and `ANTIGRAVITY_APP_DATA_DIR` so `tools/send_to_cxo.py` and `tools/send_to_agy.py reply` pass `agent_transport.current_identity()` without manual env vars.
   - `tools/mail_wake.py`: `_wake()` now routes standalone registered AGY boxes (`elif (agy := handle_agy(box)) is not None:`) even when the box prefix is not a C-level/PH/worker role.

## Files Changed

- `tools/send_to_agy.py` (new): `list`, `send`, `reply`, and `live-sessions` subcommands for cross-host Claude <-> AGY discovery and messaging.
- `scripts/live-sessions.sh`: added AGY rows (`kind: "agy"`) via `tools.send_to_agy live-sessions`.
- `tools/agy_card_run.py`: added peer reply instructions to `format_wake_prompt()` and environment variables (`AGY_CONVERSATION_ID`, `ANTIGRAVITY_APP_DATA_DIR`) to `_call_agy_cli()`.
- `tools/mail_wake.py`: added fallback `handle_agy(box)` branch in `_wake()` for standalone AGY boxes.
- `tests/test_send_to_agy.py` (new): unit tests for local/remote discovery (`App` vs `CLI`), local/remote `send`, `live-sessions` rendering (`text`, `--json`, `--id`), cross-host `reply_to_claude` (`contabo`, `mac`, `winbox`), `agy_card_run.format_wake_prompt`, and `mail_wake.wake` with `subprocess`/`ssh` mocked.

## Desktop App vs CLI Investigation (Item 4)

Read-only investigation of whether `agy -p --conversation <App uuid>` on the Mac appends to a desktop App conversation and whether the App shows it live:

1. **What is proven from repository files (`tools/agy_card_run.py` lines 58–60, 289–342, 429–498, 613–645 and commit `580a1f2f`)**:
   - **Separate default `appDataDir` directories**: The Mac Antigravity Desktop App stores its conversation state and transcripts under `~/.gemini/antigravity/{brain/<uuid>,conversations/<uuid>.pb}`, whereas the `agy` CLI binary (`~/.local/bin/agy`) defaults to `~/.gemini/antigravity-cli/{brain/<uuid>,conversations/<uuid>.pb}`.
   - **Without `ANTIGRAVITY_APP_DATA_DIR`**: Running a bare `agy -p "<msg>" --conversation <App uuid>` on the Mac looks in `~/.gemini/antigravity-cli` and **does not** find or append to the Desktop App conversation unless `ANTIGRAVITY_APP_DATA_DIR=/Users/gob/.gemini/antigravity` is set (or the directories are shared). `tools/send_to_agy.py` and `tools/agy_card_run.py` now set `ANTIGRAVITY_APP_DATA_DIR=~/.gemini/antigravity` automatically whenever the target conversation is detected as `App`.
   - **Live UI vs on-disk append**: Even when `agy -p --conversation <App uuid>` writes to `~/.gemini/antigravity`, an open Antigravity Desktop App window is backed by its own running in-memory Language Server process (`/Applications/Antigravity.app/Contents/Resources/bin/language_server`, addressed via `ANTIGRAVITY_LS_ADDRESS` + `ANTIGRAVITY_CSRF_TOKEN`). As documented in commit `580a1f2f` (`"fix(agy_card_run): wake live Antigravity Desktop App sessions via agentapi send-message"`), the Desktop App only renders and executes an injected user turn **live in the open GUI window** when delivered through `language_server agentapi send-message --title "<title>" <uuid> "<prompt>"` against the App's live `ANTIGRAVITY_LS_ADDRESS`/`ANTIGRAVITY_CSRF_TOKEN`. A separate headless `agy -p --conversation <App uuid>` process appends on disk (`brain/<uuid>` / `conversations/<uuid>.pb`), which requires reloading/reopening the conversation in the App UI to see if the window was already open.
2. **What cannot be proven from Contabo files alone (verification step for the CTO on the Mac)**:
   - Because this worker runs headless on Contabo with SSH disabled by `config/agy-settings.json`, live Mac GUI reload vs lock contention between an open Desktop App window and a concurrent headless `agy -p --conversation <App uuid>` process cannot be observed directly from here.
   - **Step for the CTO on the Mac**:
     1. Run `bash scripts/hub/org-python.sh tools/send_to_agy.py list --host mac` to pick an open Mac `App` conversation UUID (`<app_uuid>`).
     2. Run `ANTIGRAVITY_APP_DATA_DIR="$HOME/.gemini/antigravity" ~/.local/bin/agy -p "ping from CLI" --conversation <app_uuid> --output-format json` while that conversation is visible in `Antigravity.app`, and check (a) whether `~/.gemini/antigravity/brain/<app_uuid>/.system_generated/logs/transcript.jsonl` appends the new turn, and (b) whether the open `Antigravity.app` window reflects the turn immediately or only after switching away and back to the conversation.

## Validation

- Ran unit tests with `subprocess`/`ssh` mocked (no `-q`):
  - `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_send_to_agy.py tests/test_agy_card_run.py tests/test_mail_wake.py tests/test_mail_wake_agy_stale.py tests/test_ph_on_mac.py` -> **129 passed**.
  - `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest scripts/test_live_sessions.py scripts/test_cxo_crosstalk.py tests/test_agy_takeover.py tests/test_identity_fail_closed_opus.py` -> **385 passed, 1 skipped**.

## Not checked / risk

- **Live SSH round-trip across `mac` and `winbox`**: In the AGY headless worker sandbox (`config/agy-settings.json`), `ssh` is on the deny list, so cross-host SSH calls (`ssh mac`, `ssh winbox`, `ssh mooniex-vps`) were verified with mocked `subprocess.run` unit tests rather than live SSH traffic.
- **Mac Desktop App live UI refresh**: As detailed under *Desktop App vs CLI Investigation (Item 4)*, whether `Antigravity.app` watches `~/.gemini/antigravity/conversations/<uuid>.pb` on disk for external `agy -p --conversation <uuid>` writes or requires switching conversations / using `language_server agentapi send-message` must be confirmed on the Mac host by the CTO.
- **`scripts/live-sessions.sh` latency when a remote host is offline**: `tools/send_to_agy.py` scans `contabo`, `mac`, and `winbox` concurrently via `ThreadPoolExecutor` with `ConnectTimeout=6` and `BatchMode=yes` so an unreachable host times out within ~6s and degrades gracefully without blocking local sessions.

## Blockers

- (none)

## Skill learning

- (none)
