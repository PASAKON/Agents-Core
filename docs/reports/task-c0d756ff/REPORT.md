# REPORT task-c0d756ff

Implemented the Agents-Core Gmail broker, one-time consent helper, installer,
wire-contract documentation, and offline tests. No installation, consent, network
mail access, or secret provisioning was performed. Existing main-checkout auth and
systemd files were read only as requested; neither was copied or modified.

## Files changed

- `runners/gmail_broker.py`: stdlib Unix broker, fixed HTTP method/path allowlist,
  OAuth refresh in-process, security-mail withholding, safe text/filenames,
  draft/reply handling, attachment caps, caller gating and content-free audit.
- `scripts/install-gmail-broker.sh`: install/uninstall/status and non-writing
  dry-run; root Infisical fetch followed by `setpriv` to `mailbroker`, exact caller
  UID, privileged runtime-directory creation, optional runtime writable path.
- `scripts/gmail-broker-auth.py`: state/PKCE/nonce consent, fixed account and exact
  scopes, identity-claim checks, hidden/pipe input, token stored only via stdin.
- `docs/design/gmail-broker.md`: wire fields, install/consent/rollback, provisioning,
  audit behavior and threat model.
- `tests/test_gmail_broker.py`, `tests/test_gmail_broker_auth.py`: synthetic fixtures,
  mocked HTTP, all requested hard-limit classes, and installer dry-run checks.
- This report and `COMMIT_MESSAGE.txt`.

## Credential location and rollout prerequisites

Name: **`GOOGLE_GMAIL_CONTABO_REFRESH_TOKEN_RW`**.
Project/environment: **`Agents-Core` / `prod`**. Folder: **`/gmail-broker`**.

PLAN §3b puts service runtime credentials in their service project, not Org-Infra.
The name follows the requested provider/job/host/kind/access form. The folder is
an intentional runtime namespace addition: `infisical_setup.py run` injects every
secret from its selected folder, so putting this token at project root would also
give it to unrelated root-folder consumers. Folders prevent accidental injection,
but are not an Infisical permission boundary against project readers.

Before rollout, provision the folder and the same existing OAuth client under
`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`. Consent requires the root
Contabo read identity and an authorized `put` writer identity (the existing helper
defaults to `setup`). The helper does not import any legacy env file. This task
does not create those resources or make external writes.

## Validation performed

Requested command, without `-q` (exit 0; repository pytest settings control display):

```text
$ /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_gmail_broker*.py
........................................................................ [ 66%]
.....s..............................                                     [100%]
107 passed, 1 skipped in 1.93s
```

The Unix socket round-trip test skips on `PermissionError` because the sandbox
refuses Unix socket binding. Dispatcher tests run directly; peer rejection before
read and the connection size cap are tested with fake connections. HTTP is mocked;
auth tests exercise both valid and rejected consent without contacting a service.

Shell syntax and the requested dry-run (exit 0; syntax check emitted no output):

```text
$ bash -n scripts/install-gmail-broker.sh
$ bash scripts/install-gmail-broker.sh install --dry-run
+ groupadd --system mailbroker
+ useradd --system --gid mailbroker --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin mailbroker
+ usermod -aG mailbroker sompong
+ install -d -m 0700 -o mailbroker -g mailbroker /var/log/mailbroker
+ write unit /etc/systemd/system/mooniex-gmail-broker.service (0644 root:root)
[Unit]
Description=Gmail credential broker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c0d756ff
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=GMAIL_BROKER_ALLOWED_UIDS=994
Environment=GMAIL_BROKER_SOCKET_PATH=/run/mailbroker/gmail.sock
Environment=GMAIL_BROKER_LOG_DIR=/var/log/mailbroker
ExecStartPre=+/usr/bin/install -d -m 0750 -o mailbroker -g mailbroker /run/mailbroker
ExecStart=/usr/bin/python3 /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c0d756ff/tools/infisical_setup.py run Agents-Core prod --as contabo --path /gmail-broker -- /usr/bin/setpriv --reuid=mailbroker --regid=mailbroker --clear-groups --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs /usr/bin/python3 /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c0d756ff/runners/gmail_broker.py
Restart=on-failure
RestartSec=5
UMask=0077
LimitCORE=0
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=-/run/mailbroker /var/log/mailbroker

[Install]
WantedBy=multi-user.target
+ chmod 0644 /etc/systemd/system/mooniex-gmail-broker.service
+ chown root:root /etc/systemd/system/mooniex-gmail-broker.service
+ systemctl daemon-reload
+ systemctl enable mooniex-gmail-broker
+ systemctl restart mooniex-gmail-broker
Caller needs a new login/session for group membership. No secrets written to disk.
```

`git diff --check` emitted no errors. Installer dry-run tests additionally verify
root caller rejection and the generated secret-fetch/privilege-drop unit fields.
All new code uses stdlib; no dependency change is required.

## Limitations

- No live Google consent, Infisical write or systemd installation was attempted,
  as required. Those deployment integrations remain to be exercised at rollout.
- The OAuth grant can send at Google; the broker's HTTP allowlist is the no-send
  boundary. Root, project-level Infisical readers, the bootstrap helper and the
  broker UID are trusted. The consent/bootstrap processes transiently hold the
  credential; the broker is its only steady-state application consumer.
- Security-mail detection is deliberately conservative but heuristic. All mail
  remains untrusted; caller/family-gate policy belongs to the other repository.
- Draft updates preserve omitted fields and attachments but normalize the body to
  text/plain. Concurrent Gmail edits are not version-locked.
- Gmail writes and filesystem audit append cannot be atomic together. An audit
  disk failure after a successful write returns `audit_error`; callers must inspect
  state before retrying. An initially unwritable log blocks mutation.
- The final worker contract assigns commit/push to the launcher. Changes are left
  uncommitted for it; `COMMIT_MESSAGE.txt` supplies the requested message, written
  with the contract's `apply_patch` editing tool. No default branch was touched.

## Blockers

- No implementation blocker. Sandbox Unix binding restriction prevents the real
  socket round-trip test here; that test records a skip, with the reason.
- No `MAILBOX.md` was present during the between-step checks.

## Skill learning

- (none)
