# Safe restart on the Mac

The Mac twin of `docs/ops/safe-restart.md` (Contabo). The same `tools/restart_run.py` does the
work (`--host mac`); only the way it is started and resumed differs.

```
Run card on Contabo ─ scripts/mac-restart.sh ─ssh─▶ Mac: prep (save + close sessions, write
                                                     state/restart/pending-mac.json)
                                             ─ssh─▶ Mac: sudo -n shutdown -r +1   (only if prep exited 0)
Mac boots, gob logs in ─ LaunchAgent com.mooniex.org-resume ─ scripts/org-resume-mac.sh
      waits for network + tailnet + hub ─ restart_run.py --host mac resume ─ report --notify
```

Files: `scripts/mac-restart.sh` (Contabo side), `scripts/org-resume-mac.sh` and
`deploy/launchd/com.mooniex.org-resume.plist` (Mac side), tests in `tests/test_restart_mac.py`.
Nothing here was run against a real Mac when it was written: see "Not verified" at the end.

## Once, before the first restart

1. **Code on both machines.** This change merged; `git pull` in `/opt/MoonieXHQ/Agents/Core` on
   Contabo and in `/Users/gob/Projects/Agents` on the Mac. The plist and the card default assume that
   Mac path. If the checkout is elsewhere (`config/hosts.yaml` lists `/Users/gob/MoonieXHQ/Agents/Core`),
   edit the two paths in the plist before copying it, and pass `--repo <path>` to the card.
2. **An ssh route from Contabo to the Mac that may run commands.** Root on Contabo dials
   `gob@macbook-pro--gob`; the Mac refuses root, so a bare `--host-alias` gets `gob@` in front.
   The `org_dispatch` key of `docs/ops/node-dispatch.md` does **not** do: its forced command
   `node_dispatch` refuses `git rev-parse` and `restart_run.py`. The key Contabo's root uses (default
   `~/.ssh/id_ed25519`) must be in the Mac's `~gob/.ssh/authorized_keys` without `command=`, and the
   host key must already be trusted (run the check below once by hand and accept the fingerprint).
   On Contabo:
   ```sh
   ssh -o BatchMode=yes gob@macbook-pro--gob 'cd /Users/gob/Projects/Agents && git rev-parse HEAD'
   ```
3. **`sudo -n shutdown -r +1` without a password.** On the Mac, once:
   ```sh
   echo 'gob ALL=(root) NOPASSWD: /sbin/shutdown -r +1' > /tmp/mooniex-restart.sudoers && sudo visudo -cf /tmp/mooniex-restart.sudoers && sudo install -m 0440 -o root -g wheel /tmp/mooniex-restart.sudoers /etc/sudoers.d/mooniex-restart
   ```
   Check from Contabo: `ssh gob@macbook-pro--gob 'sudo -n -l /sbin/shutdown -r +1'` prints the command.
   Without this rule the card still saves and closes the sessions, then prints what to do by hand and
   exits 6.
4. **The Mac comes back to a logged-in desktop.** The LaunchAgent runs at gob's login, not at boot.
   Automatic login for gob must be on, and FileVault must be off or someone must be at the Mac: with
   FileVault on, a plain `shutdown -r` stops at the disk-unlock screen and nothing resumes until a
   person types the password. Tailscale must start at login.
5. **The hub env file** `~/.config/mooniex/org-db.env` exists, as it already must for the sessions
   (`scripts/hub/with-org-db-env.sh`).

## Install the LaunchAgent (on the Mac, as gob)

```sh
cd /Users/gob/Projects/Agents
mkdir -p ~/Library/LaunchAgents state/restart
cp deploy/launchd/com.mooniex.org-resume.plist ~/Library/LaunchAgents/ && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mooniex.org-resume.plist
```

`RunAtLoad` also fires once at bootstrap. With no marker that only writes a line, so a good install
ends with `tail -3 state/restart/mac-resume.log` showing `nothing to resume`. If the label is already
loaded, `launchctl bootout gui/$(id -u)/com.mooniex.org-resume` first. Check with
`launchctl print gui/$(id -u)/com.mooniex.org-resume | head -20`.

## The cards (run on Contabo)

`<SHA>` is the full commit id of the Mac checkout: `git rev-parse HEAD` there. The card refuses
(exit 4) when the Mac is on another commit.

Dry run (reads the Mac's HEAD, then `prep --dry-run`; closes and writes nothing):

```sh
bash /opt/MoonieXHQ/Agents/Core/scripts/mac-restart.sh --sha <SHA> --dry-run
```

Restart (returns at once; the ssh calls run in a transient service, like the Contabo card; read the
output with `journalctl -u 'mac-restart-*'`):

```sh
systemd-run --unit=mac-restart-$(date +%s) --collect bash /opt/MoonieXHQ/Agents/Core/scripts/mac-restart.sh --sha <SHA>
```

Bring the sessions back without rebooting (after a prep that failed half way, or a cancelled restart):

```sh
ssh gob@macbook-pro--gob 'export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH && cd /Users/gob/Projects/Agents && bash scripts/hub/org-python.sh tools/restart_run.py --host mac resume'
```

Options: `--host-alias <name|user@host>` (default `macbook-pro--gob`), `--repo <path on the Mac>`.

| exit | meaning |
|---|---|
| 0 | prep ok and the restart is scheduled in 1 minute (dry run: prep ok) |
| 2 | bad arguments; nothing was dialled |
| 4 | the Mac's HEAD is not `--sha`; nothing changed |
| 5 | ssh could not read the Mac's HEAD; nothing changed |
| 6 | prep ok, `sudo -n shutdown` refused: sessions are saved and closed; the card printed three ways out |
| other | prep's own exit code. 3 = a session stayed mid-turn for 600 s, nothing closed. 1 = a session failed to save; some may be closed, the card prints the resume command |

## After the Mac is back

`state/restart/mac-resume.log` (on the Mac) has one timestamped line per step and the
`กลับมา n/m` count from `report`. Retry only the report with
`bash scripts/hub/org-python.sh tools/restart_run.py --host mac report` in the repo. The marker and
manifest stay until a resume finishes with every session back, so a login resumes again.

## Cancel or uninstall

- Within the minute after the card: on the Mac `sudo pkill shutdown` (untested; a scheduled
  `shutdown` is a waiting process), then the resume command above.
- Uninstall: `launchctl bootout gui/$(id -u)/com.mooniex.org-resume && mv ~/Library/LaunchAgents/com.mooniex.org-resume.plist ~/.Trash/`.
  Keep `state/restart/` manifests and logs.

## Not verified, and known gaps

- Written on Contabo with stubs for `ssh`, `route`, `tailscale` and the hub wrapper. No real Mac, no
  macOS bash 3.2, no `launchctl`, no ssh to the Mac was used. The first run is the test.
- `shutdown -r +1` on macOS is assumed to detach and return. The card sends it with its output
  discarded so a lingering process cannot hold the ssh call open.
- `report --notify` reaches the Run Inbox through `tools/ask_run.py`, which needs
  `~/.config/mooniex/run-inbox.token`; the Mac has none yet (CLAUDE.md). Resume does not depend on
  it: the notification fails, the log keeps the count, the script exits non-zero.
- `tools/restart_run.py` still words that notification "Restart Contabo" and its missing-session
  fallback card uses a Contabo `--cwd`. `clean` reads `/proc/meminfo` and does not run on macOS.
- A dropped ssh link in the middle of prep leaves it half done (the card keeps the link alive with
  `ServerAliveInterval`). The card does not roll back by itself the way `org-restart.sh` does: it
  prints the resume command.
