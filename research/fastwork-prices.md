# Fastwork.co market research — 6 categories (2026-09-17)

Source: the live listing API (`https://search.fastwork.co/indexes/products_th_prod/search`,
Meilisearch), not the marketing HTML. See `tools/fastwork_prices.py` to
re-pull this data any time — no browser or agent needed. Commission structure
(17% / 12% / 7% tiered by job value, buyer pays 0) is out of scope here — it
was already confirmed and isn't re-derived.

**How the numbers were gotten:** opened `/video-editing`, found the client
fetched `search.fastwork.co/indexes/products_th_prod/search` (Meilisearch) on
page load, and found the search key (a public "search-only" token, not a
secret — see `tools/fastwork_prices.py` header) baked into every page's
`__NEXT_DATA__.runtimeConfig.MEILISEARCH.API_KEY`. Category page counts (9,060
/ 84 / 427 etc.) were cross-checked against the live rendered page text for 3
of the 6 categories and matched exactly, confirming `subcategory.slug` is the
right filter field. `review_count` isn't a Meilisearch-sortable attribute on
this index, so top-10-by-reviews is computed by pulling every listing in a
category (cheap fields only: price/reviews/rating/title) and ranking locally
— there is no server-side pagination cap (a 6,481-listing category came back
whole in one call).

**Delivery days: not available.** The search index has no delivery-time
field (checked the full hit schema — no `delivery_days`/`lead_time`/similar
key exists). That number only exists per-package on each listing's own detail
page, which would mean opening all ~60 top listings individually — out of
scope for this pass. Every "delivery days" cell below is `n/a`, not a guess.

---

## 1. video-editing — `/video-editing`

- **9,060 listings**
- price (THB): min **0** | p25 **1,000** | median **1,000** | p75 **1,000** | max **350,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 1,000 | 1,383 | 4.95 | n/a | ตัดต่อวีดีโอทุกรูปแบบ รีวิว/หนังสั้น/Vlog คุณภาพ(1-2วัน) |
| 2,000 | 319 | 4.97 | n/a | รับตัดต่อวีดีโอทุกรูปแบบ 🎬 คุณภาพจัดเต็ม Vlog \| YouTube \| สัมภาษณ์ |
| 1,000 | 260 | 4.89 | n/a | รับตัดต่อคลิปวีดีโอ Vlog l TikTok l Reel |
| 1,000 | 247 | 4.88 | n/a | รับตัดต่อ VDO, Vlog, video present ทำคลิปลงยูทูป วีดีโอทุกประเภท |
| 1,000 | 215 | 4.94 | n/a | รับตัดต่อวิดีโอ TikTok Reels Shorts YouTube Facebook Ads พร้อมซับ Motion |
| 1,000 | 207 | 4.75 | n/a | บริการตัดต่อวิดิโอ ตามความต้องการ เช่น CONTENT/VLOG/LIFESTYLE/โปรโมท |
| 1,000 | 182 | 4.93 | n/a | รับทำซับไตเติ้ล และตัดต่อวิดีโอ ราคาดีที่สุด! |
| 1,000 | 174 | 4.96 | n/a | รับตัดต่อคลิปสั้นสำหรับ Reel,Tiktok,Vlog,Short |
| 1,000 | 173 | 4.98 | n/a | ตัดต่องานเล่าเรื่อง การตลาด การเงินและการลงทุน ประวัติศาสตร์ สัมภาษณ์ |
| 1,000 | 171 | 4.83 | n/a | รับตัดต่องานวิดีโอระดับมือโปรทุกประเภท เสร็จไวภายในไม่กี่วัน |

