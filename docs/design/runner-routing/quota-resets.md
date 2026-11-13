# Quota sources and reset notifications

The existing quota snapshot timer runs `tools/quota.py --snapshot`. No new timer,
model call is required.

New hub events for codex, agy-gemini and agy-claude send a best-effort silent `quota_reset` email via `email_ceo`; Claude keeps its monitor email, and failures are logged without stopping snapshots (requires Console kind/cap/dedupe support).

| Bucket | Preferred source | Fallback |
| --- | --- | --- |
| codex | `/opt/usage/codex-usage.json`, `observed_at` age >= 0 and < 30 minutes | Existing newest usable rollout search |
| claude | `/opt/claude-usage-monitor/usage.json` | Existing fetch error behavior |
| agy-gemini | `agy -p /usage`, Gemini Models group | Existing fetch error behavior |
| agy-claude | `agy -p /usage`, Claude and GPT models group | Existing fetch error behavior |

Codex's optional `quota_sources.codex.feed_path` overrides the feed path; the
configured SSH host applies to both feed and rollout reads. Invalid feeds also
fall back. Feed utilization is percentage used; window_minutes maps >=10080 to
weekly and <=1440 to daily, exactly as for rollouts. Plan type is retained in
snapshots/history wherever the provider supplies it.

Before appending history, `quota_reset.process` compares each bucket with its
previous row in `state/reports/quota-history.jsonl`. A reset occurs when usage
drops at least 20 percentage points, a reset deadline advances by more than one
day while the old deadline is still in the future, or two known plan types
differ. Missing plan metadata is not an upgrade. Error rows are ignored. Weekly
raw usage takes precedence over configured bonus-adjusted usage. Weekly is
checked first, then daily; one event is emitted per bucket.

Events contain bucket, from_pct, to_pct, plan_type, resets_at and reason. They
are written with `lib.db.log_event(conn, None, "quota_reset", "quota_reset", payload)`
and the same payload is appended to `state/reports/quota-resets.jsonl`.
Bucket plus new resets_at is the dedupe key (including null deadlines).
A local journal lock and a PostgreSQL transaction advisory lock serialize
publication. Hub lookup prevents duplicate hub events after journal loss.
Publication errors stop history advancement so the next timer run can retry.

After publishing resets, the router's in-process quota cache is cleared and
`host_queue.drain()` runs once for the batch. `budget_queue.drain()` is called if
available; budget_queue currently has no drain. The existing host drain retains
its spawn limit. Normal queue polling remains the recovery route if draining
fails after publication; the event is not published twice.

Agents can read the shared hub's `quota_reset` events or view the latest local
event for each bucket:

```sh
bash scripts/hub/org-python.sh tools/quota_reset.py last [--bucket codex]
```
