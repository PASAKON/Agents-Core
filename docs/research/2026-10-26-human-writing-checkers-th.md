# Human-writing checkers for Thai text (research for the CMO, CEO order 26 Oct 2026)

## สรุปสำหรับ CEO

1. มีเครื่องมือฟรีบน GitHub หลายตัว แต่เกือบทั้งหมดทำมาเพื่อภาษาอังกฤษ ที่รองรับไทยจริงมีแค่ PyThaiNLP กับ TLTK และสองตัวนี้ช่วยตัดคำ วัดระดับความยากของบทอ่าน ไม่ได้บอกว่าเหมือนคนเขียนหรือไม่
2. เครื่องตรวจว่า AI เขียน (detector) เชื่อถือไม่ได้กับภาษาไทย โดยเฉพาะข้อความสั้นอย่างแคปชั่นหรือคอมเมนต์ มันพลาดบ่อย และเคยตัดสินข้อความของคนจริงว่าเป็น AI ใช้เป็นเกณฑ์ผ่านไม่ผ่านไม่ได้
3. สิ่งที่ช่วยให้คนอ่านเข้าใจจริงคือ ประโยคสั้น หนึ่งประโยคหนึ่งเรื่อง ใส่ประเด็นไว้ต้นประโยค ใช้คำที่คนพูดกัน ตรงกับที่คุณบอก
4. ราชบัณฑิตยสภาใช้เครื่องหมายคำพูดแบบโค้ง และไม่มีเครื่องหมายหัวลูกศรคู่แบบฝรั่งเศสในหลักเกณฑ์ ตรงกับที่คุณสั่ง แต่กฎของเราห้ามเครื่องหมายโค้งด้วย เพราะแป้นมือถือไม่มี เหตุผลนี้ใช้ได้กับโพสต์ ไม่ใช่กฎของภาษาไทย
5. กฎข้อ 3 ของเราบอกว่า พิมพ์ผิดนิดหน่อยไม่เป็นไร สมบูรณ์แบบเกินไปคือสัญญาณเตือน ข้อนี้ใกล้กับการปลอมเป็นคนมากกว่าการเขียนให้เข้าใจ ผมแนะนำให้แก้เป็น ไม่ต้องจงใจพิมพ์ผิด
6. ข้อเสนอ คือสคริปต์ตรวจในเครื่อง ฟรี ใช้เวลาสร้างประมาณ 5 ถึง 8 ชั่วโมง ตรวจคำและรูปประโยคที่ AI ชอบใช้ในภาษาไทย แล้วให้ AI อีกตัวที่ไม่เคยเห็นงานนี้อ่านแล้วสรุปเป็นหนึ่งบรรทัด ถ้าสรุปไม่ตรงกับที่เราอยากสื่อ คนอ่านก็อาจไม่เข้าใจเหมือนกัน
7. ข้อจำกัดสำคัญ ผมเปิดหน้าเว็บต้นฉบับเองไม่ได้ในรอบนี้ ข้อมูลภายนอกทั้งหมดมาจากผลค้นหาที่สรุปให้ ยังไม่ได้ยืนยันกับต้นฉบับ (ดูหัวข้อ Evidence status)

---

## Evidence status (read this first)

- **How this note was made.** The task contract for this worker allows file tools and web search only. The web search tool returns a written summary with redirect links. It does not let me open a repo page, a README, a paper or a commit list myself.
- **Marks used below.**
  - **V (verified):** I read the file myself. Only our own repo files qualify: `docs/promo/WRITING-RULES.md`, `scripts/check-post-text.sh`, `.claude/skills/humanizer/SKILL.md` (first 40 lines), `.claude/skills/de-ai-ify/SKILL.md`.
  - **R (reported):** a search summary says so. Nothing outside our repo reached V in this run. Every R claim needs one open-the-page check before anyone relies on it.
