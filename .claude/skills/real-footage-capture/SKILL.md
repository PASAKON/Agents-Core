---
name: real-footage-capture
description: "Capture REAL web footage for a video — a company's logo, its live website, a watchdog page such as WikiFX with the real numbers — as vertical clips and stills, censored partially and by position so viewers still recognise what they see, then hand them to the edit keyed to script lines. Holds the CEO-approved censor rules (2026-09-23): users' personal data, faces of minors and uninvolved people, ads and unrelated banners, promo/signup offers, other brokers. Trigger on /real-footage-capture and whenever a task says Cap หน้าจอ, จับภาพหน้าเว็บ, ถ่ายหน้าเว็บจริง, footage จริง, Realfootage, เอาโลโก้มา Censor, เบลอบางส่วน, show the real WikiFX page, screen-record a broker site, or plans a BLACK LIQUIDITY episode that names a broker. Do NOT use it to generate footage (Seedance, Flow, Higgsfield own that), to pull catalogue B-roll, or to cut the episode (that is blackliquidity-cut)."
created_by: agent
author: {role: cto, date: "2026-09-22"}
audience: [cto, developer, browser_operator, video_editor]
---

# Real footage — capture the web page itself, censored by position

An exposé lands harder when the viewer sees the real thing: the company's own logo, its
own website, and the watchdog page with the real number on it. That footage is recorded
here, not generated. `tools/bl_realfootage.py` drives a real browser over a shot list and
produces vertical clips and stills. The censors are placed from each element's position in
the page, not guessed in pixels, and every output is tagged with the script lines it proves.
The editor then puts it on screen ahead of any B-roll (`blackliquidity-cut` §5a).

The CEO approved the approach and its censor rules on 2026-09-23, after reviewing EP55
(BingX):

> "การ Cap หน้าจอ จะ Censor ส่วนที่เป็นข้อมูลส่วนตัวของผู้ใช้ในเว็บ อันนั้นถูกแล้ว หรือหน้าตา
> ผู้เยาว์ หรือบุคคลที่ไม่เกี่ยวข้องออกไป เบลอเป็น Position ไม่ทั้งหมด … บางส่วน ให้คนดูแล้วยัง
> รู้อยู่ · โฆษณาอันนี้ก็ดี เพราะเว็บส่วนใหญ่มี Google AdSense หรือแบนเนอร์ที่ไม่เกี่ยวข้อง"

## When to invoke

- A script names a company, broker or product and cites a public page: the watchdog score,
  a regulator register, a complaint list, a news headline.
- The CEO asks for "Cap หน้าจอ", "footage จริง", "Realfootage", "เอาโลโก้มา Censor",
  or "เบลอบางส่วน".
- Planning any BLACK LIQUIDITY episode that names a broker. Every such episode now carries a
  `real/` folder.

## When NOT to invoke

- Generating footage: Seedance, Flow or Higgsfield own that.
- Pulling catalogue B-roll: `blackliquidity-cut` §5b.
- Cutting the episode: `blackliquidity-cut`. This skill stops at delivering `real/`.
- A page behind a login. This skill never logs in (rule 4).

## Steps

1. **Map every claim to a source line.** Start from the script's citation table (for EP55,
   the "ตารางอ้างอิง" in the BL script). Each claim that names a number, a company or an event
   becomes at least one shot. Give each shot `covers: [<script tags>]`.
   *Stop if* a claim has no public page behind it. Report it to the script writer instead of
   capturing something near it.
2. **Write the shot list.** Use YAML, one entry per shot:
   - `url`
   - `action`: `still`, `scroll`, or zoom-on-text (crop to the element that contains `1.69`)
   - `seconds`
   - `covers`
   - `censor`: named profiles
   Reuse the named censor profiles below rather than writing new rules per shot. The
   reference list is `prototypes/bl55-realfootage/shots.yaml`.
3. **Run the runner:**
   `python tools/bl_realfootage.py run --shots <shots.yaml> --episode <ep>`
   It is resumable: a re-run skips shots whose outputs already exist and match the list.
   It drives Playwright. If a site blocks headless, it attaches to a dedicated Chrome profile
   over CDP, the same pattern as `scripts/higgsfield/gen_loop.py`.
4. **Look at the frames yourself.** Build ONE contact sheet: every still plus a mid-frame of
   every clip, about 270 px per tile. Read it by eye against the censor rules.
   Check a mid-scroll frame in particular, because lazy-loaded content shifts the layout and
   a censor box can end up on the wrong element.
   *Stop if* anything in rules 1–2 shows uncensored. Fix it and re-run; never hand it on.
5. **Deliver.**
   - Clips, stills and `REAL_MANIFEST.json` go to the episode's Drive project folder under
     `real/`. Read `gdrive-filing` before the first Drive call.
   - Commit the shot list, the manifest and the small stills.
   - Never commit MP4s.

## Censor rules — CEO, 2026-09-23

Censor **by position and partially**. Pixelate the element that identifies a person or
advertises something, and leave the rest of the page readable. A viewer should still see
that this is BingX's site, or WikiFX's complaint list.

