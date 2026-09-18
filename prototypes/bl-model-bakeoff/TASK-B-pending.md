# Task B — make the pipeline behave: Drive rules, the B-roll library loop, money guards

Repo: `mooniex-claudeflow`. Runs AFTER task A (same files). Everything measured
2026-09-18 by the CTO.

## The point of this task

Task A makes a run produce the right thing. This one stops it doing damage on
the way: filing output where the rules forbid, regenerating footage the company
already owns, and spending without a ceiling.

## 1. `AI Drafts/` is never created

`videodrive.js:377-379` creates `Audio`, `Finals` and the Brief doc. IRON-RULES
§27.2 defines FIVE entries and `AI Drafts/` is one of them — it exists so the
editor has a fixed place to read pipeline intermediates. Create it.

## 2. Intermediates are being written to the project folder root

`videogen.js:722` uploads lipsync parts and `:493` uploads footage, both to
`mainFolderId`. §27.5 forbids exactly this ("Writing AI intermediates outside
`AI Drafts/`"), and §27.6 says when you find it you fix the writer rather than
codify the drift. Send both to `AI Drafts/`.

## 3. Generated b-roll never reaches the company library — THE EXPENSIVE ONE

Today a generated clip is named `footage-<keyword>-N.mp4`, lands in that
episode's folder, and is never seen again. The channel has a catalogued library
of 93 clips on Drive, and the pipeline has never once looked at it or added to
it. Every episode pays to generate what the company may already own.

The CEO's rule, in his words: **"ทุกครั้งที่ Generate จะต้องเป็นของสดใหม่เท่านั้น"**
— every generation must produce something genuinely new. Implement it as a loop:

1. **Before generating, grep the catalogue.** `Agents/prototypes/bl-broll-catalog/CATALOG.md`,
   Thai or English, using words from the scene. A `fit=BL` row that matches the
   claim on screen is used as-is and the generation budget stays unspent.
2. **Only generate what the library genuinely lacks.** Budget is one character
   clip and one b-roll clip per episode (`VIDEO_GEN_MAX_NEW_CHAR=1`,
   `VIDEO_GEN_MAX_NEW_BROLL=1`, already set in `.env`).
3. **If the scene you are about to generate is near-identical to something in
   the library, do not generate it — move to a different scene of the script.**
   Duplicates are the failure this rule exists to prevent.
4. **Every new clip must enter the library in the same run**: uploaded to
   `AI Assets/BLACK LIQUIDITY (9:16)` as `(purpose) (D-M-YYYY) (model).mp4`,
   a row appended to `CATALOG.md` and `broll-catalog.json` with Thai and English
   tags, and a 4-frame `sheets/<drive_id>.jpg`. A clip the next episode cannot
   find is a clip that will be paid for twice.

The library grows itself: at two clips per episode it is past 110 within ten
episodes and the generation line trends toward zero.

## 4. Paid calls are wrapped in a retry that re-charges

`videogen.js:444`, `:613`, `:720`, `:1039` wrap paid calls in
`withRetry(attempts=3)` (`lib/retry.js:14`) on top of the `withIdempotentRetry`
that already lives inside `generateLipsync`. The outer one submits a NEW job, so
a flaky network bills up to three times. Remove the outer wrapper from paid
calls and let the idempotent layer do its job — it was written for this.

## 5. The balance gate is blind and the price table is fiction

- `integrations/balance-precheck.js:21` calls `https://fal.ai/api/billing/balance`,
  which **404s**. The live URL is `https://rest.fal.ai/billing/user_balance`.
  §28 has therefore never once seen fal's balance.
- The gate only `console.log`s (`videogen.js:380-385`). §28.1 requires it to
  BLOCK when balance is below the estimate.
- `lib/cost-ledger.js:4-12` is wrong nearly line by line: `sync_labs $0.30/part`
  (really $0.175 on v1), `kling $0.50/clip` (really $0.56 at 5s), it still bills
  ElevenLabs which the pipeline stopped using, and it has no entry at all for
  gemini-tts, Wan or fal whisper. Correct it, and add a per-episode ceiling:
  `EP_BUDGET_USD=3.00`, blocking when the running estimate would cross it.

Measured prices to use, all from the providers' own pages or a live response
on 2026-09-18:

| what | price |
|---|---|
| sync-lipsync v1 | $0.70/min = $0.0117/s |
| Kling v3 Pro | $0.112/s with `generate_audio:false` — the default `true` bills $0.168 |
| Wan 3.0 | $0.05 / $0.10 / $0.20 per second at 480p / 720p / 1080p |
| Topaz upscale | $0.02/s up to 1080p |
| Gemini 3.1 Flash TTS | $1/M input tokens, $20/M output; ~29 audio tokens per second |
| Seedream v4 edit | $0.05/image |

A full episode should land between $1.90 and $2.80. If the ledger says otherwise
after a real run, the ledger is what is wrong — say so rather than adjusting the
budget.

## Proof

`VIDEO_GEN_MOCK_MODE=1 npm run test:mock` green, plus tests for the budget block
and for the catalogue-before-generate decision. No live generation.
