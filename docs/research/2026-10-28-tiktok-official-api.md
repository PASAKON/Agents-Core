# TikTok official API fit-check (@mistergraph + lakorn/ILAG) — 2026-10-28

> **Evidence level:** `search_web` only returned *synthesised summaries* with redirect links, and direct page fetch was denied by the sandbox. I never opened a developers.tiktok.com / business-api.tiktok.com page. Every claim below is therefore from search summaries (which cited tiktok.com pages plus third-party blogs) unless it says otherwise. Anything not confirmed on a primary page is **UNVERIFIED**. URLs are the canonical doc paths; deep links marked (?) are from memory.

## สรุปภาษาไทย (สำหรับ CEO)
- **ตัวที่เหมาะที่สุด = Display API + Login Kit** ใช้ได้กับบัญชีส่วนตัว/creator ธรรมดา ไม่ต้องเปลี่ยนเป็น Business ดึงได้: views, likes, comments, shares ต่อวิดีโอ (`video.list`) และ followers, likes รวม, จำนวนวิดีโอ (`user.info.stats`)
- **Display API ไม่ให้ watch time / retention** และไม่มีข้อมูลย้อนหลังเป็นกราฟ ได้แค่ตัวเลขสะสม ณ ตอนที่เรียก → ต้องเก็บ snapshot รายวันเอง
- **watch time / retention ต่อวิดีโอ** มีเฉพาะ Business API (organic "TikTok Accounts") ซึ่งต้องเป็นบัญชี **Business** + ต้องกรอกฟอร์มขอสิทธิ์ + ผ่าน app review → หนักกว่า และรายละเอียดฟิลด์ยัง UNVERIFIED
- **Research API ใช้ไม่ได้** (เฉพาะนักวิจัยสถาบันการศึกษา/ non-profit ใน US/EEA/UK/CH ไม่รับบริษัท/ครีเอเตอร์) **Creator Marketplace API ใช้ไม่ได้** (เฉพาะพาร์ทเนอร์) **Marketing API** เป็นของโฆษณา ไม่ใช่สถิติ organic
- **Content Posting API ไม่จำเป็น** CEO โพสต์เองบนมือถืออยู่แล้ว (ถ้าใช้: แอปที่ยังไม่ audit โพสต์ได้แบบ private `SELF_ONLY` เท่านั้น)
- **ต้องมี:** เว็บไซต์จริง, Privacy Policy + Terms URL, verify โดเมน/URL prefix, วิดีโอ demo, คำอธิบายการใช้แต่ละ scope; รีวิวใช้เวลาราวหลายวัน–3-4 สัปดาห์ (UNVERIFIED)
- **ทดสอบถูกสุด (ฟรี):** สร้างแอปใน **Sandbox** เพิ่ม @mistergraph เป็น target user ให้ CEO กดอนุญาตบนมือถือเอง แล้วเรียก `/v2/user/info/` + `/v2/video/list/` ด้วย curl 1 ครั้ง
- ความเสี่ยงหลัก: ยังไม่ได้เปิดหน้าเอกสารหลักด้วยตัวเอง (ดูหัวข้อสุดท้าย)

## 1. Which APIs fit, and for which account type
| API | What it is | Personal/creator account | Business account | Fit |
|---|---|---|---|---|
| **Display API + Login Kit** — https://developers.tiktok.com/doc/display-api-overview | OAuth2 user token → read own profile + public videos | **Yes** (designed for any TikTok user who authorises) | Yes (same OAuth) | **Best** |
| **Content Posting API** — https://developers.tiktok.com/doc/content-posting-api-get-started | Push video/photo to account | Yes | Yes | Not needed |
| **Research API** — https://developers.tiktok.com/doc/research-api-get-started | Public-data queries (video/user/comment) | n/a | n/a | **No**: academic/non-profit researchers in US/EEA/UK/CH only; commercial users and creators ineligible |
| **Business/Marketing API** — https://business-api.tiktok.com/portal/docs | Ads (Marketing API) + organic "TikTok Accounts" (`/business/get/`, `/business/video/list/`) | **No** for organic endpoints (UNVERIFIED: switch to Business needed) | Yes, authorised via Business Center / TikTok for Business | Only for retention |
| **Creator Marketplace (TTCM) API** | Creator discovery/campaign data | n/a | Approved partners only | **No** |

- Marketing API reporting covers *paid* campaigns/Spark Ads; it does not return organic video stats (UNVERIFIED, from general knowledge).
- Organic Business API needs an "Accounts API Access Application Form" before app creation (search summary, UNVERIFIED).

## 2. Metrics returned and history window
**Display API** (`https://open.tiktokapis.com`):
| Endpoint | Scope | Fields (exact) |
|---|---|---|
| `GET /v2/user/info/` | `user.info.basic` | `open_id, union_id, avatar_url, display_name` |
| same | `user.info.profile` | `bio_description, is_verified, username, profile_deep_link` |
| same | **`user.info.stats`** | `follower_count, following_count, likes_count, video_count` |
| `POST /v2/video/list/` (cursor, `max_count` ≤20) | **`video.list`** | `id, title, video_description, create_time, cover_image_url, share_url, duration, embed_link, like_count, comment_count, share_count, view_count` |
| `POST /v2/video/query/` (≤20 `video_ids`) | `video.list` | same fields, refreshes expiring cover URLs |
- Docs: https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info · https://developers.tiktok.com/doc/tiktok-api-v2-video-list · https://developers.tiktok.com/doc/tiktok-api-v2-video-query
- **History:** only *current cumulative totals* for *public* videos (lists all, newest first). No time series, no per-day deltas, **no watch time, no retention** (absence UNVERIFIED — not seen in any summary). Build a daily snapshot job.

