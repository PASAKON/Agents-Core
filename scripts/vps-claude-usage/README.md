# Claude usage monitor (VPS, always-on)

Polls the CEO's Claude subscription usage on the **Contabo VPS** (always-on, so
it survives the Mac sleeping / battery dying), caches it for the iPhone widget,
and **emails warm-up / weekly reminders** so the plan gets used to the fullest.

This is the always-on successor to the Mac feed (`scripts/claude-usage-sync.sh`),
which only runs while the Mac is awake.

## Why a dedicated VPS login

The OAuth refresh token **rotates on every refresh**. Two independent clients
sharing one token chain rotate each other out → repeated logouts. So the VPS
gets its **own** `claude auth login` session (its own chain); the Mac is
untouched. The usage endpoint is account-level, so both see the same numbers.

## One-time setup (CEO does step 1)

```bash
# 1) Mint the VPS's own login (CEO, interactive — paste-code flow, no port-forward):
ssh -t mooniex-vps 'claude auth login --claudeai --email pass.gob1@gmail.com'
#    open the printed URL → Authorize → copy the code → paste back.
#    Creds land in /root/.claude/.credentials.json (independent of the Mac).

# 2) Deploy (CTO):
bash scripts/vps-claude-usage/deploy.sh
```

## How it works

`monitor.py` (run by `claude-usage-monitor.timer`, every 4 min):

1. Reads `/root/.claude/.credentials.json`, refreshes the access token when
   <5 min to expiry (rotated refresh token written back — chain never breaks).
2. `GET api.anthropic.com/api/oauth/usage` with `User-Agent: claude-code/...`
   (required or the endpoint rate-limits). On 401 → refresh once, retry.
3. Writes `usage.json` (cache for the iPhone widget — Phase B).
4. Evaluates reminders and emails the CEO via the Gmail API (reusing
   claudeflow's existing `GMAIL_*` OAuth2 creds — no new credential needed).

The usage endpoint is **metadata** — polling it does **not** consume the plan
quota. Only abuse rate-limiting is a risk, mitigated by the UA + 4-min cadence.

## Reminders (email → pass.gob1@gmail.com)

| Trigger | Condition | Why |
| --- | --- | --- |
| 🔥 5h reset | was using ≥50%, now <15%, **and** weekly has ≥10% left | fresh 5h window worth using |
| 🎉 weekly reset | weekly dropped from ≥20% to <10% | full budget back |
| ⏰ use-it-or-lose-it | weekly resets within 24h **and** ≥30% still unused | budget about to vanish (no roll-over) |

- Stays **silent** when weekly is exhausted (a 5h reset can't help).
- Reset events self-dedupe (via the previous-utilization transition); the
  use-it-or-lose-it warning dedupes per weekly cycle (`notified_useit_for`).
- Tune thresholds at the top of `monitor.py`.
- **Reminder-only by design** — it never auto-sends an inference request to
  "warm up" the clock (that would waste quota + the window, and is ToS-gray).
  Your first real message starts the clock.

## Ops

```bash
ssh mooniex-vps 'systemctl status claude-usage-monitor.timer --no-pager'
ssh mooniex-vps 'journalctl -u claude-usage-monitor.service -n 30 --no-pager'
ssh mooniex-vps 'python3 /opt/claude-usage-monitor/monitor.py --status'      # current usage
ssh mooniex-vps 'python3 /opt/claude-usage-monitor/monitor.py --dry-run'     # what it would email
ssh mooniex-vps 'python3 /opt/claude-usage-monitor/monitor.py --test-email'  # send a test
```

## Phase B — widget fetches over HTTPS (live)

So the iPhone widget stays fresh even when the Mac is off, a tiny read-only
server (`serve/serve.py`) exposes the cache behind the existing traefik:

- `serve/docker-compose.yml` → container `claude-usage-serve` on the `n8n_default`
  network, additive traefik router `Host(webhook.mooniex.com) && PathPrefix(/claude-usage)`
  (does NOT disturb the existing claudeflow-webhook router; auto-TLS via `mytlschallenge`).
- Gated by `USAGE_TOKEN` (in `serve/.env` on the VPS, **never committed**): `GET https://webhook.mooniex.com/claude-usage?k=<token>`.
- The widget (`output/iphone-shortcuts/Claude Usage.js`) fetches that URL first,
  falling back to the Mac's iCloud file. The repo keeps a `__USAGE_TOKEN__`
  placeholder; the real token is injected only into the iCloud copy on deploy:
  `sed "s|k=__USAGE_TOKEN__|k=$TOK|" "<repo>/Claude Usage.js" > "<iCloud>/Claude Usage.js"`.
  **Scope the sed to `k=__USAGE_TOKEN__` (the URL), NOT a global `s/__USAGE_TOKEN__/$TOK/`.**
  `fromURL()` guards on the bare `__USAGE_TOKEN__` literal to detect an un-deployed
  copy; a global sed rewrites that guard to match the real token, so `fromURL()`
  returns null every time and VPS-fetch silently dies (widget falls back to
  iCloud-only — Mac-off freshness lost).
  **Re-run this deploy after EVERY widget redesign** — the `.js` is NOT synced by
  `claude-usage-sync.sh` (that writes only `claude-usage.json`). Forgetting to
  re-deploy leaves iCloud on the OLD design while the repo moves on (this is exactly
  how the pixel-art redesign "reverted" to glass on 2026-06-24).

Deploy / teardown the server:
```bash
ssh mooniex-vps 'cd /opt/claude-usage-monitor/serve && docker compose up -d'   # up
ssh mooniex-vps 'cd /opt/claude-usage-monitor/serve && docker compose down'    # remove (reversible)
```

## Files

- `monitor.py` — the service (poll + refresh + cache + reminders)
- `claude-usage-monitor.service` / `.timer` — systemd units (→ `/etc/systemd/system/`)
- `deploy.sh` — idempotent deploy from the Mac (verifies hostname `vmi3371421` first)
- `usage.json` / `state.json` — runtime (created on the VPS under `/opt/claude-usage-monitor/`)
