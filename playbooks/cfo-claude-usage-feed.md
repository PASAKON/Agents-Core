# Playbook — CFO Claude Max usage feed

> Owner: CTO. Local launchd job on the operator Mac. Last updated 2026-06-11.

## Why this exists

Claude Max = องค์กรจ่ายก้อนใหญ่สุด (~$100–200/mo) แต่เดิม **ไม่มี telemetry ใน CFO DB**.
This feed pushes **daily utilization %** so `/admin/cfo` can show how hard the
Max seat is being worked — *without* touching the dollar ledger.

`scripts/cfo-claude-usage-feed.sh` reuses the OAuth-usage pattern from
`scripts/claude-usage-sync.sh` (the iPhone-widget feed): pull the Claude Code
token from the macOS Keychain, GET the usage endpoint, then POST **1 row/day**
into Supabase `webapp_cfo_api_events`.

## ⚠️ cost_usd is ALWAYS null — do not "fix" it

Max is a **fixed subscription** already tracked in `webapp_cfo_subscriptions`.
Putting a dollar amount on this row would **double-count** the same spend.
This row records *utilization* (percent of the rolling quota used), not cost.
The `$` lives in the subscriptions table; the `%` lives here. Keep them apart.

## The row (schema locked to `track.py`)

Field list mirrors `_post()` in `mooniex-webapp/src/lib/cfo/track.py` exactly —
do not add/rename columns here:

```json
{
  "provider": "anthropic",
  "project_key": "agents",
  "model": null,
  "agent_role": "org",
  "agent_id": "claude-max",
  "request_id": null,
  "prompt_tokens": null,
  "completion_tokens": null,
  "cost_usd": null,
  "latency_ms": null,
  "status": "success",
  "tags": {
    "kind": "subscription_utilization",
    "five_hour_pct": 46,
    "seven_day_pct": 56,
    "seven_day_opus_pct": null,
    "seven_day_sonnet_pct": 2
  }
}
```

`*_pct` come straight from the live payload (`five_hour.utilization`, etc.).
A bucket the account isn't using (e.g. Opus this week) reports `null` — expected.

## Secrets — CEO fills these once

The Agents repo has **no `.env`**. The script reads two values from
`~/.config/mooniex/cfo.env` (mode 600). It is **never committed** and the
service-role key **must never** be pasted in chat / commits / logs.

On first run with no config the script creates an empty 600 template there and
no-ops. To enable the feed, run this **one line** (paste the real key in place
of the placeholder — `printf`, not `echo`, per IRON-RULES §2 #5):

```bash
printf 'SUPABASE_URL=%s\nSUPABASE_SERVICE_ROLE_KEY=%s\n' 'https://tlokhyqpthvxabweekps.supabase.co' '<paste-service-role-key>' > ~/.config/mooniex/cfo.env && chmod 600 ~/.config/mooniex/cfo.env
```

(`SUPABASE_URL` is the public project URL; the **service-role key** is the secret.)

No file or empty keys → the script logs one clean line and `exit 0` (no error
spam in the launchd log). It starts feeding automatically on the next 06:30 run
once the keys are present.

## Schedule (launchd)

Runs **daily 06:30 local (ICT)** — 35 min before the `cfo-rollup` cron
(00:05 UTC = 07:05 ICT) so the day's row is in before the rollup aggregates.

```bash
# install / reload the live copy from the repo source
cp scripts/com.mooniex.cfo-claude-usage.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.mooniex.cfo-claude-usage.plist 2>/dev/null
launchctl load   ~/Library/LaunchAgents/com.mooniex.cfo-claude-usage.plist
launchctl list | grep cfo-claude-usage      # confirm loaded (PID/0 = ok)
```

Logs: `/tmp/cfo-claude-usage.log` (stdout, the one-line status) and
`/tmp/cfo-claude-usage.err` (stderr).

## Manual run / verify

```bash
# print the row that WOULD be posted, no network write, no config touched
bash scripts/cfo-claude-usage-feed.sh --dry-run

# real run (needs keys in ~/.config/mooniex/cfo.env)
bash scripts/cfo-claude-usage-feed.sh
tail -n 5 /tmp/cfo-claude-usage.log

# fire the launchd job now instead of waiting for 06:30
launchctl start com.mooniex.cfo-claude-usage
```

## Log lines you'll see (all single-line, key-free)

| Line | Meaning |
|---|---|
| `inserted 1 row into webapp_cfo_api_events http 201 (5h=… 7d=… …, cost_usd=null)` | success |
| `created template … fill SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY … (no-op this run)` | first run, keys not set yet |
| `SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY empty … — no-op` | config present but blank |
| `no Claude Code credentials in Keychain — no-op` | not logged into Claude Code on this Mac |
| `usage fetch failed (token expired / network?) — no-op, retry tomorrow` | transient; Claude Code refreshes the token on next CEO use |
| `insert REJECTED http 4xx: …` | Supabase rejected (bad key / schema drift) — exit 1, investigate |

## Troubleshooting

- **`launchctl list | grep cfo-claude-usage` shows nonzero last-exit** → read
  `/tmp/cfo-claude-usage.err`. A `4xx` on insert usually means a stale
  service-role key (rotate per `playbooks/secrets-rotation.md`) or that
  `webapp_cfo_api_events` schema drifted from `track.py`.
- **Nothing in the DB but log says inserted** → check you're querying the right
  Supabase project (`SUPABASE_URL`).
- **Rotating the key** → just rewrite `~/.config/mooniex/cfo.env` (the one-liner
  above) and `chmod 600`; no redeploy needed, it's read fresh each run.