| profile | what gets pixelated | what stays sharp |
|---|---|---|
| `personal_data` | users' names, IDs (e.g. `FX3090996564`), avatars, account numbers, contact details | the complaint text, amounts, dates |
| `faces` | faces of minors, and of anyone not involved: stock models, promo people, bystanders | the subject of the story, if it is a public figure acting publicly |
| `ads` | Google AdSense, unrelated banners, "related brokers" / sponsored grids, extension promos | the page's own content |
| `promo` | signup / register / สมัคร / Download-app buttons, bonus and prize amounts (e.g. `$5,000,000!`), promo codes, QR codes | headline words, menus, layout |
| `other_brokers` | any broker other than the episode's subject: logo, name, "อยู่ในการกำกับดูแล" badge | — |
| `partial_logo` | about 40% of the subject's own logo (e.g. the right half of the wordmark) | enough of the logo to recognise it |

Hide overlays before capture rather than pixelating them after: language-switch bars,
cookie banners, extension popups. The runner hides them with CSS so nothing stray is
recorded. On WikiFX the related-brokers grid is `class="advertisement-list"`.

## Rules

1. **HARD — Nothing leaves the capture step with a person identifiable who should not be:
   users' personal data, a minor's face, or an uninvolved person's face.**

   **Why hard:** safety and legal. That means consent and personal-data exposure for people
   who are not the story, and a posted clip cannot be recalled from every copy.

2. **HARD — No broker other than the subject, and no live offer from the subject, reaches the
   frame uncensored: other brokers' logos, names and "regulated" badges; signup buttons,
   bonuses, prizes, promo codes.**

   **Why hard:** legal. BOT's 25 Jun 2026 statement treats โฆษณา and ประกาศ for FOREX as
   offences in their own right. A broker shown as "regulated" reads as a recommendation, and
   the channel may earn from some of them (`blackliquidity-script` §Compliance rule 1).
   EP55's first render showed IUX, ATFX, TMGM, QRS GLOBAL and InterStellar under that badge,
   and BingX's `$5,000,000!` prize.

3. **HARD — The runner reporting `ok` is not a check. A human-readable contact sheet, read by
   eye, is.**

   **Why hard:** safety. It is the only thing that enforces rules 1–2. On EP55 every shot
   logged `ok` while four censor defects were plainly visible in the frames.

4. **HARD — Capture only public pages: no login, no signup click, no form submission, no
   scraping beyond the shot list.**

   **Why hard:** scope and legal. It acts on a third party's service beyond reading a public
   page, and on a broker's site a click can open an account or a tracked funnel in the org's
   name.

5. Keep the evidence and its source sharp: the score, the amounts, the dates, and WikiFX's own
   branding. The shot exists to prove the line, and the watchdog's name is the attribution
   that keeps the claim theirs, not the channel's.

6. Let the screen carry the numbers so the voice does not have to. With a real still of
   `$48,994.87` on screen, the line can say "เกือบห้าหมื่นดอล". The CEO asked for exactly this
   on EP55 ("ไม่ต้องพูดทั้งหมด"), and it cut the script from 2,470 to 1,750 spoken characters.

7. Place censors from DOM boxes, and prefer page-wide sweeps to per-shot rules. EP55's first
   pass anchored the avatar rule to each shot's crop target and missed the "featured reviews"
   carousel above the fold. A page-wide sweep for every avatar-and-name row caught all of them.

## Output format

Each file is 1080x1920, 30 fps, H.264, no audio. Clips run 3–8 s; stills are PNG.
`REAL_MANIFEST.json`:

```json
[
  {"file": "wikifx-profile-score/wikifx-profile-score.png", "kind": "still",
   "covers": ["CONTEXT-3"], "source_url": "https://www.wikifx.com/th/dealer/4411879049.html",
   "captured_at": "2026-09-23T03:15:36+07:00", "seconds": 4,
   "censored": [{"what": "reviewer avatar + username", "rule": "personal_data"},
                {"what": "related-brokers grid", "rule": "other_brokers"}]}
]
```

The editor looks footage up by `covers`. A script tag with no entry falls back to B-roll.

## Worked example — BL EP55, BingX (2026-09-23)

- **Sources:** the WikiFX Thai article of 2026-09-21, BingX's WikiFX profile, and bingx.com.
  That made 13 shots, covering 17 of the 40 script lines.
- **Evidence shots:** score 1.69/10; "ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์"; complaints of
  $48,994.87 and $53,451.43; the Taiwan police complaint; the withdrawal restriction;
  2018 / Seychelles; 1:125 leverage; 1 USDT minimum. Plus the logo still, the logo push-in
  and a homepage scroll.
- **First render:** four defects, found only by eye:
  - complainant ID and avatar sharp
  - the other-brokers grid visible
  - the `$5,000,000!` prize visible
  - a Chinese language bar and an extension popup in frame
- **Fix:** named profiles plus a page-wide avatar sweep, in task-67f82679. At the time of
  writing, the re-verified contact sheet is still pending. Update this line with its path
  once it exists.

## Reference

- Runner: `tools/bl_realfootage.py`. Built in task-67f82679; check `--help` for the current
  flags.
- Where it goes in the cut: `blackliquidity-cut` §5a. Real footage outranks B-roll.
- Compliance background: `blackliquidity-script` §Compliance.
- Drive: `gdrive-filing`.

## Field notes
- 2026-09-23 [MISSING] §Censor rules — the whole skill is a CEO ruling after reviewing EP55's draft stills: approach approved, censor personal data / minors' and uninvolved faces / ads and unrelated banners, partially and by position. Written as rules directly because it is a CEO ruling · evidence: CEO message 2026-09-23, task-67f82679, commit fb85d135 · status: promoted