- **URLs.** The canonical URLs in the Sources section come from the search summaries and from my memory of the projects. I did not open them. Two papers on Thai readability came back with titles only, with no stable URL.
- **Last-commit dates.** I could not get a commit date for any repo. The column says "not checked" unless a summary gave a version or a date. A release date is not a last-commit date.
- **Missing skill file.** `.claude/skills/CMO_Standard_HumanVoice_TH/SKILL.md` does not exist in this worktree (file read returned "does not exist"). The gap analysis (question 4) therefore compares against `WRITING-RULES.md` and `check-post-text.sh`, plus the brief's description of that skill (10 Thai tells, banned characters, a 4-step pass). I could not see the 10 tells. Some gaps below may already be covered there.
- **Gate state in this worktree.** `scripts/check-post-text.sh` here does NOT yet contain guillemets (U+00AB and U+00BB). The brief says they are added from 26 Oct, so that change lives on another branch. (V)

---

## 1. Tool table

Ranked: tools with a Thai path first, then tools with none. "Effort" is my estimate of hours to get a useful Thai check from it, from zero, including a Thai test set. Estimates are my own judgement, not sourced. "Offline" means after install, no network call at run time.

| # | Tool | What it measures | Thai support, with evidence | Licence | Offline | Last commit | Effort on Thai |
|---|---|---|---|---|---|---|---|
| 1 | **TLTK** (Chulalongkorn), github.com/attapol/tltk | Text difficulty class L1 to L4 (lower elementary to high school) and genre, from 129 linguistic features (`TextClass`, `txt2feat`) | **Yes.** README lists Thai syllable and word segmentation, POS, and `TextClass` (R, S7) | BSD-3 since 1.2.2, earlier LGPL (R, S7) | Yes, needs a Python install | Not checked. Summary names v1.9.1 and commit 0cef4bc, no date | 3 to 6 h to try. Weak fit: level is for school text, so one social post gives a coarse number. Useful only to flag text far harder than our approved posts |
| 2 | **PyThaiNLP**, github.com/PyThaiNLP/pythainlp | Not a style checker. Gives `sent_tokenize`, `word_tokenize`, `subword_tokenize` (syllables), spelling correction, Thai char counts | **Yes for NLP. No readability or style function** found: summary says it has no Flesch-type index and lists the tokenisers as the building blocks (R, S6) | Apache-2.0, data CC0 and CC-BY (R, S6) | Mostly yes. Some engines fetch models on first use (my memory, not checked) | Not checked. 5.x line described as active (R) | 8 to 16 h to build our own length and word-choice stats on top. This is the engine any Thai readability script would need |
| 3 | **Vale**, github.com/vale-cli/vale | Rule engine for style: `existence`, `substitution`, `repetition` rules in YAML, plus sentence-scope rules | **Partial.** Regex rules (existence, substitution) work on any script. Sentence-scope rules assume English segmentation and do not suit Thai (R, S1, S2) | MIT (R, S1) | Yes, single Go binary | Not checked. Repo now under `vale-cli` (R) | 6 to 10 h including install. It could carry our Thai rules as YAML, but a plain script does the same job with no new tool. Gain is editor and CI integration only |
| 4 | **Thai readability formulas from papers** | Surface features: sentence length, syllables per word, word frequency, fed to SVM or similar | **Yes by design**, but no ready-to-run code found. Two papers named: "Assessing readability of Thai text" and "Content-Based Readability Assessment: A Study Using A Syllabic Alphabetic Language (Thai)" (R, S13) | Paper, not code | n/a | n/a | 20 h or more, plus a labelled set to validate. Wrong target: they grade school texts, not clarity of a caption |
| 5 | **antislop-sampler / auto-antislop**, github.com/sam-paech | Bans over-used words and phrases while a model generates (generation side, not a checker) | **No out of the box.** English slop lists. Method (compare word and n-gram frequency of model text with human text) could be redone for Thai with a Thai human corpus (R, S12) | MIT (R, S12) | Needs a local model | Not checked | 20 to 40 h. Needs a Thai human corpus, Thai model output and a model on this box |
| 6 | **slop-forensics**, github.com/sam-paech/slop-forensics | Finds over-represented words and n-grams of a model against a human baseline, builds a slop list | **No out of the box.** Same reason as row 5 (R, S12) | Not stated in the summary, not checked | Yes | Not checked | Same as row 5. The idea is the useful part: our own Thai slop list from CMO drafts versus CEO-written posts |
| 7 | **EQ-Bench slop score**, eqbench.com | Counts slop words, slop trigrams and "not X but Y" patterns per 1,000 words or characters | **No.** Described as English only (R, S12) | Not checked | n/a (a benchmark, not a tool to run on drafts) | Not checked | Not usable. Useful only as a list of structural tells (the contrast pattern) |
| 8 | **GLTR**, github.com/HendrikStrobelt/detecting-fake-text | Colours each word by its rank under a language model (GPT-2) | **No.** Built around English GPT-2 vocabulary (R, S8). Tokeniser mismatch for Thai is my inference | Apache-2.0 (R, S8) | Yes, with model weights | Stale: summary says 2019 to 2021 (R) | Not worth it. Would need a Thai LM swapped in |
| 9 | **Binoculars**, github.com/ahans30/Binoculars | Zero-shot detector: ratio of perplexity to cross-perplexity between two Falcon models | **No.** Summary says English-optimised, thresholds calibrated on English, needs long input, ~512 tokens suggested (R, S9) | BSD-3 (R, S9) | Yes, but two 7B-class models | Not checked | Not usable: heavy models, English thresholds, short text |
| 10 | **Fast-DetectGPT**, github.com/baoguangsheng/fast-detect-gpt | Zero-shot detector: conditional probability curvature | **No evidence for Thai.** Evaluated mainly on English. A multilingual scoring model would be needed (inference, S10) | MIT (R, S10) | Yes, needs a model | Not checked | Not usable for short text. Would need calibration on Thai we do not have |
| 11 | **Ghostbuster**, github.com/vivek3141/ghostbuster | Detector from token probabilities of weaker models, then a classifier | **No.** English only, and it sends text to the OpenAI API (R, S11). That breaks our no-paid-API rule | Summary says licence tag NOASSERTION (R) | **No** | Not checked | Excluded |
| 12 | **proselint**, github.com/amperser/proselint | Style checks (clichés, weasel words, jargon) from a curated English check list | **No.** English prose linter (R, S3) | BSD-3 (R, S3) | Yes | Release 0.16.0 on 14 Nov 2025 (R). Commit date not checked | Rewrite all checks in Thai, so it is just our own list |
| 13 | **write-good**, github.com/btford/write-good | Passive voice, weasel words, wordiness, English only | **No.** English (R, S4) | MIT (R, S4) | Yes (Node) | Not checked | Same as proselint |
| 14 | **textstat**, github.com/textstat/textstat | Flesch, Gunning Fog and similar scores | **No.** Language list is en, de, es, fr, it, nl, pl, ru (R, S5). Formulas count spaces and English syllables, so Thai gives meaningless numbers (inference) | MIT (R, S5) | Yes | Not checked. Stable 0.7.13 per PyPI summary (R) | Not usable. The de-ai-ify skill in our repo already leans on Flesch (V): do not apply it to Thai |