**Pricing read:** the market is a wall of ฿1,000 starting prices — 3 out of 4
listings sit at exactly ฿1,000 (that's why p25/median/p75 are all 1,000), and
every top-10-by-reviews seller (1,300+ reviews at the top) is *also* at
฿1,000–2,000. This is a race-to-the-floor category: a new shop with 0 reviews
would have to enter at ฿1,000 or below just to be visible next to sellers who
already have hundreds of reviews at that same price. The ฿350,000 max is a
single outlier (agency/enterprise package), not a realistic reference point.

---

## 2. ai-video-editing — `/ai-video-editing`

- **151 listings**
- price (THB): min **300** | p25 **300** | median **350** | p75 **800** | max **10,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 800 | 15 | 4.72 | n/a | สื่อจาก AI พร้อมตัดต่อสไตล์การ์ตูน |
| 1,000 | 3 | 4.42 | n/a | ล้านวิว!!ด้วยAI content (รับตัดFacelessVDOบนtiktok/instagram reel) |
| 300 | 2 | 5.00 | n/a | รับทำภาพ AI / วิดีโอ AI / เสียงพากย์ AI / Voice Clone ตามบรีฟ พร้อมใช้ |
| 300 | 1 | 5.00 | n/a | รับตัดต่อคลิป Reels / TikTok / Facebook มืออาชีพ \| แนวไวรัล ดูทันสมัย |
| 500 | 1 | 5.00 | n/a | รับตัดต่อวิดีโอมืออาชีพ ไว ด้วยเทคนิค AI-Assisted \| NEXDECK |
| 300 | 1 | 5.00 | n/a | ตัดต่อวิดิโอแบบสั้น/ยาว ด้วยCapCut ลง tt,reels |
| 300 | 1 | 5.00 | n/a | ตัดต่อ&ai |
| 500 | 0 | — | n/a | รับทำคลิป AI คลิปการ์ตูนพูดได้ คลิป AI สั้น กระชับ น่าดู โฆษณาแบรนด์ |
| 399 | 0 | — | n/a | รับตัดต่อวิดีโอคลิปสั้น/คลิปยาว แนวตั้งแนวนอน และวิดีโอAi Video Vlog |
| 1,980 | 0 | — | n/a | รับตัดคลิป วิดีโอ Ai สร้างแบรนด์ สร้างช่อง |

**Pricing read:** thin category (151 listings) with a low review ceiling —
the #1 seller by reviews has only 15. Half the top-10 have **zero reviews**,
meaning it's easy to get *listed* here but there's little proven demand yet.
Entry price of ฿300–500 would be competitive; there's no established leader
charging a premium to undercut.

---

## 3. ai-video — `/ai-video`

- **604 listings**
- price (THB): min **300** | p25 **300** | median **590** | p75 **1,490** | max **100,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 899 | 71 | 4.99 | n/a | สร้างวิดีโอ AI Video โฆษณา วิดีโอโปรโมทสินค้าระดับมืออาชีพ |
| 500 | 55 | 4.97 | n/a | สร้างวิดีโอคอนเทนต์ AI โฆษณา \| เอไอมันทำ |
| 1,000 | 37 | 4.91 | n/a | รับสร้างและตัดต่อ AI Video สำหรับ TikTok Reels Shorts YouTube |
| 500 | 37 | 4.85 | n/a | AI Video Generation / วีดีโอAi/รับผลิตสื่อเกี่ยวกับAi |
| 900 | 37 | 4.99 | n/a | VDO Production ด้วย AI ครบวงจร สร้างคลิปสั้น โฆษณา และวิดีโอโปรโมทสินค้า |
| 1,000 | 33 | 4.93 | n/a | รับทำ AI Video โฆษณา จากไอเดียสู่วิดีโอระดับมืออาชีพ ด้วย AI |
| 999 | 26 | 4.76 | n/a | รับผลิต AI Video มืออาชีพ ตั้งแต่คอนเซปต์ถึงวิดีโอพร้อมใช้ \| CEO@KT |
| 400 | 26 | 4.83 | n/a | Ai.รับทำวิดีโอโปรโมท สินค้า บริการ ,เพจ,เฟสบุ๊ก ตต. ด้วยai 100% |
| 500 | 26 | 4.93 | n/a | รับทำ วีดีโอเนื้อเรื่องสั้น 1 นาที + เสียงพากย์ และดนตรีประกอบ |
| 500 | 25 | 4.93 | n/a | Gen ภาพ/วีดีโอ AI, โฆษณา, Reel, โปรโมทสินค้า ร้านค้า, Intro, แนวเหนือจ |

**Pricing read:** more mature than `ai-video-editing` (604 listings, top
sellers have real review counts in the 25–71 range) but still cheap —
established leaders sit at ฿500–1,000. A new shop entering at ฿400–500 would
be in line with proven sellers, not undercutting into "too cheap to trust"
territory.

---

## 4. ai-tool-and-saas — `/ai-tool-and-saas`

- **84 listings**
- price (THB): min **300** | p25 **500** | median **1,500** | p75 **5,000** | max **1,400,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 300 | 6 | 4.71 | n/a | ( Chat GPT Plus / Gemini Ai Pro / Grok Premium ) ใช้ส่วนตัว |
| 1,500 | 3 | 5.00 | n/a | AI Generations Images & Video รับติดตั้งโปรแกรม-สอนเพื่อใช้งาน ai |
| 505 | 2 | 4.63 | n/a | รับสร้างตามคำสั่งลูกค้าด้วย AI |
| 490 | 2 | 5.00 | n/a | ติดตั้ง AI ส่วนตัวบนคอม \| Ollama + Open WebUI \| ข้อมูลไม่ออกจากเครื่อง |
| 1,500 | 2 | 5.00 | n/a | รับทำเว็บแอปผู้ช่วยเรียน สรุปเอกสาร ทำ Quiz และ Flashcard ใช้งานง่าย |
| 30,000 | 0 | — | n/a | ระบบ License Plate Carpark อัจฉริยะ |
| 1,000 | 0 | — | n/a | รับทำ AI OCR อ่านใบเสร็จ ใบกำกับภาษี และเอกสารอัตโนมัติ |
| 399 | 0 | — | n/a | Chat GPT Plus ราคาถูก |
| 990 | 0 | — | n/a | รับทำ AI ครบวงจร: Chatbot / AI Agent / Local LLM / Image & Video Gen |
| 6,000 | 0 | — | n/a | ระบบ AI Automation ลดงานซ้ำซาก-บันทึกขาย สต็อก บัญชี รายงาน อัตโนมัติ |

**Pricing read:** smallest, least-proven category (84 listings, top seller
has only 6 reviews). The ฿1,400,000 max is almost certainly a custom
enterprise SaaS build, not representative. This is the category with the
most room to differentiate on positioning rather than price — nobody has
built review-based trust yet, so a well-presented ฿500–1,500 offer competes
on quality of listing, not on being cheapest.

---

## 5. web-development — `/web-development`

- **6,481 listings**
- price (THB): min **1,200** | p25 **1,500** | median **2,900** | p75 **5,000** | max **2,200,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 1,500 | 523 | 4.97 | n/a | แก้ bug PHP |
| 1,500 | 257 | 4.97 | n/a | รับทำ WEBSITE + รองรับ Google Facebook |
| 5,500 | 202 | 4.91 | n/a | บริการทำเว็บไซต์ทุกประเภท ใช้งานง่ายทำงานเร็ว |
| 4,990 | 188 | 5.00 | n/a | รับทำเว็บไซต์ทุกประเภท ออกแบบทันสมัย รองรับทุกอุปกรณ์ |
| 3,500 | 142 | 4.91 | n/a | รับทำเว็บไซต์ รองรับ Responsive |
| 4,900 | 120 | 5.00 | n/a | บริการรับทำเว็บไซต์ครบทุกประเภท ใช้งานง่าย โหลดไว ทำงานรวดเร็ว |
| 5,500 | 120 | 4.92 | n/a | ออกแบบและสร้างเว็บไซต์ทุกประเภท เน้นความสวยงาม คุยง่าย งานดี งานเร็ว |
| 1,500 | 109 | 5.00 | n/a | รับเขียนโค้ด Google Appscript |
| 8,000 | 103 | 4.90 | n/a | รับทำเว็บไซต์ ด้วยทีมงานมืออาชีพ จดทะเบียนบริษัทมานานกว่า 15 ปี |
| 1,500 | 100 | 4.94 | n/a | แก้บั๊ก ดูแล แก้ไขเว็บไซต์ โฮสติ้ง PHP MySQL |

**Pricing read:** by far the biggest and most saturated of the 6 (6,481
listings). Two clear price tiers among proven sellers: small fixes/quick
jobs (แก้ bug, Appscript) at ฿1,500 with 100–500+ reviews, and full website
builds at ฿3,500–8,000 with 100–200 reviews. A new shop competing on
full-site builds needs to either match the ฿3,500–5,000 band with a strong
portfolio or find a narrow-enough niche (a specific stack, a specific fix
type) to avoid competing head-on with 500-review incumbents.

---

## 6. seo — `/seo`

- **427 listings**
- price (THB): min **600** | p25 **990** | median **2,750** | p75 **7,000** | max **185,000**

| price THB | review count | rating | delivery days | title |
|---|---|---|---|---|
| 1,600 | 1,566 | 4.93 | n/a | รับทำ SEO Offpage เพิ่ม Traffic + Backlink คุณภาพสูง ดันเว็บหน้าแรก Google |
| 3,000 | 945 | 4.90 | n/a | รับทำ SEO ใหม่! ทำ SEO AI ติดอันดับ ChatGPT Gemini และสร้าง Backlink |
| 600 | 511 | 4.80 | n/a | สร้าง Backlink จากเว็บที่มีค่า DA สูง 40 ลิ้งค์ |
| 900 | 492 | 4.83 | n/a | ติดจรวจ ทำ SEO Backlinks ด้วย 2 Tier Link Pyramid แรงๆ |
| 5,500 | 471 | 4.86 | n/a | ทำ SEO ขั้นสูง เทคนิคเฉพาะ 3 tire pyramid สายขาว |
| 800 | 321 | 4.61 | n/a | รับโพสเว็บบอร์ด 200 เว็บ รับสอนโพส ด้วยเทคนิค SEO จาก CPALL |
| 4,500 | 206 | 4.80 | n/a | ทำ SEO คุณภาพสูง แรงๆ 100 Backlinks จาก 10 Platforms+++ |
| 1,500 | 138 | 4.98 | n/a | รับทำ SEO + Backlink ติดอันดับ Google & AI (ChatGPT, Gemini) |
| 990 | 136 | 4.80 | n/a | บริการทำ SEO, AEO, AIO และ GEO รายเดือนแบบครบวงจร |
| 5,000 | 136 | 4.89 | n/a | รับทำ Guest Post สายคุณภาพ (DR40+) เพิ่มพลัง SEO ด้วย Backlink แบบ Dofollow |

**Pricing read:** highest review counts of all 6 categories by far (1,566 at
the top — an order of magnitude above every other category's leader), meaning
this is the most trust-saturated market here. The top sellers cluster at
฿600–1,600 for backlink/offpage packages and ฿3,000–5,500 for
"advanced"/pyramid packages. A new shop would need to enter well under ฿990
(p25) just to compete for attention against a seller with 1,500+ reviews at
similar prices — SEO looks the hardest of the 6 to break into on price alone.

---

## Cross-category summary — where a 0-review shop should price

| category | listings | median THB | top seller reviews | read |
|---|---|---|---|---|
| video-editing | 9,060 | 1,000 | 1,383 | saturated, price-floored at ฿1,000 |
| ai-video-editing | 151 | 350 | 15 | thin, low trust — easy entry at ฿300–500 |
| ai-video | 604 | 590 | 71 | growing, entry at ฿400–500 is credible |
| ai-tool-and-saas | 84 | 1,500 | 6 | smallest, least proven — win on positioning |
| web-development | 6,481 | 2,900 | 523 | huge, two-tier (fix ฿1,500 / full build ฿3,500–8,000) |
| seo | 427 | 2,750 | 1,566 | most trust-saturated, hardest to break in on price |

**For MoonieX specifically:** `ai-video`, `ai-video-editing`, and
`ai-tool-and-saas` are the 3 categories where the *AI* framing is a
differentiator rather than a commodity race — review counts are still low
(6–71 at the top) and prices (฿300–1,500) leave room for a well-presented
first listing to get picked. `video-editing` and `seo` are both won on volume
of reviews already banked by incumbents (1,000+), not on price — a new
account there is competing for scraps below the price floor. `web-development`
is the biggest opportunity by raw job volume but requires committing to one
of its two price tiers rather than trying to straddle both.

---

## Terms of Service — the 3 requested clauses

Source: `https://fastwork.co/terms` (redirects to
`https://static.fastwork.co/contents/terms`). Full ToS text (~35,500
characters) was read and grepped for each clause.

**(a) Delivering AI-generated work** — no clause found. Searched for AI /
"ปัญญาประดิษฐ์" / "Generative" / "สร้างโดย" — the only "AI" hit in the whole
document is the company's contact-info footer, unrelated to service delivery.
Fastwork's ToS does not mention AI-generated deliverables at all, positively
or negatively.

**(b) Subcontracting / reselling someone else's work** — no clause found.
Searched for "จ้างช่วง" / "รับช่วง" / "ผลงานของผู้อื่น" / "แอบอ้างผลงาน" /
"ลอกเลียน" and variants — none appear. The closest related clause is a
catch-all against self-dealing for promotional benefit (quoted below), but it
does not address subcontracting or reselling by name.

**(c) One account per person** — **clause exists.** Verbatim (Thai), from the
prohibited-conduct section:

> "การมีบัญชีมากกว่าหนึ่งบัญชี หรือผู้ใช้งานใช้ข้อมูลส่วนบุคคลของบุคคลอื่นมาสมัครใช้งาน"
>
> "การซื้อขายบัญชีผู้ใช้งานให้กับบุคคลอื่น"

(Translation for context, not part of the quote: "Having more than one
account, or a user using another person's personal information to register"
/ "Buying or selling a user account to another person" — both listed as
prohibited acts, with the company's judgment on violations stated as final
and non-appealable.)

The adjacent catch-all clause, quoted for completeness since it's the closest
thing to (b):

> "การกระทำการใด ๆ อันมีพฤติการณ์หรือลักษณะให้ตนเองหรือบุคคลอื่นได้รับสิทธิประโยชน์ที่ไม่มีสิทธิได้รับตามกฎหมาย ซึ่งรวมถึงแต่ไม่จำกัดเพียง การจ้างงานตนเองเพื่อหวังผลประโยชน์จากการส่งเสริมการขายและไม่ได้มีวัตถุประสงค์เพื่อการจ้างงานอย่างแท้จริง ฯลฯ"

(This bans self-hiring/fake-job schemes for promo abuse — not subcontracting
or AI-work resale specifically.)
