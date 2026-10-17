# winbox hold release — a PH asks, the CEO taps

OrgMesh P3-A. CEO decision 2026-10-17 (option A): a winbox Project Head raises its own
"lift the hold" card and the CEO taps it on his phone. His tap is the authority.

The CEO's hold on the winbox screen (`windows/pc_lease.py ceo-on` / `ceo-off`) has to outlast
every agent. A PH may not run `pc_lease.py ceo-off` itself, and an ad-hoc `ask_run` over ssh
was refused as well. What it may do is ASK, once, in his words, through a key that can run
nothing else.

## The flow

```
winbox PH                               Contabo                              CEO's phone
---------                               -------                              -----------
pc_lease.py status          -> "held -> ask the CEO: pc_lease.py ask-release --ceo-said ..."
pc_lease.py ask-release
  --ceo-said "<his words>"
  ssh -i id_hold_release  ------------> sshd forced command
                                        tools/hold_release_card.py
                                         - parses ONE form, refuses the rest (exit 2)
                                         - refuses if a hold-release card is pending
                                         - raises the fixed Run card (risk amber)  --> Run Inbox card
  prints the card id  <---------------  prints the card id                         CEO reads the exact
                                                                                    bytes, taps Run
                                        executor on contabo runs the card:   <---- his tap
                                        ssh winbox 'pc_lease.py ceo-off
                                          --ceo-said <slug> & del ESC_HOLD
                                          & pc_lease.py status'
```

`ask-release` changes nothing on winbox: no hold, lease, window or farm (it appends one line
to `pc_lease.log`). While the hold is on, `status`, `take`, `extend`, `gate` and `ceo-check`
all end with the same line:

    held -> ask the CEO: pc_lease.py ask-release --ceo-said "<his words>"

## What the key can do

Exactly one form reaches the script (`SSH_ORIGINAL_COMMAND`, matched by a regex, never by a shell):

    ask-release --ceo-said "<words>" [--who <ph id>]

| part | rule |
|---|---|
| words | printable ASCII (space to `~`), no double quote, 3..120 characters, at least 3 letters or digits |
| `--who` | `[A-Za-z0-9_-]{1,40}`; it becomes the card's requester session (default `winbox-ph`), role `project_head`. ask_run also needs an alphanumeric first character |
| anything else | `refused: ...` on stderr, exit 2, nothing sent |

Of the words only a slug (`[a-z0-9-]`, lowercase, runs of anything else become one `-`) reaches
the card's command line. `;`, `&`, `|`, quotes, backticks, `$()`, `%VAR%` and `\` in the words are
turned into hyphens (or, for a double quote, a newline, a tab or non-ASCII, refused outright).
The words themselves appear on the card in the `why` line (`winbox PH quotes you: "..."`, cut
with `...` after 66 characters; the slug in the command carries them in full).

The card is a fixed template; only the slug varies (`tests/test_hold_release_card.py` pins every byte):

    host contabo · risk amber · timeout 600 s · requester <who> / project_head
    ssh winbox '<winbox python> C:\mooniex\pclease\pc_lease.py ceo-off --ceo-said <slug>
                & del %USERPROFILE%\Documents\CookieRunScript\modelplay\ESC_HOLD
                & <winbox python> C:\mooniex\pclease\pc_lease.py status'

Rate limit: while a hold-release card is pending the next ask is refused (exit 2, the message
names the waiting card). If the hub cannot say whether one is pending, nothing is raised (exit 3).

Exit codes of the forced command: 0 card raised (stdout is the card id and nothing else) ·
2 refused · 3 hub error (stderr is `hub error (<status>) <code>`; no env value, no address).
`pc_lease.py ask-release` maps them to 0 / 2 / 1.

`pc_lease.py ceo-off` itself is unchanged: from a shell it still needs the desktop button or
`--ceo-said`. The card passes the slug as `--ceo-said`, which `ceo_button_guard` logs.

## Install (after merge) — a CEO Run card, raised by the PH

This PR installs nothing. After it is merged and `windows/pc_lease.py` (LEASE_VERSION 4) is on
winbox (`scripts/pc-lease.sh` deploys it on the next call), the PH raises Run cards for the two
steps below; the CEO reads them and taps.

### 1. On winbox: make the key

Plain `cmd.exe`, as the user that runs `pc_lease.py` over ssh. The key has no passphrase because
nothing is there to type one; that is why it can only run the forced command.

    ssh-keygen -t ed25519 -f "%USERPROFILE%\.ssh\id_hold_release" -N "" -C "winbox-hold-release"
    icacls "%USERPROFILE%\.ssh\id_hold_release" /inheritance:r /grant:r "%USERNAME%:R"

Then an ssh alias, so no address or user is in this repo (`%USERPROFILE%\.ssh\config`):

    Host hold-release
        HostName <contabo tailnet name>
        User <the Contabo user that owns the line below>

`hold-release` is the default; `PC_LEASE_RELEASE_TARGET` names another alias.
Only the PUBLIC half (`id_hold_release.pub`) goes anywhere. Never put the private key on a card.

### 2. On Contabo: the authorized_keys line

One line in that user's `~/.ssh/authorized_keys`, with the public key and winbox's tailnet
address filled in from `tailscale status` on the day (a placeholder here on purpose):

    command="cd /opt/MoonieXHQ/Agents/Core && exec .venv/bin/python -E -s tools/hold_release_card.py",from="<winbox tailnet ip>",restrict <key>

- `command=` runs this script whatever the client asked; the client's text only fills
  `SSH_ORIGINAL_COMMAND`.
- `from=` limits the key to winbox's tailnet address.
- `restrict` switches off the pty, port, agent and X11 forwarding and `~/.ssh/rc`.
- `-E -s` ignores `PYTHON*` variables and the user site.
- No hub wrapper (`with-org-db-env.sh`): `ask_run` does not use `lib.db`, so the key never drives a
  process holding `ORG_DB_URL`. The user is a non-root Contabo user (never root) that holds only
  the Run Inbox token.

Needs on Contabo: `.venv/bin/python` in `/opt/MoonieXHQ/Agents/Core`, and a Run Inbox token for
that user (`RUN_INBOX_TOKEN` or `~/.config/mooniex/run-inbox.token`, mode 0600) that the hub
accepts for command cards.

### 3. Check it

On Contabo, without a token and without sending anything:

    SSH_ORIGINAL_COMMAND='ask-release --ceo-said "testing the card text"' \
      .venv/bin/python -E -s tools/hold_release_card.py --dry-run

Prints the card body. On winbox, while the hold is on, the real thing:

    pc_lease.py ask-release --ceo-said "<his words>"

Prints `OK - asked the CEO. Run card RUN-... is on his phone.` The hold stays until he taps.
`--who <id>` names the session; the default is `ORG_SESSION_ID` / `CXO_SESSION_ID`, else `winbox-ph`.

## Revoke

Delete the `command=` line from Contabo's `authorized_keys`. Nothing else holds state: a card
already raised is the CEO's to deny or let expire.

## What it does not do

- It does not lift the hold. Only the executor running the card the CEO tapped does.
- It does not let the PH choose the command, the host, the risk or the timeout: they are constants
  in `tools/hold_release_card.py`.
- It is not for the Cookie Run farm: `ceo-off` puts the farm back as it always has.
