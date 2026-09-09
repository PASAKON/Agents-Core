# LINE OA "สมพงษ์" — setup report (task-1052f525)

Created 2026-09-09 via https://entry.line.biz/form/entry/unverified, CEO-approved
(order relayed by CTO session cto-e3c8345f, 2026-09-09), under LINE Business ID
already logged into Chrome (10 accounts). Accepted the LY Corporation data-use
notice and the Messaging API terms as part of onboarding — both covered by the
CEO's pre-approval to create this account and accept LINE's terms.

## Account facts

| Field | Value |
|---|---|
| Account name | สมพงษ์ |
| Basic ID | `@590jexxd` |
| Add-friend URL | `https://lin.ee/t05lyDC` |
| Provider | MoonieX (existing provider, not a new one) |
| Channel ID | `2011528242` |
| Business category | ธุรกิจบริการ (Services) → ธุรกิจบริการ(อื่นๆ) (Other) — no exact "อื่นๆ" at the top level, so picked the closest to services per brief |
| Company/business name | MoonieX |
| Email | pass.gob@hotmail.com (pre-filled default, never typed) |

## Toggle states (final, verified on LINE Developers Console → Messaging API tab)

| Setting | State |
|---|---|
| Allow bot to join group chats | **Enabled** |
| Auto-reply messages (ข้อความตอบกลับอัตโนมัติ) | **Disabled** |
| Greeting messages (ข้อความทักทายเพื่อนใหม่) | **Disabled** |
| Webhook URL | `https://webhook.mooniex.com/line/@sompong` |
| Use webhook | **ON** |
| Channel access token (long-lived) | Issued |

Webhook **Verify** was intentionally not pressed (brief says it 404s until the
CTO onboards the account row).

## Secrets

Written to `~/.secrets/sompong-line.env` (chmod 600, umask 077 at creation) —
channel ID, channel secret, channel access token, Basic ID, add-friend URL.
Not reproduced here or anywhere else in the worktree, chat, or screenshots.

## What I could not set / skipped (in scope of the brief)

- Did not request account verification (blue badge) — not asked for.
- Left the Messaging API "Privacy policy" / "Terms of service" URL fields on
  the provider-link step blank — optional, brief didn't specify values.
- Did not press Webhook "Verify" per explicit instruction.

## Replay script

None. One-time account creation + settings flow through two web UIs with
CEO-approval gates at each irreversible step (account creation, terms
acceptance, provider linking); not a repeatable automation candidate.
