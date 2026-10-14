# Spend guard (phase 1): ops

`tools/spend_guard.py` checks OpenRouter and fal spend every 15 minutes with no model call. It mails the CEO
when a cap, a spike or a short runway shows up. Once armed, it can also pause a runaway OpenRouter key and put
the decision on a Run card. It comes from CEO card Q-20261013-1958-bc81 (option 1) and SomPong's design §3.
Phases 2–3 and the consumer table are in `docs/plans/spend-guard-2026-10-14.md`.

## What it reads

| Provider | Call | Key (Infisical `Agents-Core/prod/spend-guard`) |
|---|---|---|
| OpenRouter | `GET /api/v1/credits` gives the account balance (total_credits − total_usage). `GET /api/v1/keys?include_disabled=true` gives every key's limit, limit_remaining, usage, and daily/weekly/monthly usage | `OPENROUTER_API_KEY_ADMIN`, a management key. It cannot run inference |
| fal.ai | `GET rest.alpha.fal.ai/billing/user_balance` gives the prepaid balance as a bare number. The documented `api.fal.ai/v1/account/billing?expand=credits` is the fallback: from Contabo's IP `api.fal.ai` answers a Vercel challenge (403, HTML) even with no key (task-b1b251f0) | `FAL_BILLING_API_KEY_RO`, preset BILLING (read-only) |
| Google Cloud | nothing yet. No billing account exists (the CEO's call). Plan §5 | — |

A key is always named by its **name** on the provider page and the first 8 characters of its hash. OpenRouter's
`label` field is a piece of the key, so it is never logged, stored or mailed.

## When it mails (`email_ceo` kind `alert`, as session `cto-spend-guard`)

| Alert | Fires when | Mailed again |
|---|---|---|
| cap 50 / 80 / 100 % | a key's `limit`, or the prepaid balance since the last top-up, or `monthly_cap_usd` (CFO, config) | once per level crossed; 100 % again every 24 h; a reset or top-up re-arms the levels |
| spike | the last hour is ≥ 3× the hourly average of the last 7 days **and** ≥ $0.50/h | every 6 h while it lasts |
| runway | balance ÷ (7-day average × 24) < 3 days | every 24 h; at once when it drops under 1 day |
| blind | a provider could not be read (down, refused, key missing), or `check` never started | every 6 h while it lasts |
| paused | a key the guard paused still waits for the CEO | every 24 h, with a fresh card |

Each run sends at most one mail, with the most urgent alert as the title. In its first 24 h the guard has no
history of its own, so the baseline comes from OpenRouter's calendar counters: this week since Mon 00:00 UTC,
or this month when the week is under 25 h old. The mail labels that figure "ประมาณจาก…" (estimated from…).
fal has no counter, so fal spike and runway start after 24 h of snapshots.

Telegram is off. The only existing send path, `lib/telegram_out.send_to_ceo` (@SSomPongBot), needs
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CEO_CHAT_ID`, and on Contabo those live only in the secretary's legacy env
file, outside Infisical. Add both to `/spend-guard` (an Infisical secret reference is enough) and the guard
sends on Telegram too, with no code change. No new bot.

## Pause (OpenRouter only)

`pause.mode: auto` behaves in two stages:
- **Alert-only for the first 24 h of live runs.** The guard logs `would pause <name> (<hash8>)`, and the mail
  says so.
- **Then armed.** At 100 % of a key's limit, or on a key's spike, it sends `PATCH /keys/{hash} {"disabled": true}`,
  checks the answer, and raises a red Run card (root on Contabo; option 3 deletes a key; expects input, 1800 s):
  - `1`: resume
  - `2 <USD>`: set that limit and resume
  - `3 revoke`: delete the key for good
  - no answer: the key stays paused, and a new card and a reminder follow every 24 h.

Account-level alerts and every fal alert never pause anything: fal can only revoke, and that cannot be undone.

The guard does not auto-pause:
- a key with no row under `providers.openrouter.keys` in `config/spend_guard.yaml` (`unmapped_keys: alert`),
  because it is unknown which services that key would take down;
- a key whose row says `pause: false`;
- a key the CEO resumed within the last 24 h.

A key re-enabled by hand on openrouter.ai drops off the paused list.

## Data

`$ORG_ROOT/state/spend_guard/` holds the following. Git ignores it, and nothing in it is a credential.

| File | Contents |
|---|---|
| `state.json` | alerts sent, prepaid cycles, paused and resumed keys, first live run |
| `snapshots.jsonl` | one row per run, kept 35 days |
| `events.jsonl` | `check`, `would_pause`, `paused`, `decided`, `unpaused`, `not_started` |

## Verbs

```
spend_guard.py timer                   # the unit: runs `check` under infisical run; mails blind if it never started
spend_guard.py check [--dry-run]       # needs the keys in env; --dry-run pauses, mails and writes nothing
spend_guard.py keys                    # name, hash8, limit, usage per OpenRouter key (to fill the consumer map)
spend_guard.py status                  # offline: mode, open alerts, paused keys, last reading
spend_guard.py test-alert [--dry-run]  # one mail marked ทดสอบ with the current balances
spend_guard.py decide <hash>           # the pause card; reads 1 / 2 <USD> / 3 revoke from stdin
```

Any verb that needs a key runs under Infisical:

```
env ORG_ROOT=/opt/MoonieXHQ/Agents/Core /opt/MoonieXHQ/Agents/Core/.venv/bin/python \
  /opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy/tools/infisical_setup.py run Agents-Core prod --path /spend-guard -- \
  /opt/MoonieXHQ/Agents/Core/.venv/bin/python /opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy/tools/spend_guard.py <verb>
```

An agent session never runs that itself: the secret-env guard refuses it. It goes on a red Run card: it runs as root and reads the management key.

## Install (Contabo, one Run card, after the branch lands at `<SHA>`)

```bash
git -C /opt/MoonieXHQ/Agents/Core fetch origin main
git -C /opt/MoonieXHQ/Agents/Core worktree add --detach /opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy <SHA>
cp /opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy/deploy/systemd/spend-guard.service \
   /opt/MoonieXHQ/Agents/Core/worktrees/spend-guard-deploy/deploy/systemd/spend-guard.timer \
   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now spend-guard.timer
systemctl start spend-guard.service
systemctl list-timers spend-guard.timer
tail -3 /opt/MoonieXHQ/Agents/Core/state/spend_guard/events.jsonl
```

`systemctl start` runs the first check at once, so `first_live_run` is stamped and the 24 h alert-only window
starts. Install only after both keys verify (`infisical_setup.py last4 … --path /spend-guard`). Without them
the first run mails "Spend guard ไม่ได้เริ่มทำงาน (exit 2)" ("spend guard did not start"), which is correct but
not useful.

**Upgrade:** `git -C …/worktrees/spend-guard-deploy checkout --detach <NEW_SHA>`, then copy the units again
only if they changed and run `systemctl daemon-reload`.

**Remove:** `systemctl disable --now spend-guard.timer`, then delete the two unit files and run `daemon-reload`.

## Arm, disarm, check

- **Arm before 24 h:** `pause.mode: armed` in the config, then land and move the deploy worktree.
- **Never pause:** `pause.mode: alert_only`.
- **Map a key:** run `keys` on a red Run card (root, reads the management key). Under `providers.openrouter.keys` add `"<name>": {consumers: [...]}`,
  or `pause: false` for a key that must never stop.
- **Health:** `systemctl status spend-guard.service`. `spend_guard.py status` reads files only and needs no
  key. Exit 1 means a provider is blind (already mailed). Exit 3 means the hub did not take the mail (the next
  run retries).

## Known limits

- If the guard's own Python cannot start, nothing mails; `systemctl --failed` shows it. Anything after Python
  starts (Infisical refused or down, a key missing, a provider down) mails "blind".
- OpenRouter's counters are calendar UTC (day, week from Monday, month), not rolling. In the first 24 h the
  baseline is an estimate. After that, the spike and runway math uses the guard's own snapshots.
- Pausing a key cuts every service that reads that key's value. Today ClaudeFlow (LuNar) and Option share one
  value (plan §2). The phase-2 key broker gives each service its own key.
