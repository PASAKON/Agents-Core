# EP07 Cast & Voice Registry (`cast.md`)

Episode: **EP07 — กฎ 5 ข้อของคนเฝ้าศาลาตั้งศพกะดึก วัดป่าห้วยหมอก (The 5 Rules of the Night Watchman at Funeral Pavilion No. 4)**
Voice Model: `fal-ai/gemini-3.8-flash-tts` (`$0.045` per 1,000 billed characters; `tools/fal_tts.py`).
Per CEO picks (27 Nov 2026, `Q-20261127-1347-90cd`): Multi-voice cast with `Algenib` as the narrator plus one distinct Gemini preset voice and one-line `style_instructions` per character, with every line as its own call in `voice/job.json`.

---

## Cast Table

| Role ID | Name (TH / EN) | Age & Role | Visual Look (Embed verbatim in ChatGPT Plate Prompts) | Gemini Voice Name | One-Line `style_instructions` (`fal-ai/gemini-3.8-flash-tts`) |
|---|---|---|---|---|---|
| `NARRATOR` | ผู้บรรยาย (Channel Storyteller) | 62, Night-legend narrator | *(Off-screen narrator; never appears in plates)* | `Algenib` | `Thai grandfather in his 60s telling a night legend. Deep warm gravelly voice close to mic, fluent brisk storytelling pace.` |
| `KHEM` | เข้ม (Khem) | 27, Temporary night-watch electrician (`ช่างไฟรับจ้างเฝ้าเครื่องปั่นไฟและศาลาสวดศพกะดึก`) | `Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture)` | `Puck` | `Young Thai man age 27, cautious and tense, breathless low voice hiding fear, natural conversational Thai.` |
| `LUNG_IN` | ลุงอิน (Lung In) | 64, Veteran forest-temple undertaker (`สัปเหร่อเก่าประจำวัดป่าห้วยหมอก`) | `Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture)` | `Charon` | `Old Thai rural temple undertaker in his mid-60s, deep raspy weathered voice, speaks low and slow like a solemn warning.` |
| `PA_BUA` | ป้าบัว / หญิงชุดดำและเสียงเรียกในโลงเย็น (Pa Bua / The Mourner in Black) | 52, Mysterious midnight mourner / spirit bound to the cooling coffin | `Pa Bua, a pale 52-year-old Thai woman with hollow dark-ringed eyes, wet hair pulled back in a tight low bun, wearing an old rain-damp black lace mourning blouse and dark skirt, holding a wilted white lotus stem (she appears at most once in the picture)` | `Kore` | `Middle-aged Thai woman in her 50s, eerie flat hollow whisper, unnaturally calm and slow, chillingly polite Thai.` |

---

## Visual & Vocal Continuity Rules

1. **Zero Character Reuse from EP01–EP06 (`CMO_Standard_GhostChannel_DNA` §3.1):**
   - `Khem` (navy canvas work jacket, charcoal tee, black tool sling bag), `Lung In` (dark-brown traditional cotton shirt, braided black cord with brass talisman cylinder), and `Pa Bua` (black lace mourning blouse, wilted white lotus) are newly designed exclusively for EP07 and do not reuse Natee (EP01), Keng (EP02), Karn (EP03), Thos/Ta Kham (EP04), Non/Lung Chot (EP05), or Phop/Nadet (EP06).
2. **Prompt Embedding Lock:**
   - Every ChatGPT prompt in `plates.md` that depicts `Khem`, `Lung In`, or `Pa Bua` embeds the exact English look string from the table above (including `(he/she appears at most once in the picture)` and `Pale neutral skin tone, no blush, no red face, no red ears`).
3. **Voice Call Separation (`voice/job.json`):**
   - Every spoken block in `script/c01.txt..c20.txt` marks its lines with `[NARRATOR: Algenib]`, `[LUNG_IN: Charon]`, `[KHEM: Puck]`, or `[PA_BUA: Kore]`.
   - In `voice/job.json`, each marked line is its own individual TTS call (`c01_01` through `c20_02`, 54 calls total, `<= 60` `MAX_CALLS` limit in `tools/fal_tts.py`) pointing to its own clean Thai text file in `/opt/MoonieXHQ/Work/ghost-pilot/ep07/voice/in/<call_name>.txt`.
