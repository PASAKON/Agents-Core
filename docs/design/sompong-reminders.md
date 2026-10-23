# SomPong durable reminders

`tools/sompong_reminders.py` is a model-free service independent of the COO
session. It reads LungNote every 30 seconds and sends due reminders to the
durable inbox. SomPong reads the reminder and uses its own `send` tool.

The COO creates an open todo with an explicit timezone-aware `due_at` and
text containing `[SomPong` (for example `[SomPong]` or `[SomPong · CEO]`).
The text must say **which chat to send to**, as well as what to say. All
examples here are synthetic:

```text
[SomPong] Send “check the sample notice” to the test chat. repeat:10,15@09:00
[SomPong · CEO] Send “check the sample schedule” to the test chat. repeat:last-1,last@09:00
```

Use one whitespace-delimited `repeat:<days>@<HH:MM>` token, without trailing
punctuation. Days are 1–31, `last`, or `last-1`, comma-separated. Time is
Asia/Bangkok. A nonexistent day (such as April 31) is skipped. A bad token
is logged once per todo id and treated as one-shot. Without a token the
todo is one-shot. The service does not close todos.

One-shot reminders more than 72 hours overdue are recorded as expired.
Repeating reminders that old skip to the next occurrence after now without
waking. After an accepted repeat, `due_at` and `due_text` advance to the next
occurrence strictly after the fired deadline. These are the only LungNote
fields written. Updates compare the original due time and text and require
the todo to remain open, so a concurrent COO edit is not overwritten.

The event goes to `POST http://172.18.0.1:8644/v1/wake`, authenticated with
`Authorization: Bearer $SOMPONG_EA_WAKE_KEY`:

```json
{
  "event_id": "reminder:synthetic-todo:1793325600",
  "message_id": "reminder:synthetic-todo:1793325600",
  "platform": "line",
  "chat_type": "dm",
  "target": "reminder",
  "sender_id": "reminder",
  "sender_name": "ตัวเตือนตามนัด",
  "role": "reminder",
  "ts": 1793325600,
  "text": "[เตือนตามนัด · todo synthetic-todo · ครบกำหนด 2026-10-30 09:00 TH] [SomPong] Send the synthetic notice to the test chat."
}
```

The event key uses the todo id and due epoch seconds. Every payload id must
match the inbox ID_RE and text is limited to 20,000 characters; oversized
or invalid payloads are rejected locally, not truncated. More than five
minutes late adds ` · ช้า N นาที` (whole elapsed minutes) before the closing
bracket. The role is always `reminder`, which the inbox treats as family;
even a `[SomPong · CEO]` tag grants no CEO rights.

202 is durably recorded before attempting a repeat PATCH. A lost response
can safely be retried using the same inbox event id. Network failures and
5xx retry next pass. 400/413/422 are recorded as `rejected:<status>` and
never retried. Other unsuccessful HTTP responses remain retryable.
A failed PATCH retries from the accepted ledger entry without another wake.

The ledger is `/var/lib/sompong-reminders/ledger.jsonl`, with fields
`key`, `todo_id`, `due_at`, `at`, `status`. `key` is the required public
deduplication identifier, **not a credential value**. Neither credential
values nor todo text are persisted or logged. Invalid repeat warnings also
use ledger entries so they are not repeated after restarts. Corrupt ledger
data fails closed and requires operator repair; do not delete accepted
entries, since deletion can replay one-shot reminders. A process lock keeps
manual `fire-once` from racing `serve`.

## Install and operations

From a root-owned checkout whose ancestors and runtime sources are not
group- or world-writable:

```sh
sudo bash scripts/install-sompong-reminders.sh install
sudo bash scripts/install-sompong-reminders.sh status
sudo journalctl -u mooniex-sompong-reminders
```

The installer renders `@ROOT@` in the unit template, creates the
`sompong-reminders` system account, enables boot startup, and starts the
service. This is a long-running service, not a timer. Root fetches LungNote-MCP
prod and MoonieX-SomPong prod via nested Infisical runs with the Contabo
identity. `cmd_run` merges inherited environment with project secrets;
the inner project wins if names overlap. It then execs `setpriv` to remove
root identity, supplementary groups and capabilities before running the tool.
No dotenv file is loaded and no credentials are written to disk.

`ProtectSystem=strict`, `ProtectHome`, `NoNewPrivileges`, and a private tmp
directory restrict the process. `ExecStartPre` creates and owns the ledger directory (no `StateDirectory=`: it would be re-owned to root before `ExecStart`), and
startup restores its ownership after systemd's root bootstrap ownership
handling. `Restart=always` recovers crashes. Monitor repeated
`status=pass-failed`, `status=patch-retry`, or unsuccessful HTTP statuses.

For a read-only pass, invoke `tools/sompong_reminders.py list` under the same
environment and service identity. Output contains only id, due_at and action.
`fire-once` performs one pass. Do not run it alongside the installed service.
Uninstall with `sudo bash scripts/install-sompong-reminders.sh uninstall`;
the account and ledger are retained to prevent replay on reinstall.

## COO acceptance test (deployment operator)

1. In a designated test chat, create a synthetic tagged todo due two minutes
   ahead. Its text must instruct SomPong to send a harmless test message to
   that chat. Confirm `list` does not show it before it is due.
2. Confirm the service logs a 202 within one polling interval after the due
   time, the ledger contains one accepted entry, and SomPong sends the message
   once. Delivery latency may include the session's own processing time.
3. Create another test todo two minutes ahead. Run
   `sudo systemctl restart mooniex-sompong` before it is due. Verify the
   independently running reminder service queues it and the resumed session
   delivers it once. To exercise actual offline queuing, an operator may keep
   the test session stopped through the due time, then start it.
4. Restart `mooniex-sompong-reminders` and confirm no duplicate delivery.
   Test a repeat separately and verify both due fields advance while it stays
   open. Clean up the synthetic todos through the normal COO workflow.

These live checks are deliberately not run by the implementation worker.
The offline test suite uses synthetic values, fake HTTP and an injected clock.
