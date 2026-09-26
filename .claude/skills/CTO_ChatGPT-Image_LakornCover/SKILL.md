---
name: CTO_ChatGPT-Image_LakornCover
description: "Make the cover of a ละครสั้นคุณธรรม / ILAG drama episode the way the CEO approved on «จุดจบของเจ้าหนี้นอกระบบ» (2026-09-24): people from ChatGPT, a custom title LOGO from ChatGPT on pure black, lettered locally in the Thai lakorn poster layout, three options for the CEO to pick. Trigger on /CTO_ChatGPT-Image_LakornCover and whenever an episode needs a cover, poster, thumbnail or key art — 'ทำปก', 'ปกละคร', 'ปกคลิป', 'โปสเตอร์ละคร', 'thumbnail', 'ทำมาให้เลือก 3 แบบ', 'โลโก้ชื่อเรื่อง'. Use instead of typing the title in a font or asking an image model to draw the whole poster. Do NOT fire for YouTube thumbnails of BLACK LIQUIDITY / MYPASAKON (different look) or festival key art (ILAG festival films have their own Poster rules)."
created_by: agent
author: {role: cto, date: "2026-09-24"}
audience: [cto, browser_operator]
---

# Lakorn cover — ChatGPT Plus image + local lettering

## Model scope — read first

**Proven on:** ChatGPT **Plus web UI** (gpt-image, Thai UI, Sep 2026) driven by
`tools/chatgpt_images.py` on the Mac automation Chrome (`--cdp-url http://127.0.0.1:9223`,
profile `~/.flow-automation/chrome-profile`, signed in by the CEO 2026-09-24), plus
`tools/lakorn_poster.py` (Pillow with raqm for Thai shaping). One film: «จุดจบของเจ้าหนี้นอกระบบ».

The lettering and layout half is model-agnostic. The picture half is gpt-image habits:
it drops or misplaces requested text, and it flattens staged compositions into a
group portrait. Another generator (Nano Banana, Seedream, Flow stills) may behave
differently. Test one image before relying on the traps below.

## What it does

Three passes, cheapest control first. People and title are made **separately**:
1. **People.** One ensemble picture from ChatGPT with every character's face plate
   attached, everyday clothes, **no text at all**.
2. **Title logo, three ways.** Three concepts, each built on the story's own prop or
   turn, on pure black. The runner makes them, and `--continue` fixes a wrong letter
   or stray mark in the same chat without re-attaching anything.
3. **Lettering locally.** `lakorn_poster.py` screens each logo onto the people picture
   in the lakorn layout, adds tagline, English title, airtime line and billing, and
   keeps the block inside Facebook's 4:5 feed crop.

The CEO gets three finished 1080×1920 posters and picks one.

## The layout (fact — six Ch3 posters + ~30 more the CEO sent, 2026-09-24)

| slot | real lakorn | ours |
|---|---|---|
| top-left | channel logo | `ILAG STUDIO` |
| top-right | production company | `ละครสั้นคุณธรรม` |
| top, small, in quotes | tagline, often a hook question | `--tagline … --tagline-top` |
| upper 2/3 | the cast, leads biggest | the ChatGPT people picture |
| lower third, centred, biggest element | **title logo designed for this one show** | `--logo` |
| under it | English title, spaced caps | `--english` |
| under that | airtime/date (“คืนนี้ 21:20”, “Coming Soon”) | `--cta "ดูจบในตอนเดียว"` |
| very bottom, tiny | billing block | credits + “ภาพและเสียงสร้างด้วย AI” |

**The title is the identity.** Every real title is hand-made lettering whose shape
tells the story: a wave splash (คลื่นชีวิต), a cupid (น้ำตากามเทพ), stone (หัวใจศิลา),
Arabic-style calligraphy (ฟ้าจรดทราย), raw red brush (ร่าน, เรยา). A stock font typed on
a picture reads as a news or YouTube thumbnail, whatever the layout. The CEO had to ask
"เห็นความเป็นเอกลักษณ์ของตัวหนังสือไหม" before this was understood.

## When to invoke

- An episode is finished or nearly finished and needs a cover, poster or thumbnail.
- The CEO asks for cover options ("ทำปกมาให้เลือก 3 แบบ").
- A cover exists but "ตัวหนังสือไม่ใช่" / "ไม่เหมือนละคร".

## When NOT to invoke

