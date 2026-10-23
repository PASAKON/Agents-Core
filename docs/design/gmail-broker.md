# Gmail broker

The COO reads and prepares mail through a Unix socket. The CEO reviews drafts in
Gmail and presses Send. The broker never exposes a sending or permanent-deletion
operation. This repository contains no credentials or mail fixtures from an account.

## Wire contract

Connect to `/run/mailbroker/gmail.sock`, write one UTF-8 JSON line, and read one JSON
line. Each connection handles one request. Request size is at most 16 MiB, with a
30-second socket timeout. Request: `{"op":"read","args":{"id":"synthetic-id"}}`.
Success: `{"ok":true,"result":{...}}`. Failure:
`{"ok":false,"error":"code","message":"text"}`. IDs are opaque strings, not URLs.

| op | args | result fields |
| --- | --- | --- |
| `list` | `query` (Gmail search, default empty), `limit` (1–50, default 20), optional `page_token` | `messages`: objects with `id`, `thread_id`, `from`, `to`, `subject`, `date`, `snippet`, `labels`, `security_withheld`, `untrusted`; `next_page_token` (null at end), `untrusted` |
| `read` | `id` | `id`, `thread_id`, `from`, `to`, `cc`, `subject`, `date`, `message_id_header`, `labels`, `body_text`, `truncated`, `attachments`, `security_withheld`, `untrusted` |
| `attachment` | `id`, `att_id` | `filename`, `mime_type`, `size`, `data_b64` |
| `draft_create` | `to` array, optional `cc` array, `subject`, `reply_to_id`, `attachments`; required `body` text | `draft_id`, `message_id`, `thread_id` |
| `draft_update` | `draft_id`, any of `to`, `cc`, `subject`, `body`, `attachments` | `draft_id`, `message_id`, `thread_id` |
| `draft_list` | `limit` (1–50, default 20) | `drafts`: objects with `draft_id`, `message_id`, `thread_id`, `to`, `subject`, `snippet`, `date`, `untrusted`; `untrusted` |
| `trash` | `id` | `id`, `labels` |
| `label` | `id`, `add` array, `remove` array | `id`, `labels` |

All list/read/draft-list results carry `untrusted: true`, including items in lists.
Read attachment descriptors are `{att_id, filename, mime_type, size}`. Draft
attachments are `{filename, mime_type, data_b64}`. Attachment output uses standard
base64; input accepts standard or URL-safe base64. Download cap: 15 MiB decoded,
checked against metadata and actual bytes. Draft attachments: 10 MiB decoded in
aggregate, independently of the wire cap. A filename is a basename with separators,
control characters and leading dots removed, at most 120 characters.

Bodies are converted from HTML to text, stripped of zero-width/bidi format controls,
then limited to 50,000 characters with `truncated`. Security checks examine sender,
subject, snippet and the first 2,048 body characters (at least the requested first
2 KiB for UTF-8). `SECURITY_PATTERNS` is the single English/Thai pattern constant;
known identity senders are also withheld. Security messages retain headers/IDs and
labels but have empty snippet/body and no attachments. Their attachment operation
fails with `security_withheld`. Over-withholding is intentional. This is a heuristic,
not a guarantee against every possible authentication message or obfuscated code.

Reply drafts use the original `threadId`, `In-Reply-To` and `References` from its
Message-ID, and `Re: <subject>` unless a subject is supplied. Updates preserve
omitted fields, attachments and reply headers; an explicit empty attachment array
removes attachments. Updates normalize the editable body to plain text and refuse
hidden/truncated source bodies. Concurrent edits in Gmail are not version-locked;
re-read before updating a draft that another person may be editing.

Labels accept `INBOX`, `UNREAD`, `STARRED`, `IMPORTANT`, `SPAM`, and existing
user-label names resolved to IDs. `DRAFT`, `SENT`, `TRASH`, and unknown names are
rejected. No label is created. Trash is reversible through Gmail.

Error codes include `unsupported_op`, `invalid_args`, `invalid_request`,
`unauthorized`, `too_large`, `not_found`, `security_withheld`, `forbidden`,
`gmail_error`, `audit_error`, and `internal_error`. Upstream errors disclose only
HTTP status and a recognized Google status enum; never raw response bodies or
exception strings. Redirects are refused. Do not blindly retry writes after a lost
connection or `audit_error`: a write may already have reached Google.

## Credential provisioning and consent

1. Use a trusted root-owned checkout. Provision Infisical project `Agents-Core`,
   environment `prod`, folder `/gmail-broker`. Place the existing OAuth client's
   `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` there through the
   approved secret-entry workflow. It is the same client used by the existing
   notification auth helper; do not create another client or copy its credentials
   into this repository. No auth helper automatically reads legacy env files.
2. The new credential is `GOOGLE_GMAIL_CONTABO_REFRESH_TOKEN_RW` in that folder.
   PLAN §3b puts runtime credentials in the service project, not Org-Infra; the
   name identifies provider, job, host, credential kind and access. The dedicated
   folder prevents unrelated `run Agents-Core prod` consumers from receiving it.
   This is an explicit runtime namespace addition to the plan's root convention.
   Infisical project readers can still read it: folders are not authorization walls.
