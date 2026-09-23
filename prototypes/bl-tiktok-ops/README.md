# BL TikTok ops — CTA-loop watcher (task-c01b0b99)

CEO, 2026-09-23: the CTO now owns BLACK LIQUIDITY's CTA loop — make the clip →
post → once a day check views, new comments and new inbox messages. 100%
script, no SendPulse, Playwright + a dedicated Chrome profile, same pattern as
`tools/flow_shoot.py` / `scripts/higgsfield/gen_loop.py`.

## Step 1 — logged-in session: BLOCKED on the CEO

- Dedicated Chrome profile created: `~/.bl-tiktok-automation/chrome-profile`
  (never the CEO's everyday profile). Launch: `bash scripts/bl-tiktok/launch-chrome-debug.sh`
  (CDP port 9224 — 9222 is Higgsfield's, 9223 is Flow's, so nothing collides).
- QR login confirmed live 2026-09-23 (this task, read-only probe, logged out):
  `https://www.tiktok.com/login` lists 7 `div[data-e2e="channel-item"]` login
  options; the first, visible text **"ใช้รหัส QR"** (Use QR code), navigates to
  `https://www.tiktok.com/login/qrcode`, which renders the QR as a bare
  `<canvas>` (170x170 CSS px). No password or code was ever typed.
- `python3 tools/bl_tiktok_watch.py login-qr` captures a fresh QR PNG (the code
  expires in ~1-2 minutes, so it is re-captured right before each notify, never
  reused). Per the task brief: **stop here and wait for the CTO's go** — the
  CEO scans the QR with the TikTok app on the black_liquidity account. Nothing
  past this point in Step 2/3 can run for real until that scan happens.
- No alternative to QR login was needed — TikTok's QR flow was reachable and
  worked exactly as expected on the first try.

## Step 2 — DM-rule verification inside the account: NOT YET DONE (blocked by Step 1)

`prototypes/bl-reply-bot/RESEARCH.md` (commit `0d360f9c`, main) already answered
these from **secondary sources** (TikTok's own developer/business-API docs are
JS-rendered SPAs that block automated fetch — see that doc's §3c caveat). This
task's job is to open the real black_liquidity account and confirm each one
directly, citing the UI text or help-page URL seen. **That confirmation could
not run this task** — no logged-in session exists yet (Step 1 above). Once the
CEO's scan lands, whoever resumes this task should check, in this exact order,
in the automation Chrome (port 9224):

1. **Can BL message a commenter who never DM'd first?** Open any commenter's
   profile from a video's comment list → does a "Message" button exist? Does
   it open a composer, or refuse/redirect? RESEARCH.md's secondary-sourced
   answer: **no — TikTok requires the user to message first** (SleekFlow,
   Qiscus, Respond.io all describe the same Business Messaging API rule).
   **Do not actually send anything** if the composer opens.
2. **Window/limit after the user messages first.** RESEARCH.md's
   secondary-sourced answer: **48-hour window, ~10 business messages cap**
   (anti-spam). Confirm by checking Settings → Messages / the account's own
   help article if TikTok surfaces one in-app (Business Suite accounts
   typically do); note whichever UI text or URL is actually seen.
3. **Account type** (personal / creator / business) — read directly off
   Settings → Manage account, or the badge next to the account type in
   TikTok Studio. This changes which messaging rules apply (business
   accounts get the Business Messaging API rules above; personal/creator
   accounts have a plainer DM model with no documented 48h/10-message rule).
4. **Inbox settings** — Settings → Privacy → Messages (who can message the
   account: everyone / mutuals / no one), and whether a **native
   auto-reply/keyword-reply** feature exists in TikTok itself (a genuinely
   zero-cost option, if it exists — this has not been confirmed either way
   in any source read so far).

Record each finding as **fact + where seen** (UI text quoted, or the exact
help-page URL opened in-app) — not a repeat of RESEARCH.md's secondary
sourcing, which this step exists specifically to upgrade to firsthand.

## Step 3 — `tools/bl_tiktok_watch.py`: BUILT, unverified against the live DOM

Read-only, zero-model, Playwright-over-CDP. `login-qr` / `run` / `status`
subcommands — see the file's module docstring for the full design. 20 unit
tests pass against saved JSON fixtures (`tests/fixtures/bl_tiktok/`) for
everything that isn't the browser itself: the raw-JSON adapters, new-since-
last-run diffing, delta computation, and the ledger.

**What is NOT verified, because no logged-in session was reachable:**
- The actual TikTok Studio / creator-center JSON field names
  (`extract_video_stats_from_raw` et al. guess from TikTok's *public* API
  naming conventions — `play_count`/`digg_count`/etc. — since the internal
  Studio API shape is undocumented).
- The actual XHR endpoint URL patterns `BLTikTokBrowser._collect_json_from`'s
  callers search for (`collect_video_stats_raw`, `collect_inbox_raw`).
- `is_logged_in()`'s detection heuristic.

**The first live run must be a human-watched dry pass**, same as
`tools/flow_shoot.py`'s own documented first-run caveat: open TikTok Studio's
content list, comments, and inbox with browser devtools network capture open,
confirm the real endpoint(s) and JSON field names, and correct the three
places named above. The diff/ledger/summary logic underneath does not need to
change regardless of what that correction finds.

## Ledger

`state/bl-tiktok/state.json` (current per-video stats + seen comment/DM id
sets, atomic write) and `state/bl-tiktok/events.jsonl` (append-only: every
new comment/DM this tool has ever surfaced, with its discovery timestamp).
Neither is committed to git — runtime state, like `state/banchi/*.tsv`.

## Proposed daily schedule (NOT installed — CTO/CEO call)

A launchd `~/Library/LaunchAgents/com.mooniex.bl-tiktok-watch.plist`,
`StartCalendarInterval` once a day (e.g. 09:00, human pace — never more often,
per the task brief), running:

```
scripts/bl-tiktok/launch-chrome-debug.sh   # idempotent — restarts the profile if it died
/Users/gob/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/bl_tiktok_watch.py run
```

`StandardOutPath`/`StandardErrorPath` to `state/bl-tiktok/run.log`, so the
daily summary (and any `STOP`/`NOT_LOGGED_IN`/`VERIFICATION_WALL` line) lands
somewhere a human or a future CTO check-in can read it — this task does not
wire up a push/alert path (LINE, LungNote, etc.) for a stopped run; that is a
follow-up decision, not assumed here. Not installed this task, per the brief
("Propose, but do NOT install").

## Step 4 — `tools/bl_tiktok_cta.py`: BUILT, unverified against the live DOM (task-8df13432)

The CTA-loop decision engine on top of Step 3's watcher: per the CEO's
verbatim flow, checks whether a commenter can be DM'd directly and either
sends the deliverable + confirms on the comment, or invites them to DM us;
tracks who DM'd us from which episode in `state/bl-tiktok/cta.sqlite`
(contacts / questions / action_log / planned_actions tables); a general-chat
fallback for unrecognized DMs is a **stub only** (logged + surfaced in the
summary — the model/cost for real auto-chat is a later CEO decision).

**Shadow mode is the default and this task never runs `--live`.** Every
decision is written to `planned_actions` and the run summary
("would DM @handle: ...", "would invite @handle: ..."); the two outward
adapters (`send_dm`, `reply_comment`) are only ever called under `--live`,
capped at `--cap` (default 10) actions/day with a randomized human-pace
delay. Every outgoing text is checked against the reply pack's `never_say`
list and "no URL except the ones already in the pack" before it is planned
or sent — a failed check blocks the action and logs why.

Reply packs are read-only here, written by task-6cc24a28 at
`prototypes/bl-reply-packs/EP<n>.yaml` (schema: `episode`, `video_id`,
`cta.keyword`/`variants`/`deliverable`/`dm_message`/`comment_reply_dm_sent`/
`comment_reply_dm_invite`, `never_say`, `escalate_to_human`).

22 unit tests pass against fake adapters and fixture packs
(`tests/test_bl_tiktok_cta.py`, `tests/fixtures/bl_tiktok_cta/`): keyword
matching incl. Thai spelling drift (เช็ค/เช็ก, โบรค/โบรก, extra spaces,
emoji), every state-machine path (DM-able / not-DM-able / known-contact DM /
unknown-sender DM / repeat comment → no double delivery), the never_say/URL
guard, the daily cap, and shadow mode never touching `send_dm`/`reply_comment`.

**What is NOT verified, because no logged-in session was reachable (same
blocker as Step 3):**
- `can_dm(handle)` — guessed as "open `https://www.tiktok.com/@<handle>` and
  look for `button[data-e2e="message-button"]`"; TikTok's Business Messaging
  rules (`prototypes/bl-reply-bot/RESEARCH.md`) suggest a commenter who never
  messaged first is usually not DM-able, but the actual button/selector is
  unconfirmed.
- `send_dm(handle, text)` — guessed selectors
  `div[data-e2e="message-input-area"]` / `[data-e2e="message-send-button"]`.
- `reply_comment(comment_id, text)` — guessed selectors keyed off
  `[data-comment-id="…"]` with `comment-reply` / `comment-reply-input` /
  `comment-reply-submit` sub-elements; TikTok Studio's real comment-list DOM
  has never been opened by this account.

The first live check must be the same human-watched dry pass as Step 3: open
TikTok Studio's comment list and a commenter's profile with devtools open,
confirm the real selectors, and correct the three methods on
`BLTikTokCTABrowser` (`tools/bl_tiktok_cta.py`). Everything above that class —
matching, safety checks, the state machine, the cap, the summary — does not
need to change regardless of what that correction finds.
