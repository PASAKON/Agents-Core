# Jade Tally (@JadeTally) — BRAND truth

Owner: CMO. Written 27 Oct 2026 from PH CnDrama #3511068d's EP01 (v2 26 Oct, v3 27 Oct) and its upload pack
(`/opt/MoonieXHQ/Work/cn-series/publish/ep01_v3/`). The channel lives on the CEO's own Google account.

## What it is
- A YouTube channel, **Jade Tally** (handle `@JadeTally`), for Thai-narrated long-form serials. The first serial is
  **ลูกคิดประเมินฟ้า**, an original story and not a re-dub of anyone's drama.
- **One channel, many audio languages (CEO 2026-10-27, Q-20261027-0246-806d: "ช่องเดียว Jade Tally (@JadeTally): ไทยหลัก
  อังกฤษเป็นเสียงเพิ่ม").** Thai is the main audio. English is an added audio track on the same video, never a second
  channel or a second upload, so subscribers and watch hours gather in one place. Multi-language audio reached all
  creators in Sep 2025, but YouTube's help page still lists it under Advanced features; not yet checked on this
  channel (Agents-Wikis `research/2026-10-24-youtube-multilang-audio-thumbnail.md`).
- **The job for the viewer:** an evening of Chinese fantasy told in Thai by one narrator. **Real competitors:** the
  Thai channels that narrate official donghua over its own footage, Chinese subtitles left on and some shots mirrored
  to dodge claims (verified, Agents-Wikis `research/2026-10-23-thai-dub-chinese-drama-teardown.md`); the TikTok scroll
  and doing nothing (assumed, not measured). **Where we win:** the same narrated format on an original story and our
  own footage, so no claims, no mirrored shots and no subtitles in someone else's language.
- **The premise of ลูกคิดประเมินฟ้า:** หลัวอี้, a tea server at the Qinglan auction house, carries a cracked jade abacus
  that appraises anything. Every appraisal costs him something from his own life.

## The picture
- 3D donghua-style animation: clearly animated, never photoreal.
- **No text is burned into an episode (CEO 2026-10-26, Q-20261026-0804-62e3: no on-screen text at all).** One
  picture serves every audio language; captions, titles and descriptions live in YouTube's per-language fields. A
  fact the viewer needs is spoken by the narrator: v3 added narrator lines for the six facts v2 lost with its
  overlays (`/opt/MoonieXHQ/Work/cn-series/cut/EP01_v2_lost_hud_facts.md`).
- Loudness: -14 LUFS for the master and for every audio track.

## The voice
- Narrator: ElevenLabs v4 on fal (`elevenlabs/tts/eleven-v4`), voice `Brian`, `stability` 0.5, Thai. It is the same
  voice on every EP.
- English: from EP02 on, the EN script is written to the TH shot timing. EP01's EN track is re-fitted to the TH picture
  in a job of its own (fal, on a spend card).

## Packaging (one EP)
- **Title:** the hook first, then `| ลูกคิดประเมินฟ้า EPxx`. A new viewer knows no series name yet (CMO 2026-10-27).
- **Thumbnail:** 1280x720, a frame from our own render: the strongest face or object, plus the hook in two lines of big
  text (white, then yellow, with a dark outline). No logo. Font and hex values: PENDING, to be measured from the
  thumbnail script.
- **Description:** the premise with no spoilers past arc 1, then the line "เรื่องต้นฉบับ สร้างเป็นแอนิเมชันด้วย AI".
  No links, no handles.
- **YouTube settings:** Altered or synthetic content is Yes on every upload. This is our rule, even though clearly
  animated work is exempt; YouTube says the label does not limit reach. Made for kids: No. Language: Thai.
  Category: Film & Animation.
- **Channel features:** a video over 15 minutes and a custom thumbnail both need Intermediate features (phone
  verification), so the channel is verified before its first upload.
- Channel avatar and banner: PENDING. The jade abacus is the mark.

## Hard rules
1. One upload per EP. Only the current cut goes up, and a re-cut never goes up beside a version that is already public.
2. The words blush, หน้าแดง and หูแดง never appear in a prompt, script, title or description.
3. No `« »` and no em dash in any public text. Run `scripts/check-post-text.sh` before every upload.
4. Every frame comes from our own renders. Another channel's footage is never the base we cut from.
