# Mac sshd hardening — key-only, one account, tailnet only

Org Mesh W2.7 (task-42fdcda7). **A document, not a change.** The review applied
none of it: no file under `/etc/ssh` was written, Remote Login was not touched,
no key was generated. The Mac's sshd stays off (docs/design/org-mesh.md §6). Apply
this before Remote Login is ever turned on for the mesh (W2.8 or a later
pull-side caller), and re-check it after every macOS update.

## What this Mac has today (read 2026-09-30)

| fact | where | consequence |
|---|---|---|
| macOS 14.3.1 (23D60), OpenSSH_9.4p1 | `sw_vers`, `ssh -V` | `DisableForwarding`, `KbdInteractiveAuthentication`, `PermitUserRC` and CIDR in `AllowUsers` all exist |
| `/etc/ssh/sshd_config` line 18: `Include /etc/ssh/sshd_config.d/*` | the file | a drop-in is read at that point, in name order |
| `/etc/ssh/sshd_config.d/100-macos.conf`: `UsePAM yes`, `AcceptEnv LANG LC_*` | the file | PAM stays on, so keyboard-interactive must be switched off by name |
| "for each keyword, the first obtained value will be used" | sshd_config(5) | the drop-in must sort **before** `100-macos.conf`: name it `000-...` |
| sshd is started by launchd from `/System/Library/LaunchDaemons/ssh.plist`: `inetdCompatibility`, `Sockets` → `SockServiceName ssh`, Bonjour `ssh` and `sftp-ssh`, `Disabled = 1` | `plutil -p` | launchd owns the socket on **every** interface. `ListenAddress` in sshd_config has no effect, and the Mac advertises ssh on the LAN by Bonjour when Remote Login is on |

Because of the last row, "tailnet only" cannot be done with `ListenAddress`. It is
done twice instead: `AllowUsers gob@<address>` refuses the login, and a pf rule
drops the connection before sshd sees it.

## The drop-in

`/etc/ssh/sshd_config.d/000-mooniex-mesh.conf`, owner root, mode 644:

    # Org Mesh (W2.7, task-42fdcda7): key-only, one account, tailnet only.
    # Named 000- so it is read before 100-macos.conf: sshd keeps the first
    # value it reads for a keyword.
    PubkeyAuthentication yes
    AuthenticationMethods publickey
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PermitEmptyPasswords no
    PermitRootLogin no
    # One address per dispatcher that may call this Mac (tailscale ip -4 on it).
    # 100.64.0.0/10 is the whole tailnet AND the carrier-grade NAT range some
    # mobile networks hand out, so prefer exact addresses.
    AllowUsers gob@100.x.y.z gob@100.a.b.c
    DisableForwarding yes
    PermitTunnel no
    PermitUserEnvironment no
    PermitUserRC no
    MaxAuthTries 3
    LoginGraceTime 20
    MaxStartups 4:50:10
    ClientAliveInterval 60
    ClientAliveCountMax 3

Why each line:

- `AuthenticationMethods publickey` with password and keyboard-interactive off:
  a key is the only way in. With `UsePAM yes`, PAM then only runs its account
  and session steps.
- `AllowUsers gob@<address>`: sshd_config(5) checks USER and HOST separately
  and accepts CIDR `address/masklen`. Any other account, or `gob` from any other
  address, is refused after the key exchange. **This also refuses `gob` from the
  LAN.** If anyone reaches this Mac over ssh from the LAN today, add that
  address first or they are locked out.
- `DisableForwarding yes` overrides every other forwarding option (X11, agent,
  TCP, StreamLocal). The `org_dispatch` key's `restrict` already does this for
  that key; this line covers every other key in `~/.ssh/authorized_keys`.
- `PermitUserEnvironment no`, `PermitUserRC no`: no `~/.ssh/environment`, no
  `~/.ssh/rc` run at login. `PermitUserEnvironment no` is the default, written
  down so a later edit is visible.
- `MaxAuthTries 3`, `LoginGraceTime 20`, `MaxStartups 4:50:10`: fewer attempts
  per connection and fewer unauthenticated connections held open.
- `ClientAlive*`: a dead dispatcher's connection is dropped after about 3 minutes.

Not in the drop-in on purpose: `ForceCommand`. The dispatch key's own
`command=` already forces `node_dispatch`; a server-wide `ForceCommand` would
also take the shell away from the account's other keys.

## The packet filter (optional, recommended)

`/etc/pf.anchors/mooniex.ssh`:

    # Org Mesh W2.7: port 22 only from loopback and the dispatchers.
    pass in quick on lo0 proto tcp to any port 22
    pass in quick proto tcp from { 100.x.y.z, 100.a.b.c } to any port 22 keep state
    block drop in quick proto tcp to any port 22

Two lines at the end of `/etc/pf.conf`:

    anchor "mooniex.ssh"
    load anchor "mooniex.ssh" from "/etc/pf.anchors/mooniex.ssh"

Then `sudo pfctl -nf /etc/pf.conf` (parse only), `sudo pfctl -f /etc/pf.conf`,
`sudo pfctl -E`. Caveats, **none tested on this Mac** (the review was read-only):
pf is not enabled at boot unless a LaunchDaemon runs `pfctl -E`; a macOS update
can replace `/etc/pf.conf` and drop the two lines; this rule also stops the
Bonjour-advertised ssh from answering on the LAN, which is the point.

## Turning Remote Login on

System Settings → General → Sharing → Remote Login: on, "Allow access for: Only
these users" → the one account. That adds a second gate (the
`com.apple.access_ssh` group) under the same account rule as `AllowUsers`.

## Verify

    sudo sshd -t      # syntax only; prints nothing when the files parse
    sudo sshd -T | grep -Ei '^(pubkeyauthentication|authenticationmethods|passwordauthentication|kbdinteractiveauthentication|permitemptypasswords|permitrootlogin|allowusers|disableforwarding|permittunnel|permituserenvironment|permituserrc|maxauthtries|logingracetime|maxstartups)'

`sshd -T` prints the effective values after first-value-wins, so it shows whether
the drop-in or `100-macos.conf` won. Expected: `passwordauthentication no`,
`kbdinteractiveauthentication no`, `authenticationmethods publickey`,
`permitrootlogin no`, `disableforwarding yes`, `allowusers gob@...` for each
dispatcher, and the rest as written above.

From outside:

1. From a dispatcher, with the dispatch key: the W2.8 checks in
   `docs/ops/node-dispatch.md` pass.
2. Password attempt from a dispatcher:
   `ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive gob@<mac tailnet ip>`
   → `Permission denied (publickey)`.
3. Another account: `ssh someone@<mac tailnet ip>` → `Permission denied`.
4. From the LAN: `ssh gob@<mac LAN ip>` → no answer (pf) or `Permission denied` (AllowUsers).

Re-run `sudo sshd -T` after every macOS update: an update may rewrite
`/etc/ssh/sshd_config` or `100-macos.conf`.

## Rollback

Move the drop-in to the Trash (`sudo mv /etc/ssh/sshd_config.d/000-mooniex-mesh.conf ~/.Trash/`),
then switch Remote Login off and on. For pf, delete the two lines from
`/etc/pf.conf` and run `sudo pfctl -f /etc/pf.conf`.

Sources: sshd_config(5) and sshd(8) on this Mac (OpenSSH_9.4p1),
`/System/Library/LaunchDaemons/ssh.plist`, `/etc/ssh/sshd_config`,
`/etc/ssh/sshd_config.d/100-macos.conf`, pf.conf(5).
