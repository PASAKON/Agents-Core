# BL EP59 / EP60 topic scout (task-eb88fd7b, script_writer)

Scouted 2026-10-01 20:30 to 21:15 ICT on Contabo, headless Chromium (Playwright), public pages only, no login.
Source = WikiFX only. Start page: https://www.wikifx.com/th/news.html (the news list, sorted newest first).
The WikiFX.th Facebook page (https://www.facebook.com/wikifx.th) opens to a login wall for a logged-out
visitor: header and intro only, no posts. It was not used. Nothing on this page comes from Facebook.

Window: 24 Sep 2026 or later. The news list showed 19 items from 24 Sep to 1 Oct; 9 of them are single-broker reviews.
All 9 articles and all 9 dealer profiles were opened and read in full by me (not read from a snippet).

IB check (criterion c): grep of the repo (`docs`, `prototypes`, `knowledge`, `config`, `output`) and the wikis
(`Agents/Wikis`, `Agents/Rules`) for GVD, Goldenburg, GBFX, mirrox, BTFX, CTFOREX, Murrentrade: zero hits.
The only brokers the repo and wiki say the channel earns from are XM and Exness (rebate fact sheet,
`2026-09-28-brief-forex-ib.md`). Weltrade is excluded by the brief. So none of the four below is known as an IB broker,
but "no hit" is not a confirmation. Each episode's RUNLOG.md carries
"IB status unconfirmed, CEO to confirm before posting" at the top.

## The 4 candidates

| # | broker | WikiFX profile | the article that makes it fresh | what the page states (one line) | the Thai question people would type |
|---|---|---|---|---|---|
| 1 | **GVD Markets** | https://www.wikifx.com/th/dealer/3938681280.html | 29 Sep 2026 https://www.wikifx.com/th/newsdetail/202609296884498721.html | WikiFX's field team (survey dated 22 Oct 2024) found no GVD Markets office at the Limassol address it was given; the page shows a withdrawal-problem complaint, one of them a 2,800 USDT "tax" asked before a withdrawal; the CySEC licence number the firm cites (411/22) is marked "not verified" | **GVD Markets ถอนเงินได้ไหม** |
| 2 | **GB (Goldenburg Group)** | https://www.wikifx.com/th/dealer/8341918460.html | 1 Oct 2026 https://www.wikifx.com/th/newsdetail/202610019604717978.html | WikiFX states the CySEC Cyprus licence (no. 242/14, from 2014) now has status Revoked, the profile carries a red warning dated 2026-10-01, and the related-company box lists GOLDENBURG GROUP LTD (Cyprus) with status "ยกเลิกการจดทะเบียน" (registration cancelled) | **GB broker ใบอนุญาตจริงไหม** |
| 3 | mirrox | https://www.wikifx.com/th/dealer/1782355680.html | 25 Sep 2026 https://www.wikifx.com/th/newsdetail/202609256724304228.html | claims a MISA (Comoros) licence, but WikiFX says some sources show none; no MT4/MT5, trades only in its own app; founded 2024 | mirrox ถอนเงินได้ไหม |
| 4 | BTFX | https://www.wikifx.com/th/dealer/6901857724.html | 24 Sep 2026 https://www.wikifx.com/th/newsdetail/202609249974987617.html | WikiFX's team went to the Malta address it lists and found no company sign, no reception and no BTFX logo; the profile shows "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์" | BTFX มีสำนักงานจริงไหม |

The search questions are my guess at what a Thai viewer types, built from the broker name plus the two question words
the channel's own data says people use. They are not measured. WikiFX's 22 Apr 2026 GVD article says "GVD Markets
ถอนเงินไม่ได้" and "GVD Markets โกง" are common searches; that is WikiFX's claim, not measured here.

Also read and dropped (reason in one clause): CTFOREX 30 Sep (shares a registered address with other brokers; a
survey page exists but no complaint pages, so thin), Murrentrade 29 Sep (1:2000 leverage is a selling point, and
no complaint or survey on the page), EZ SQUARE 28 Sep (no complaint pages), SPOVA 24 Sep (new broker, 1 complaint
page, a mostly generic review), GBE brokers 25 Sep (page shows a valid CySEC licence and a score that reads as an
endorsement), Capital.com 28 Sep (a regulated broker's feature piece: reads as promotion), Weltrade 30 Sep
(excluded by the brief, EP58).

## Criteria applied to the top two

| criterion | GVD Markets | GB (Goldenburg) |
|---|---|---|
| (a) named broker, WikiFX page opened and read by me | yes: profile, 29 Sep article, 22 Apr and 22 Jun articles, 3 survey pages (2 UAE "Good", 1 Cyprus "Danger"), 3 complaint pages | yes: profile, 1 Oct article, 1 survey page, 2 complaint pages |
| (b) a cost, withdrawal or licence fact the viewer can check, not a rumour | withdrawal complaints (on WikiFX, viewer opens them) + the office check + the CySEC number the viewer can search at CySEC | the licence status: viewer looks up no. 242/14 at CySEC and the register shows it |
| (c) not Weltrade, not a known IB broker, different from the other pick | yes; angle = withdrawal + "is there an office" | yes; angle = licence revoked and company struck off |
| (d) enough public content for 10-13 stills | 12 stills planned | 11 stills planned |

## Why GVD Markets is EP59 and GB is EP60

1. **GVD has the stronger, more checkable story for this channel.** The withdrawal question is what the channel's
   viewers search, it comes with three complaint pages the viewer can open, and a field survey that
   WikiFX publishes in full. The firm runs a Thai page (`gvdmarkets.com/home-th/`, listed on its WikiFX profile) and WikiFX's April article
   mentions a complaint from Thailand, so Thai viewers exist (my reading; not measured).
2. **GB's headline is a pure licence fact**, which is the most defensible type of claim, but its complaint pages are
   from February 2021 (two, both from Hong Kong, a loss of "80,000" with the currency not stated) and its survey (31 May 2019) says the
   office exists. Older complaints make the withdrawal angle weaker, and the content is thinner than GVD's.
   It is the better contrast to EP59, so it goes second.
3. **The two angles differ**: EP59 = withdrawal + "no office found", EP60 = "licence revoked, company struck off".
   Neither repeats EP58's (Weltrade) story shape of two profiles, two scores.
4. The newest facts: GVD article 29 Sep, GB article and the red warning card both 1 Oct. Both clear the 24 Sep line.

Open point for the CMO: both picks are low-score brokers. WikiFX's own warning wording ("โปรดหลีกเลี่ยง") appears
on screen in the red card of GB. As on EP58, it is WikiFX's text on screen; the voice does not repeat it.