Not in the table by choice: commercial detectors (Copyleaks, Originality.ai, GPTZero). They need sign-up and money, which the brief rules out. See question 2 for what they claim.

**Searches that found nothing.** I found no open-source Thai-specific "sounds like AI" checker and no public Thai AI-text detector with a README and a test set. This is "not found by one search round", not proof that none exists.

**Answer to the Vale question.** Yes, Vale custom styles could carry our Thai rules, but only the pattern kind: banned characters, banned phrases, regexes for patterns like "ไม่ใช่แค่ ... แต่". Anything that needs a sentence (length, count per sentence) will not work because Vale's sentence logic is English-centric (R, S1, S2). Our rules are almost all pattern kind, so Vale would work, but it adds a Go install and a YAML layout for no new capability over a script.

---

## 2. Do AI-text detectors work on Thai, and on short text?

**Short answer: no evidence they work. Several sources say they fail on exactly our case. Never use a score as a gate. For Thai captions it is not even a good hint.**

| Point | Evidence | Status |
|---|---|---|
| No Thai in a major multilingual detection benchmark | MULTITuDE has 11 languages: ar, ca, cs, de, en, es, nl, pt, ru, uk, zh. No Thai (S17). I believe M4 and RAID do not include Thai either, from memory, not checked | R |
| Open detectors are tuned for English | Binoculars, Ghostbuster: English-optimised, authors warn about other languages (S9, S11) | R |
| Short text is unreliable | OpenAI withdrew its own classifier in July 2023 for low accuracy and said it was unreliable under 1,000 characters (S16). A Thai caption is far under that. Binoculars is suggested at ~512 tokens (S9) | R |
| False positives on plain human writing | Liang et al: detectors flagged 61.22% of TOEFL essays by non-native writers as AI while near-perfect on US 8th-grade essays. Cause: perplexity detectors read simple, predictable wording as machine text (S14) | R |
| Detector tools in general are neither accurate nor reliable | Weber-Wulff et al tested 12 public detectors and 2 commercial ones, found them inaccurate and easy to defeat by light edits (S15) | R |
| Thai-specific reasons | Summaries argue that no word spaces, token inflation and scarce Thai training data hurt zero-shot detectors. These come from a general search summary without a named paper, so treat as plausible, not shown | R, weak |
| Vendor claims for Thai | Copyleaks lists Thai among 30+ languages and a Scribd document quotes ~97.9% accuracy for Thai. Originality.ai says Thai added in its Multi Language 2.0.0 model. GPTZero does not list Thai (S22). These are the sellers' own numbers, from a document I could not check, on unknown text length | R, weak, self-reported |

