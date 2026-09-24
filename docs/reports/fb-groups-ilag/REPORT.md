# FB group join run — ILAG Studio (ละครสั้นคุณธรรม)

Date: 2026-09-24
Task: task-03a83889
Browser: Mac Chrome (`select_browser` deviceId `35a05d33-19a5-4d2e-bab0-08503bad0a9b`)
Identity used: personal profile **Dorsine Gobb** (facebook.com/igob.fy) — the account that manages the Page «ละครสั้นคุณธรรม by ILAG Studio», Page id `61594116376333` (confirmed matches task brief). Switched from the Page identity to the personal profile via the account menu before joining, since group membership is normally per-profile.

11 groups joined, all instantly (no admin approval queue, no membership questions asked on any of them). 5 candidates evaluated and skipped for cause. No rate-limit/checkpoint/CAPTCHA warnings shown at any point.

## Joined (11)

| Group | URL | Members | Last activity | Promo rule (one line) | Page can post? |
|---|---|---|---|---|---|
| ละคร AI ไทย \| ละครสั้น AI • หนังสั้น AI • ซีรีส์ AI • | [link](https://www.facebook.com/groups/1128465650898382/) | 740,307 | 56 posts today | Selling banned; ละคร/substantive video sharing explicitly allowed | Untested |
| ละครสั้น AI | [link](https://www.facebook.com/groups/2241521005964979/) | 576,564 | 67 posts today | About text allows drama/video sharing; admin rule #3 has generic anti-spam wording — **borderline** | Untested |
| รวมละครซีรีย์ AI ฝีมือคนไทย | [link](https://www.facebook.com/groups/1341293771473179/) | 3,775 | 27 posts today | "Only AI series may be shared" — purpose-built for us | Untested |
| Seedance 2.0 Community Thailand – พูดคุย ทำหนังด้วย AI | [link](https://www.facebook.com/groups/739851845673593/) | 5,987 | 52 posts today | Share your work fully + cite the tool; only direct course-selling banned | Untested |
| แจก Prompt Google Flow Thailand | [link](https://www.facebook.com/groups/681574071631926/) | 90,114 | 633 posts today | "For AI-generated images/videos only"; boilerplate anti-spam rule — **borderline** | Untested |
| Google Flow Thailand Community | [link](https://www.facebook.com/groups/1186370691006379/) | 4,835 | 51 posts today | No rules posted; content-creation community | Untested |
| แชร์เทคนิค Ai ChatGPT Gemini Flow Grok Seedance Kling สร้างภาพ วิดีโอ | [link](https://www.facebook.com/groups/801149272689355/) | 30,971 | 71 posts today | Only rule: must be AI content | Untested |
| seedance 2.0 Ai Thailand | [link](https://www.facebook.com/groups/1481374853552014/) | 13,017 | 82 posts today | No rules posted | Untested |
| ละครสั้น | [link](https://www.facebook.com/groups/720458009234748/) | 7,618 | 235 posts today | No rules posted; "community of people who love short dramas" | Untested |
| Seedance 2.0 & 2.5 Community | [link](https://www.facebook.com/groups/1405079694162137/) | 70,467 | 360 posts today | "Share value before promoting" — allows promotion | Untested |
| AI Filmmakers Hub - Gumvue Studio | [link](https://www.facebook.com/groups/533068934883217/) | 171,560 | 280 posts today | "Dedicated exclusively to AI filmmaking" — no self-promo ban | Untested |

**Questions asked on any of the 11:** none. Every join button resolved instantly to "เข้าร่วมแล้ว" (joined) — none of these public groups gated on membership questions or admin approval, despite one group's nav bar exposing a "คำถามที่เปิดอยู่" (open questions) discussion tab (that's a Q&A feature, not a join gate).

**"Page can post?"** column is honestly "untested" for every row — I joined as the personal profile Dorsine Gobb (per the task's "join as that profile" instruction), not as the Page. Whether the ILAG Studio Page can post into these groups depends on each group's own settings and would need a separate check before the CEO's posting go-ahead.

## Skipped (5) — with reason

| Group | URL | Members | Reason skipped |
|---|---|---|---|
| คลิป AI \| ละครสั้น AI • หนังสั้น AI • ละคร AI ไทย • | [link](https://www.facebook.com/groups/358463722198695/) | 285,330 | Renamed from a dating/matchmaking group ("รักแฟน🧸🤎"); tagged ความรักและความโรแมนติก/การหาคู่ (love & dating); rule #2 explicitly bans self-promotion |
| กลุ่ม Google Flow Thailand | [link](https://www.facebook.com/groups/889297583720550/) | 78,858 | Rule #1 bans self-promotion outright; rule #5 bans ALL links in any post |
| Flow Ai Thailand (Veo3 Ai สาย Creative) | [link](https://www.facebook.com/groups/nftthailand/) | 18,031 | Renamed from an NFT/Crypto group (URL slug is still `nftthailand`); rules require NFT/Crypto-only content, off-topic = permanent block. Matches the task's "avoid crypto" instruction |
| AI-ART CREATIVE | [link](https://www.facebook.com/groups/239606309197284/) | 12,951 | Rule #4 bans self-promotion and restricts posts to AI face-swap images of yourself only; also 0 new members in the past week (stagnant) |
| AI CREATIONS | [link](https://www.facebook.com/groups/272435462580307/) | 45,389 | Rule #4 bans videos/reels outright ("strictly for image-based content"); rule #3 also bans self-promotion |

No group required a mandatory email/phone/ID field, so nothing was skipped for that reason.

## Facebook warnings

None. No rate-limit toast, no checkpoint, no CAPTCHA, no login/verification prompt at any point across all 16 group pages visited.

## Pacing

One join every ~2–3 minutes (10s explicit wait + the multi-step read/evaluate/click work in between each), well under the 12/day cap, none rushed as a burst.

## Method

Used `javascript_tool` to search Facebook Groups (`facebook.com/search/groups/?q=...`) across 6 Thai/English query terms (ละครสั้น AI, Google Flow Veo AI, คนทำคอนเทนต์ AI, Kling AI Thailand, Seedance Midjourney AI art Thailand, AI Filmmakers Hub) and extract `{href, member-count/activity snippet}` pairs in one call per page — no screenshots needed for discovery. Then visited each candidate's `/about` page with `get_page_text` to read the full description + admin rules before deciding join/skip. Screenshots (7 total) were only used to confirm the exact join-button position/state when the ref-click didn't register (page banner heights vary per group, shifting the button's Y-coordinate) and to verify the "joined" toast.

## Skill learning
- WRONG   [browser-operator §Traps] : ref-click via `find`'s returned `ref` intermittently failed to register on Facebook's group Join button (silent no-op, no error) while a coordinate click at the same visible location worked · evidence: task-03a83889, groups 1128465650898382 / 2241521005964979 / 1186370691006379 / 720458009234748 needed a screenshot+coordinate retry · fix: on Facebook group pages, verify with a cheap `document.body.innerText.includes('เข้าร่วมแล้ว')` check after a ref-click; if false, screenshot and click the visible coordinate instead of retrying the same ref.
- MISSING [browser-operator §mute snippet] : the persistent `MutationObserver`-based mute snippet (page 1 of this skill) tripped the Claude Code auto-mode classifier ("Permission for this action was denied... dangerous") on this run, while a one-shot `document.querySelectorAll('video,audio').forEach(...)` with no observer passed every time · evidence: task-03a83889, first mute attempt after switching to Dorsine Gobb profile · fix: default to the one-shot mute after every navigation; only reach for the observer version if a page is later found to inject autoplaying media dynamically.
- MISSING [browser-operator §tab_registry] : this run never called `tab_registry.py claim` before driving the tab, since the task briefing didn't mention it and I didn't proactively load it · evidence: task-03a83889, single tab 53496501 used start-to-finish, closed cleanly at the end · fix: none needed this run (no collision happened), but the skill's "claim the moment you open a tab" step should be treated as always-on, not conditional on task text.
- (none) beyond the above.