- BLACK LIQUIDITY / MYPASAKON / TRADER UNCUT thumbnails: different channels, different look.
- ILAG festival films (Do Not Disturb, Sorry Sir): their Poster/ folder has its own rules.
- A frame grab from the film as the cover. That is a different, cheaper product; say so if the CEO asks for it.

## Workflow

0. **Inputs, or stop and ask.** You need: every character's face plate, the exact Thai
   title, the ending's secrets (what must NOT appear on the cover), and one line on
   what the story turns on (for the logo motifs and the tagline). If the ending's
   secrets are unknown, ask. A spoiler cover is the one mistake the CEO has ruled on.
1. **People (1 image, ChatGPT).** Attach every face plate, ask for an ensemble in
   everyday clothes with **no text**, faces in the upper two thirds, vertical 2:3.
   Check every face against its plate, and check no ending prop or costume slipped in.
2. **Three logo concepts.** Write each concept from the story's own material: its
   prop, its turn, its genre colour. Banchi's three: the moneylender's ledger with a
   red strike-through (the story's working title was «บัญชี»; the strike is «จุดจบ»),
   cracked antique gold, raw red-and-white brush. Use the prompt template below, one
   JSON item each, and run:
   `.venv/bin/python tools/chatgpt_images.py --cdp-url http://127.0.0.1:9223 --json <Work>/logos/round1.json --out <Work>/logos`
3. **Spell-check every logo letter by letter** at full resolution, one line at a time.
   Fix with a same-chat edit, no re-attach:
   `… --out <Work>/logos --name logo-b2 --continue logo-b --prompt "Keep everything the same; remove …"`
4. **Compose all three** on the same people picture, so the CEO compares logos only:
   `.venv/bin/python tools/lakorn_poster.py people.png out/poster-logo-a.png --logo logos/logo-a.png --english "…" --tagline "…" --tagline-top --cta "ดูจบในตอนเดียว" --title-top 1215`
   Add `--scale 0.88–0.94` when a low face would sit under the title. The tool warns when
   the block leaves the 4:5 feed crop. Look at each poster once, small, before sending.
5. **Send the three to the CEO** and file the chosen one (gdrive-filing decides where).

### Logo prompt template (worked on banchi, 3 of 3 spelled right)

```
Create a TITLE LOGO (lettering only) for a Thai prime-time TV drama (lakorn) poster.
The Thai text must be exactly this, character for character, in two lines:
line 1, smaller: <ส่วนเล็ก>
line 2, much larger: <ส่วนใหญ่>
Spell it exactly as written, every vowel and tone mark included (<name the tricky marks>).
No other words at all: no English, no subtitle, no signature, no watermark.
Background: solid pure black (#000000) edge to edge, nothing else in the frame.
Landscape 3:2 image; the lettering centred and filling about 85% of the width.
No <ending props>, no banknotes, no coins.
Style concept: '<name>' — <the motif, how it touches the letters>. Every letter still perfectly readable.
```

## Rules

1. **HARD: Never use the OpenAI API for covers. Use the ChatGPT Plus web UI through the runner.**

   **Why hard:** money. The CEO already pays for Plus and ruled on it
   (2026-09-23: "ดีกว่าเสียเครดิต API ChatGPT เพราะฉันจ่าย GPT PLUS อยู่แล้ว"). Any API
   call is spend he did not approve.

2. **HARD: Nothing from the ending on the cover.** Characters wear everyday clothes,
   and whatever the story reveals last stays off it.

   **Why hard:** scope. CEO ruling 2026-09-23: "ตำรวจใส่ชุดธรรมดา ไม่งั้นปกคลิปจะเฉลยตอนจบ".
   A published cover cannot be un-seen.

3. **HARD: No banknote showing a royal portrait, drawn or photographed.**

   **Why hard:** legal and safety. Thai law protects the royal image and the currency's
   likeness. On banchi, Flow painted portrait banknotes six times from context alone, so
   ask for "no banknotes, no coins" outright.

4. The title is a logo made for this story, never a typed stock font. System fonts
   (Sukhumvit, Thonburi, Kanit) are for the tagline, airtime and billing only.
5. Ask gpt-image for people with **no text**, and for the logo on its own. Asked for both
   at once, it dropped the title on the first pass 3 of 3 times and put it at the top.
6. A mark under a consonant reads as a vowel. Debris hanging under ห, ร or บ looked like
   ุ ("หุ", "บุ") on the cracked-gold logo; one same-chat edit removed it.
7. A pale logo over a pale shirt needs the tool's dark halo (built in since 2026-09-24).
   Check the smallest line («จุดจบของ») at poster scale, not only the big one.
8. The runner's traps (image turn is `section[data-turn]`, first paste can land nothing,
   never click Send twice in a live chat) are fixed in the tool. If it misbehaves, read
   `ledger.json` and use `--recover <name>` before generating again.