**Plain reading for us.** A Thai social post is short, simple and written in plain words, which is the very text perplexity-based detectors misjudge. Our own goal is a reader who understands, and a detector does not measure that. A low score tells us nothing about clarity. A high score on a real person's text can only cause a wrong accusation.

**My inference, not sourced:** the Liang et al result suggests that our "write plainly and shortly" rule would push text toward what detectors call AI. Clear writing and "does not look like AI to a detector" can pull in opposite directions. This is one more reason not to chase scores.

---

## 3. What makes text easy for a person to understand

### 3.1 Plain-language guidance (English sources)

- **Sentence length.** Federal plain-language guidance, as restated by opm.gov and state.gov pages, says to average 15 to 20 words, one main idea per sentence, mix short and long (R, S19). The search did not return the plainlanguage.gov page itself, so the number is second-hand.
- **Active voice** and naming who does what (R, S19).
- **Wikipedia "Signs of AI writing"** is a field guide for editors (R, S18). Its main groups:
  - inflated significance ("pivotal", "testament", "lasting impact");
  - vague attribution ("studies show", "experts argue");
  - formulaic wrap-ups ("In conclusion", "Overall");
  - rule of three;
  - negative parallelism ("not just X, it is Y");
  - false ranges;
  - AI vocabulary (delve, tapestry, landscape);
  - em dash used where a human would use a comma or brackets;
  - heavy bold, title-case headings, over-use of lists;
  - chatbot leftovers ("I hope this helps").
- **Its own caveat:** the list is descriptive, not a test. Humans write some of these too. Do not delete text only because it has one tell (R, S18). This supports using tells as a prompt to rewrite, not as a gate on one hit.

**These are English sources.** No Thai number for sentence length exists in anything I found. English words per sentence do not transfer, because Thai has no word spaces. Do not copy "15 to 20 words". Use the CEO-approved posts as the baseline instead (see question 5).

### 3.2 Thai: Royal Society (ราชบัณฑิตยสภา) punctuation rules

The source is the Royal Society book on punctuation and other marks, spacing and abbreviations, found on orst.go.th. I could not open it. These points are from search summaries (R, S20) and must be read once in the original before the CMO relies on them.

| Topic | What the summaries say |
|---|---|
| Quote marks | Thai uses double curly quotes (U+201C, U+201D) for speech, quoted text, emphasis and slang or special meaning. Single curly quotes (U+2018, U+2019) nest inside them. For a quote of several paragraphs, open the quote at every paragraph and close it only at the last |
| Guillemets (U+00AB, U+00BB) | Not listed as Thai quote marks. Consistent with the CEO's 26 Oct remark that Thai does not use them. Search did not find a line that says they are forbidden, only that they are not the standard |
| Full stop | Thai does not normally end a statement with a full stop. A space marks the end of a sentence or idea. The full stop is for abbreviations and decimals. One summary says a "large space" (about double) separates sentences in print |
| Spacing between phrases | A space groups phrases or clauses so a long sentence does not run together. Space goes before an opening quote mark |
| ไม้ยมก (ๆ) | One space before and one after |
| Comma | Space after, none before. Thai lists often have no commas at all ("สีแดง สีน้ำเงิน และสีเหลือง") |

