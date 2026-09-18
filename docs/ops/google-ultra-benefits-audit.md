# Google AI Ultra benefits audit — YouTube Premium & Jules

Account: pass.gob1@gmail.com (CEO, Google AI Ultra ฿3,500/mo since 2026-09-18).
Read-only audit, no plan changes made. Colab excluded (handed to Cookie Run CTO session).

## Part B — YouTube Premium

### Step 1: one.google.com → Benefits

URL: `https://one.google.com/benefits?g1_landing_page=3` (Thai UI).

7 benefits listed as "ใช้ได้แล้ว" (available now). **YouTube Premium card is
present**, tagged "ใหม่" (New):

> **YouTube Premium • รายบุคคล** (Individual)
> "YouTube และแอป YouTube Music แบบไม่มีโฆษณา ออฟไลน์ และขณะล็อกหน้าจอหรือขณะใช้แอปอื่น รวมถึงสิทธิประโยชน์สุดพิเศษอีกมากมาย"
> (YouTube and YouTube Music app, ad-free, offline, and while screen-locked or
> using other apps, plus many more exclusive benefits.)

No region-restriction or "not available" notice — it renders as a normal
active/available card, individual tier. Did not click "ดูรายละเอียด" (View
details) or any Add-to-plan control.

Screenshot: `docs/ops/screenshots/google-ultra-benefits-audit/01-benefits-page.jpg`
(top of Benefits page, YouTube Premium card visible top-left).

### Step 2: youtube.com/paid_memberships

**Two active YouTube Premium memberships found on the same account** — this is
the trap the task named, confirmed real:

| # | Name | Price | Next billing | Provided by Google One? | Payment method |
|---|---|---|---|---|---|
| 1 | YouTube Premium — Individual (การเป็นสมาชิกรายบุคคล) | not shown as a separate line item (bundled into Ultra) | not shown | **Yes** — card reads "โดย Google One" | n/a on this card |
| 2 | YouTube Premium — Individual (การเป็นสมาชิกรายบุคคล) | **฿199.00/เดือน** (à la carte) | **30 ก.ย. (Sep 30)** | **No** — no Google One label | TrueMoney wallet ending `8330` (`+66*****8330`) |

Both cards carry the same warning banner:
> "คุณมีการเป็นสมาชิกที่ใช้งานอยู่มากกว่า 1 รายการสำหรับบริการ YouTube เดียวกัน"
> (You have more than 1 active membership for the same YouTube service.)

Also present, unrelated to Google One: one **inactive channel membership**
("ตีลังกาดูหนัง" / ตีลังกาเริ่มต้น tier, expires 14 พ.ค. 2026 / May 14, 2026) —
listed for completeness, not a Google benefit.

**Action needed (CEO's call, not done here):** membership #2 (฿199/mo via
TrueMoney) is redundant now that Ultra includes membership #1 via Google One.
Cancelling #2 before the Sep 30 charge is the money-saving move — did not
touch Cancel/Pause/Manage on either card, per instructions.

Screenshots:
- `02-paid-memberships-list.jpg` — both cards + duplicate warning, collapsed view
- `03-paid-memberships-billing-detail.jpg` — membership #2 expanded: ฿199.00/เดือน, "เรียกเก็บเงินครั้งถัดไปในวันที่ 30 ก.ย.", TrueMoney wallet `+66*****8330`, "ปิดใช้งาน" (Deactivate) button visible but **not clicked**.

## Part C — Jules

### Step 1: jules.google.com

`https://jules.google.com` redirected straight to `https://jules.google.com/session`
— loads fine for this account, no login wall. Top-right badge reads **ULTRA**.

Dismissed a first-run feature-intro modal via its "Skip" button (not a GitHub
auth prompt — just onboarding copy). Then opened Settings → General:

> **Plan: Jules in Ultra**
> "You've unlocked Jules' full potential—every tentacle, every tool, fully
> unleashed. This is our most powerful tier, built for serious coding scale
> and agent-first workflows."

Model in use: **Gemini 3.1 Pro**.

**Daily task limit:** found on the main session page, not settings —
`Daily session limit (0/300)` (0 used so far today, cap **300/day**).

**Concurrent task limit:** **not displayed anywhere in the UI.** Checked
Settings → General, the session page body text, and the full page DOM
(`.rate-limit-label` — only one such element exists, the daily-limit one; a
text search for "concurrent" across the page returned nothing). Marking this
**not reached / not exposed by the product**, not "missed."

Screenshots:
- `04-jules-landing-ultra-badge.jpg` — landing page, ULTRA badge top-right, feature-intro modal open
- `05-jules-settings-plan-ultra.jpg` — Settings → General, "Plan: Jules in Ultra" text confirmed

### Step 2: GitHub connect

A **"Connect to GitHub"** button is visible on the landing page (sidebar and
main "Import your repos" card) but it is passive — nothing auto-triggered an
authorization screen. **Did not click it.** No screenshot needed since no
GitHub screen ever appeared; the button itself is visible in
`04-jules-landing-ultra-badge.jpg`'s background context (not fired).

## Budget

- Browser actions used: 30 / 30 (navigate/click/find/screenshot/js calls, see below)
- Screenshots: 5 / 5
- Time: well under 30 min
- route: step 5 (text-first, cheapest tool) — task needed exact wording/numbers off live pages with deep links already given; no API for Google One benefits, YouTube memberships, or Jules. Used `get_page_text`/`javascript_tool` first on every page, screenshots only to document the two required visual captures (Benefits page, membership duplicate) plus 3 more to nail down Jules' plan/limit text since it wasn't in one place.

## Replay Script

- path: none
- covers: n/a
- brittle: n/a — this is a one-time state audit (plan tier, current subscriptions, current limits), not a repeatable operational flow. Re-running it later would need fresh reads anyway since the numbers (billing dates, daily-limit counter) change.

## Skill learning

- WRONG    : (none)
- MISSING  : `browser-operator` skill's cost table doesn't call out that a modal/onboarding "Skip" click and a settings-gear navigation are essentially free (no screenshot needed) — worth a one-line reminder that dismissing a non-blocking onboarding modal is not a "click near a priced action" risk, since it reads similar to the Higgsfield click-blocked-control warning at a skim.
- COSTLY   : Losing the tab group mid-task (`tabs_context_mcp` returned "No tab group exists" right after `select_browser`+navigate) cost one extra navigate+resize+registry-reclaim round trip. Cause unclear — possibly `select_browser` itself resets the MCP tab group. Worth checking whether `select_browser` should always be followed by a fresh `tabs_context_mcp{createIfEmpty:true}` rather than reusing tab IDs from before the select.
- (none)   :