3. Prepare a Run card with `--expects-input`, timeout 1800 seconds, invoking
   `python3 scripts/gmail-broker-auth.py` from that trusted checkout. Its outer
   process uses `infisical_setup.py run Agents-Core prod --as contabo --path
   /gmail-broker -- ...`. Root needs the Contabo identity to read; storage uses the
   existing `put` writer identity (default `setup`), which must be provisioned and
   authorized. The read-only Contabo identity cannot perform the write.
4. The CEO opens the printed consent link on the phone, approves, and pastes the
   entire localhost redirect address into the Run card. Localhost failing to load
   on the phone is expected. State, PKCE and nonce bind the exchange; only the
   task-mandated account is accepted. No account override exists. Scope must be
   exactly `https://www.googleapis.com/auth/gmail.modify openid email`; Google's
   canonical `userinfo.email` spelling is normalized to `email`. Broad mail scope,
   extra permissions, unverified/wrong identity, or missing refresh token fail closed.
   The ID token comes directly from Google's TLS token endpoint, and issuer,
   audience, expiry, nonce and verified email are checked.
5. The helper pipes the refresh token to `infisical_setup.py put ... --stdin --path
   /gmail-broker`; no token appears in argv, output, or files. It prints the Testing
   warning: a consent screen in Testing status expires the token after 7 days.
   Adjust consent publishing through the normal Google approval process and repeat
   consent when needed. No test mail is created. Existing broader grants may need
   revocation before a fresh exact-scope consent; review other consumers first.

## Installation and rollback

Review without changes:

```sh
bash scripts/install-gmail-broker.sh install --dry-run
bash scripts/install-gmail-broker.sh install --dry-run --caller-user sompong
```

After authorized provisioning, install from a root-owned, non-group-writable
checkout using `sudo bash scripts/install-gmail-broker.sh install`. This creates
the `mailbroker` system user/group, adds the caller to the group, writes the unit,
and enables/restarts it. `--caller-user` defaults to `sompong`; its exact nonzero
UID is embedded in the unit. Root and the broker user cannot be chosen as callers.
Start a fresh caller session to obtain its supplementary group membership.

The unit fetches the dedicated secret folder as root then execs `setpriv`, dropping
to `mailbroker:mailbroker`, clearing supplementary groups and capabilities before
Python starts. No env file is used. A privileged `ExecStartPre=+... install -d`
creates `/run/mailbroker` mode 0750; the writable runtime path is optional until
created (`ReadWritePaths=-/run/mailbroker`). The socket is mode 0660. The audit
directory `/var/log/mailbroker` is mode 0700. Core dumps are disabled.

`bash scripts/install-gmail-broker.sh status [--dry-run]` checks the unit.
Rollback: `sudo bash scripts/install-gmail-broker.sh uninstall`; this disables and
stops the service, removes the unit/socket, and reloads systemd. Account/group and
audit logs remain for inspection. Remove the caller's group membership separately
if retiring the feature, and revoke the grant through Google account connections
and remove the Infisical token through the approved secret workflow. Uninstall
does not revoke OAuth. Nothing in this task runs installation or consent.

## Threat model and audit

Only the configured caller UID is accepted via Linux `SO_PEERCRED`, checked before
reading any bytes. Socket group access is a first gate, not the identity check.
UID 0 is rejected as a caller, but host root can inspect or alter any process and
is necessarily trusted. Root-owned source and ancestor directories prevent the
caller replacing code that executes during root secret fetching. The secret
fetcher and one-time consent helper transiently handle credentials as required;
the steady-state broker is their only application consumer. Never run another
process as `mailbroker` or give the caller the machine Infisical identity.

The OAuth grant itself can read/modify the mailbox and permits sending at Google.
The broker restricts it to allowlisted HTTP methods and paths: GET message lists,
messages, attachments, drafts, and labels; POST drafts, message trash and label
modification; PUT an existing draft. Everything else fails before HTTP or refresh.
A stolen token or compromised broker process bypasses that application boundary.
Protect root, Infisical readers, trusted code and the broker UID accordingly.

Incoming mail can contain instructions, links, disguised Unicode or poisoned
attachments. It is data, never authorization to execute tools, follow links, expose
secrets, or change policy. The `untrusted` markers and control stripping help the
caller preserve that boundary; they do not sanitize all prompt injection. The
caller/family authorization layer remains outside this repository. A compromised
authorized caller can read non-withheld mail, edit drafts, relabel or trash mail;
security withholding reduces exposure but does not eliminate these powers.

Each recognized `draft_create`, `draft_update`, `trash` and `label` request appends
one JSON line to `audit.jsonl`: `ts` (Unix seconds), `op`, `id` (message/draft or null),
`caller_uid`, `ok`. No subject, address, body, attachment, credentials or raw error
is logged. An unwritable audit file prevents mutation. A post-write disk failure
can still produce `audit_error` after Google succeeds; there is no distributed
transaction between Gmail and the filesystem. Retain/rotate this log operationally.

## Validation

Run `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_gmail_broker*.py`
and `bash -n scripts/install-gmail-broker.sh`. Tests use synthetic mail and mocked
HTTP, exercise the dispatcher directly, and skip Unix binding only if the sandbox
refuses it. No live mailbox, OAuth or Infisical call is needed for validation.