**Conflict with our gate (important).** The gate bans curly quotes (U+201C, U+201D, U+2018, U+2019) and the stated reason in `WRITING-RULES.md` is that the phone keyboard has no key for them (V). That is true for typed posts. But the Royal Society standard for printed Thai is exactly those curly quotes. So the rule is right for posts and wrong as a statement about Thai. Anything formal (press release, document, website copy) that goes through the gate would be pushed away from the official form. The brief limits the gate to posts, so this is only a wording risk, but the CMO should not say "Thai does not use curly quotes".

**Possible Thai checks from these rules** (my suggestion, each needs a native reader to confirm):
- a full stop at the end of every line or sentence in a post;
- commas between list items;
- ๆ stuck to the word with no space.

### 3.3 Word choice and reading on a phone

- **Word choice (Thai AI tells).** A Thai-language search summary lists: English sentence order carried into Thai, over-use of "ของ" and "การ/ความ" noun phrases, stacked connectors (นอกจากนี้, ยิ่งไปกว่านั้น, ดังนั้น), over-formal words where people say something shorter (ดำเนินการ for ทำ, ท่าน for คุณ), stock openings ("ในยุคปัจจุบัน", "ปฏิเสธไม่ได้ว่า") and stock closers ("เป็นกุญแจสำคัญสู่อนาคต"), equal-length numbered sections. The sources behind it are commercial "humaniser" blogs (R, weak). They fit our own experience but are not research. Use them as candidate phrases for the list, to be confirmed against real drafts.
- **Phone.** Nielsen Norman Group, as summarised: on a phone, simple short content is understood as well as on desktop, dense content is not. Advice is short paragraphs (1 to 3 sentences), front-load the point, and make scan anchors (R, S21). This supports rule 3 in `WRITING-RULES.md` (short, line breaks) (V for our rule, R for the research).
- **No source found** for Thai-specific line length or the best phrase length on a phone.

---

## 4. Gaps: what these sources say that our skills and gate do not cover

Compared against `WRITING-RULES.md` and `check-post-text.sh` (V) and the humanizer and de-ai-ify skills (V). Not compared against the HumanVoice_TH skill, which was missing from this worktree.

| # | Gap | Source | Where we stand |
|---|---|---|---|
| 1 | **Guillemets (U+00AB, U+00BB) are not blocked** in the script in this worktree | CEO order 26 Oct; Royal Society (R, S20) | Script lacks them (V). Brief says they land from 26 Oct |
| 2 | **Our rule 3 asks for small typos** ("สมบูรณ์แบบเกินไปคือสัญญาณเตือน"). This is imitation, not clarity. The CEO's 26 Oct wording says the goal is understanding, "not pretending to be human". Typos make text harder to read | `WRITING-RULES.md` rule 3 (V); CEO order | Contradicts the order. Suggest rewording to "do not add typos on purpose" |
| 3 | **The gate's stated purpose is "readers cannot tell it is not a person"** (rule 1 "Why hard"). The CEO now says the aim is that readers understand. The character gate still stands, since those characters are not typed on phones, but the reasoning should change | `WRITING-RULES.md` (V); CEO order | Wording only |
| 4 | **No check for a full stop at sentence end, commas in lists, or phrase spacing** | Royal Society (R, S20) | Not in script, rules or humanizer |
| 5 | **No Thai phrase list.** The script checks 11 characters only. No stock openers, closers, stacked connectors, or over-formal words | Thai summary (R, weak, S23); Wikipedia (R, S18) | humanizer and de-ai-ify are English only (V), the Thai list is not in the script |
| 6 | **Negative parallelism ("ไม่ใช่แค่ X แต่ Y")**, rule of three, false ranges, vague attribution, inflated significance | Wikipedia Signs (R, S18); EQ-Bench slop patterns (R, S12) | In humanizer §1 to §6 (V for the skill) in English. Not in a Thai rule or in the script |
| 7 | **Leftover chatbot lines** ("หวังว่าจะเป็นประโยชน์", "ถ้าต้องการให้ช่วยเพิ่ม บอกได้เลย") | Wikipedia Signs (R, S18) | humanizer covers it in English (V). Nothing Thai in the script |
| 8 | **Sentence and phrase length is advice, not measured.** Rule 3 says short sentences, but no check and no number | plainlanguage via opm.gov and state.gov (R, S19) | Needs a Thai measure (space-separated phrase length), calibrated on approved posts |
| 9 | **Front-load the point** (important thing first) | Plain language, NN/g (R, S19, S21) | Not in rule 3 |
| 10 | **No comprehension test.** None of our tools asks "does a reader get the message and the next step?" | CEO's actual goal; no tested method found | Gap in all three skills and the gate |
| 11 | **de-ai-ify's score is unsourced and English-based.** The file claims "92% agreement with human editors (n=200)", a 0 to 10 human-ness score built partly on Flesch Reading Ease, and a case study with traffic numbers. None cites a source (V: I read the file) | `de-ai-ify/SKILL.md` | Do not use its score or its Flesch targets on Thai |
| 12 | **Tells are hints, not proof.** Wikipedia says humans use these too. Our script rejects on one em dash, which is fine for a keyboard-typed channel, but we should not reject on soft tells like "นอกจากนี้" after one hit | Wikipedia Signs caveat (R, S18) | Use hard gate for characters only. Make phrase checks warnings |