## Output format (to the CEO)

```
ปก 3 แบบ (ส่งไฟล์ด้านบน)
- A · <concept> — <one line on why it fits the story>
- B · …
- C · …
สะกดชื่อเรื่องถูกทุกแบบ (ซูมเช็คทีละตัว) · ไม่มีอะไรจากตอนจบ · อยู่ในกรอบฟีด 4:5
เลือกแบบไหน หรือจะแก้ตรงไหนต่อในแชตเดิมได้ (~2 นาที/รอบ)
```

## Worked example — «จุดจบของเจ้าหนี้นอกระบบ», 2026-09-24

- People: `Work/task-d206afca/out/cover-3-ensemble-c.png` (6 characters; the officer in a grey polo).
- Logos: `Work/task-d206afca/logos/` + `ledger.json`: logo-a-ledger, logo-b-cracked-gold → b2 (debris
  removed) → b3 (brighter), logo-c-brush; b, b2 and b3 in one chat.
- Posters: `Work/task-d206afca/out/poster-logo-{a-ledger,b-gold,c-brush}.png`. **CEO picked A** (ledger + red strike).
- Took 3 rounds of CEO feedback to get here: title at the top → typed font in the right
  place → custom logo. This skill starts at round 3.

## Reference

- Tools: `tools/chatgpt_images.py` (runner, `--continue`, `--recover`), `tools/lakorn_poster.py`
- Story and format: `CTO_Story_ThaiMoralDrama` · filing: `gdrive-filing` · browser rules: `browser-operator`
- Memory: `feedback_study_genre_references_for_identity.md`

## Field notes

- 2026-09-24 [MISSING] cover (moved from thai-moral-drama 2026-09-25) — the story skill said nothing about the episode cover. First try (ChatGPT, title in the prompt) put the title across the TOP; CEO: "คนแบบนี้ถูกแล้ว ติดแค่ข้อความ … มันจะมีจุดที่อยู่ประจำของมัน". Real Ch3 lakorn posters (ลายกินรี, คลื่นชีวิต, ลดา, เลือดเจ้าพระยา, 18 มงกุฎ) share one layout. The layout itself is §The layout, generating the people only and lettering with `tools/lakorn_poster.py` is §Workflow 1 and 4, and no face-changing cop clothes on a cover is rule 2 (text removed here on 2026-09-25 so the layout is written once) · evidence: task-d206afca, b5296b42 · status: promoted
- 2026-09-24 [MISSING] cover (moved from thai-moral-drama 2026-09-25) — the whole cover workflow now lives in its own skill, `CTO_ChatGPT-Image_LakornCover`; the 09-24 cover note above is its first draft. What the CEO approved: the title is a LOGO made for this story (ledger + red strike on banchi), not a typed font; people and logo come from ChatGPT separately; three options, CEO picks · evidence: task-d206afca, CEO picked A 2026-09-24 · status: promoted
- 2026-09-26 [MISSING] §Workflow 3 — **2 of 3 logos misspelled the tone mark**: gpt-image drew the mark above ช in ตาชั่ง as a hook (mai tho ้ → "ชั้ง") on the rusted-scale and pebble concepts; only the gold one drew mai ek ่ as a clean vertical bar. Visible only in a crop of the mark at full resolution, not at poster scale. One same-chat edit ("the tone mark above ช must be MAI EK ่ — one short straight vertical stroke — not mai tho ้") fixed it with the design unchanged. Name the exact tone mark by its Thai name AND its shape in the first prompt · evidence: taachang Work/task-c2723478/out/cover/logo-a-scale vs logo-a2, CEO picked A → posted with A2 · status: pending
- 2026-09-26 [MISSING] §Model scope — the ChatGPT web UI changed on 2026-09-26 (send button aria-label ส่ง, no section[data-turn], images in a gallery with blob: src) and a multi-line JSON prompt fails the runner's paste check; both fixed in tools/chatgpt_images.py 3c70e00b. If the runner fails every image with "send did not register" or "timed out waiting for the image" while the chat shows a picture, the UI moved again: read the live DOM before retrying · evidence: cover run1-run4 logs · status: pending