**Business API organic** (all UNVERIFIED field/scope names; summaries disagreed):
- Account `/business/get/`: followers, profile views, likes/comments/shares, audience countries/genders/activity; daily metrics window **~60 days** (supermetrics-sourced); 24–48 h lag.
- Video `/business/video/list/`: `video_views`, likes, comments, shares, reach, `total_time_watched`, `average_time_watched`, `full_video_watched_rate`, `video_view_retention`, `impression_sources`. Scope shown as "TikTok Accounts > Account User / Get Account Media"; one blog claims a `video.insights` scope — **UNVERIFIED**.

**Research API:** `view_count, like_count, comment_count, share_count` etc. for *anyone's* public videos; irrelevant (ineligible).

## 3. Content Posting API
- **Direct post** — `POST /v2/post/publish/video/init/`, scope **`video.publish`**; caption, `privacy_level`, comment/duet/stitch flags set via API. Must call `/v2/post/creator_info/query/` first.
- **Draft / inbox upload** — `POST /v2/post/publish/inbox/video/init/`, scope **`video.upload`**; video lands in creator's app inbox as a draft, creator finishes caption and publishes in-app.
- **Unaudited client limits:** `privacy_level` must be `SELF_ONLY`; error `unaudited_client_can_only_post_to_private_accounts` if target account is public; max **5 posting users per 24 h**. Per-token rate ~6 req/min; ~15 posts/day/creator (both via blogs, UNVERIFIED).
- **Audit unlocks** public direct post (`PUBLIC_TO_EVERYONE`). Checks UX per Content Sharing Guidelines (https://developers.tiktok.com/doc/content-sharing-guidelines): creator nickname from `creator_info`, privacy dropdown with no default, comment/duet/stitch off by default, commercial-content toggle, Music Usage Confirmation, no watermark. Reported 2–4 weeks (UNVERIFIED).
- Whether inbox upload escapes the audit entirely: summaries say yes; **UNVERIFIED** (the `video.upload` scope still needs app approval).

## 4. App approval
1. Create app at developers.tiktok.com (needs a TikTok login — **not done**), add products Login Kit + Display API, request scopes.
2. Sandbox is available without review for testing; only listed target users can authorise (target-user cap ~10: UNVERIFIED).
3. For production, submit review. Required (search summaries of https://developers.tiktok.com/doc/app-review-guidelines): unique app name (no "TikTok"), icon, **live public website** (not login-walled/localhost), **Privacy Policy + Terms URLs** visible on the site, **URL-prefix/domain ownership verification** (mandatory for apps created after 2024-09-09 and for Content Posting), **demo video** of real end-to-end flow (login → consent → feature; no slides/mockups), per-scope justification text.
4. Review time: "several days to 3–4 weeks" (blogs + one tiktok.com summary) — **UNVERIFIED**; rejections common over demo/privacy issues.
5. An internal-only tool still needs a public site and policy pages. Check whether an existing Mooniex/ILAG domain can host them.

## 5. Recommendation and cheapest test
- **Use Display API + Login Kit** with `user.info.basic,user.info.stats,video.list`. Works on personal accounts, no Business switch (which may cost features, e.g. commercial music: UNVERIFIED). Covers views, likes, comments, shares, followers. One OAuth per account (@mistergraph, each lakorn/ILAG page); CEO taps "Authorize" on his phone once; refresh tokens keep it unattended. Snapshot daily to get trends.
- **Watch time/retention:** not in Display API. Options: read manually in TikTok app Studio, or later pursue Business API organic if the gap is worth the Business switch + form + review. Park it.
- Skip Research, TTCM, Marketing, Content Posting.
- **Cheapest real test (one step, $0):** create a **Sandbox** app (Login Kit + Display API), add @mistergraph as target user, have the CEO approve on mobile, then run `curl -X POST 'https://open.tiktokapis.com/v2/video/list/?fields=id,create_time,view_count,like_count,comment_count,share_count' -H 'Authorization: Bearer <act.…>' -d '{"max_count":20}'`. A returned JSON with counts proves the fit. Whether sandbox returns live `video.list` data is UNVERIFIED; if not, the answer comes only after app review.

## Not checked / risk
- **No primary page opened** (fetch denied; search summaries only). All scope/field names, limits and review times need confirming on the pages linked above before building.
- Not verified: exact Business API scope names, retention field availability, history window (60 d is third-party), Business-account switch side effects, Thailand availability.
- Not verified: sandbox limits, whether `video.list` works for private/unlisted videos (assumed public only), refresh-token lifetime, Display API rate limits.
- Not checked: ToS clauses on internal analytics use, cost of any partner tool, how the lakorn/ILAG pages are owned (personal vs Business).
- Risk: docs change often; audit/review times are anecdotal; no sign-up or login was performed.