---

## 5. Recommendation: one setup

**Name:** a local Thai pre-publish check with two parts. Part A is a script, part B is a fresh-reader test. No install, no paid API, no sign-up.

### Part A: Thai pattern lint (script)

- **What it is.** Extend the existing bash gate, or add a sibling script written in plain Python (standard library only, already on most boxes), reading a draft file or stdin.
- **Hard checks (fail, exit 1):** the existing character list, plus guillemets (U+00AB, U+00BB).
- **Soft checks (warn, exit 0, show line and phrase):**
  1. A Thai phrase list. Start with the candidates in 3.3: นอกจากนี้, ยิ่งไปกว่านั้น, ปฏิเสธไม่ได้ว่า, ในยุคปัจจุบัน, เป็นกุญแจสำคัญ, หวังว่าจะเป็นประโยชน์, ท่าน, ดำเนินการ, ส่งเสริม.
  2. The contrast pattern "ไม่ใช่แค่ ... แต่" (regex) and a count of "ของ" per 100 characters.
  3. Phrase length: the longest run of Thai between spaces or line breaks. No number from the literature, so set the limit from the CEO-approved posts: take the median and the 95th percentile of the run length over about 20 to 30 approved posts, then warn above the 95th percentile.
  4. A full stop at the end of a line, commas between list items, ๆ without spaces (Royal Society checks, need native-reader confirmation).
  5. Three-item lists and equal-length bullet runs.
  6. Chatbot leftover lines.
- **Phrase list upkeep.** The list is the real cost. Keep it in one text file, add a phrase every time the CEO strikes one in a draft, remove a phrase that fires on good text.

### Part B: fresh-reader comprehension test (model reread)

- **How.** Give a new model session only the finished text, without the brief, and ask three things:
  1. "Restate this message in one line."
  2. "What is the reader supposed to do next?"
  3. "Quote any sentence you had to read twice or any word a Thai reader would not say aloud."
- **Pass rule.** The one-line restatement matches the intended message and the next step is stated. If not, the text is unclear to a stranger, rewrite it.
- **Cost.** No extra tool: the agents already run on models we have. Not a paid API call from the script. It is run by the CMO or a second agent, so it adds a prompt, not infrastructure.
- **Caveat.** There is no tested method behind this. The search for LLM comprehension tests returned one line and no usable source (R, weak). Treat it as a pilot idea. Run it on 10 past posts, compare with what the CEO says is clear, and keep it only if it agrees.
- **Bias risk (my inference).** A model fills gaps a person would not, so it may "understand" a post a human could not. It also prefers its own style. So use a different session, never the one that drafted, and keep the CEO or one native reader as the final check.

### Build effort

| Piece | Hours |
|---|---|
| Collect 20 to 30 approved posts, measure phrase length baseline | 1 |
| Script: hard and soft checks, exit codes, usage in the HumanVoice skill | 2 to 3 |
| Phrase list v1 plus test on 10 old drafts to remove false alarms | 1 to 2 |
| Reread prompt, pilot on 10 posts, write the one-page checklist | 1 to 2 |
| **Total** | **about 5 to 8 h** |

### What it would catch

