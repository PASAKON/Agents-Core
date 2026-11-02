# Report: HostSpawn Mac Run Inbox P2 & Host Router Enablement (M1–M5)

- **Date:** 2026-11-02
- **Project:** `hostspawn` (PH `#a08e3352`, completed via CTO takeover `#f69c4825`)
- **Milestones covered:** M1 (`Mac side: Console flag + token, probe 401`), M4 (`Skill + role docs updated`), M5 (`Enable router in config/hosts.yaml`)

## What Changed

1. **Mac Peer Executor & Token (M1):**
   - Fast-forwarded `/Users/gob/MoonieXHQ/Projects/MoonieX/Console` to `410092b`.
   - Installed `~/.config/mooniex/run-inbox.token` (`mode 600`, 44 bytes) matching Contabo's Run Inbox bearer token.
   - Added `<key>RUN_PEER_EXECUTOR</key><string>1</string>` to `~/Library/LaunchAgents/com.mooniex.console-mac.plist` and reloaded `com.mooniex.console-mac`.
   - Verified `POST /api/peer/run` returns HTTP `401` without valid HMAC headers both locally (`https://127.0.0.1:8443/api/peer/run`) and from Contabo over Tailscale (`https://macbook-pro--gob.tail400676.ts.net/api/peer/run`).
   - Verified `tools/ask_run.py list --status pending` and `tools/ask_run.py list --questions` exit `0` on the Mac.

2. **Contabo Hub Dispatch (M2 setup):**
   - Installed `/etc/systemd/system/mooniex-console.service.d/peer-dispatch.conf` with `Environment=RUN_PEER_DISPATCH=mac-3ecb3784` on Contabo and restarted `mooniex-console.service` (after verifying 0 running cards and `org-tmux.scope` isolation).

3. **Docs & Host Router Enablement (M4, M5):**
   - Updated `.claude/skills/ALL_Protocol_RunInbox/SKILL.md`, `CLAUDE.md`, and `roles/project_head.md` to document Mac Run Inbox P2 (`tools/ask_run.py` + `tools/ask_run.py wait <id>`) and automatic host routing.
   - Enabled `router.enabled: true` in `config/hosts.yaml` and updated `tests/test_w26_pick_host.py`.
   - Fixed Windows `cp1252` `UnicodeEncodeError` in `tools/agy_browse.py` by reconfiguring `sys.stdout` to UTF-8 in `main()`.

## Not checked / risk

- **Compromised-Mac blast radius (`~/.config/mooniex/run-inbox.token` + `SESSION_SECRET`):**
  - **What `run-inbox.token` grants:** Ability to create, list, and wait on Run Inbox command cards and question cards (`POST /api/run/requests`, `POST /api/run/questions`) on `https://terminal.mooniex.com`. It does **not** grant ability to approve or execute a command card (every command card still requires the CEO's WebAuthn / Face ID assertion from his phone).
  - **What `SESSION_SECRET` + `RUN_PEER_EXECUTOR=1` grants:** The Mac peer Console accepts HMAC-SHA256-signed `POST /api/peer/run` payloads from Contabo (bound to `host="mac"`, `peerId="mac-3ecb3784"`, 60-second clock skew window, single-use nonce cache, and byte-verified `command === argv.join(" ")`). Because `SESSION_SECRET` is shared between Contabo and the Mac peer Console, a full compromise of the Mac user account (`gob`) would expose `SESSION_SECRET` and `~/.config/mooniex/run-inbox.token`.
  - **Immediate revoke commands if the Mac is ever lost or compromised:**
    1. **On Contabo (disable peer dispatch & rotate Run Inbox token):**
       ```bash
       rm -f /etc/systemd/system/mooniex-console.service.d/peer-dispatch.conf
       openssl rand -base64 32 > /root/.config/mooniex/run-inbox.token
       chmod 600 /root/.config/mooniex/run-inbox.token
       systemctl daemon-reload && systemctl restart mooniex-console.service
       ```
       *(And rotate `SESSION_SECRET` in `/opt/MoonieXHQ/Projects/MoonieX/Console/.env` followed by `systemctl restart mooniex-console.service`.)*
    2. **On the Mac (if reachable — disable peer executor & remove token):**
       ```bash
       rm -f ~/.config/mooniex/run-inbox.token
       launchctl bootout gui/$(id -u)/com.mooniex.console-mac
       ```