- Banned characters and guillemets, every time (hard).
- Known stock Thai phrases, stacked connectors, English-style contrast frames, over-use of "ของ".
- Over-long phrases compared with posts the CEO has approved.
- Ambiguous or empty messages, if part B works as piloted.

### What it would miss

- New tells. Models change, and word habits change with every release (the humanizer skill says so itself, V). The list will lag.
- Tone: a text with no flagged phrase can still sound cold or wrong for the CEO.
- Facts: neither part checks that the claim is true.
- Fluent but empty text, unless part B notices it.
- Anything that is understood by the model but not by a person.
- Whether the Thai is natural. Only a Thai reader can say that.

### Why not the alternatives

| Option | Verdict |
|---|---|
| Vale | Works for pattern rules (R) but adds a Go install and a YAML layout for no new power. Revisit if we need editor or CI integration |
| PyThaiNLP / TLTK | Real Thai tools, but they give counts and a difficulty label, not "sounds natural". Not allowed to install here. Revisit only if we want a measured readability number |
| Any AI detector | Rejected, see question 2 |
| Thai readability formula | Wrong target (school text), high effort |

### Order of work for the CMO

1. Read the Royal Society book once in the original (orst.go.th) to confirm section 3.2.
2. Open the three or four R claims that matter most (Vale Thai behaviour, TLTK licence and date, OpenAI 1,000-character statement, Liang et al figure) and mark them V.
3. Fix the wording in gaps 2 and 3.
4. Build part A. Pilot part B.

---

## Sources

All external links are R: from search summaries or from memory, not opened in this run. "No stable URL" means the search returned only a redirect.

- S1 Vale: https://github.com/vale-cli/vale
- S2 Vale docs (styles, rule types): https://vale.sh/docs
- S3 proselint: https://github.com/amperser/proselint
- S4 write-good: https://github.com/btford/write-good
- S5 textstat: https://github.com/textstat/textstat
- S6 PyThaiNLP: https://github.com/PyThaiNLP/pythainlp and https://pythainlp.org
- S7 TLTK: https://github.com/attapol/tltk
- S8 GLTR: https://github.com/HendrikStrobelt/detecting-fake-text and arXiv 1906.04043
- S9 Binoculars: https://github.com/ahans30/Binoculars and arXiv 2401.12070
- S10 Fast-DetectGPT: https://github.com/baoguangsheng/fast-detect-gpt and arXiv 2310.05130
- S11 Ghostbuster: https://github.com/vivek3141/ghostbuster and arXiv 2305.15047
- S12 Sam Paech tools and slop score: https://github.com/sam-paech/antislop-sampler, https://github.com/sam-paech/slop-forensics, https://eqbench.com
- S13 Thai readability papers: "Assessing readability of Thai text" (ResearchGate) and "Content-Based Readability Assessment: A Study Using A Syllabic Alphabetic Language (Thai)" (University of Liverpool). No stable URL
- S14 Liang et al, GPT detectors are biased against non-native English writers: arXiv 2304.02819
- S15 Weber-Wulff et al, Testing of detection tools for AI-generated text: arXiv 2306.15666
- S16 OpenAI, AI text classifier notice: https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/
- S17 MULTITuDE: arXiv 2310.13606
- S18 Wikipedia, Signs of AI writing: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- S19 Plain language: https://www.plainlanguage.gov/guidelines/ (sentence-length figure via opm.gov and state.gov restatements, no stable URL)
- S20 ราชบัณฑิตยสภา, หลักเกณฑ์การใช้เครื่องหมายวรรคตอนและเครื่องหมายอื่น ๆ หลักเกณฑ์การเว้นวรรค หลักเกณฑ์การเขียนคำย่อ: site https://www.orst.go.th, no stable URL to the book
- S21 Nielsen Norman Group, mobile content: https://www.nngroup.com
- S22 Vendor language pages: copyleaks.com, originality.ai, gptzero.me (no stable URLs)
- S23 Thai AI-tell summary built on humantone.io and similar blogs (weak, no stable URL)
- V (local, read in this run): `docs/promo/WRITING-RULES.md`, `scripts/check-post-text.sh`, `.claude/skills/humanizer/SKILL.md` (lines 1 to 40 of 397), `.claude/skills/de-ai-ify/SKILL.md`
