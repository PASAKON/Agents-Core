# «เงินที่พ่อตั้งใจหา» EP1 — Structure Audit (tig-scene-engine, AUDIT mode)

Source: `docs/scripts/ngoen-tee-por-EP1.md` (60 shots, 8:00 exact). Script text
untouched — this is a read-only audit per IRON-RULES §51 and `.claude/skills/tig-scene-engine/SKILL.md`.

**Reading note before anything else:** every "Goal / Obstacle / Tactic / Reversal /
Value Shift" term below uses the skill's bespoke definitions, not textbook
screenwriting definitions. In particular: Goal = the fixed thing the hero is
fighting to fix, tested by removal (cut the scene — does the causal chain to
the story goal still hold?); Reversal = a turn against the AUDIENCE's
expectation of the *character*, not just a plot twist; Value Shift = the
audience's before→after verdict on that character, and a reversal with no
nameable value shift is **inert**, full stop, regardless of how sad the line
is.

---

## 0. Story goal (needed before Goal can be audited at all)

The overt personal goals (get a job, run the shop) are not the story's spine.
The spine is: **สมชายต้องทำให้เงินที่ส่งลูกยังคงมีความหมายอย่างที่เขาตั้งใจ ไม่ว่าจะต้องแลกด้วยอะไร
หรือลูกจะรู้ความจริงในที่สุดหรือไม่.** Concealment is the *tactic* in play for most
of the episode, not the goal — the goal survives the Big Turn unchanged,
which is exactly what the engine's Goal rule requires ("the hero is never
wrong about the goal, only about tactics"). Once ต้น learns the truth, his own
goal snaps into being the episode's second engine: relieve his father of the
debt by refusing the money. Both goals resolve into the same object (the
envelope) at the payoff.

## 1. Sequence segmentation (scale stated per sequence)

Two nested scales, per the skill's nesting rule:

- **Macro** — the whole episode is one sequence: jeopardy = "will today's
  secret survive, and what happens once it doesn't." Opens at the cold open,
  resolves (for this episode) at the payoff, with one sub-thread (grandma)
  deliberately left unresolved and pushed to a season-length sequence.
- **Meso** — 10 sequences below, each its own jeopardy-open→resolve unit,
  roughly aligned to the script's own scene map but re-derived from jeopardy,
  not from the map's labels.

| Seq | Shots | Jeopardy opens | Jeopardy resolves | Scale |
|---|---|---|---|---|
| S0 Stinger | 1–2 | Father attacked | He composes himself, gets up | Pre-Goal (see §2) |
| S1 Ordinary rhythm | 3–15 | (mostly none — see §2) / ต้น's job search (12–15) | Job thread NOT resolved here — deferred to shot 58 | Local, mostly inert |
| S2 Upstairs witness | 16–22 | Grandma wants to warn, physically can't | NOT resolved in EP1 — deferred to S9 (59–60) | Global, season-length, opens here |
| S3 Counting the day | 23–30 | Risk of ต้น discovering the split | ต้น watches unseen — narrows, doesn't resolve | Local (feeds S6) |
| S4 Lender arrives, public | 31–36 | Public exposure risk | Father redirects him out back | Local (feeds S5) |
| S5 Back alley + Big Turn | 37–45 | Physical threat + secrecy, GLOBAL | Father pacifies lender (his tactic "succeeds" locally); secrecy fails GLOBALLY — ต้น now knows | Global |
| S6 Give it back | 46–53 | ต้น's new goal (relieve father) vs. father's refusal | Refusal escalates to naming the truth aloud | Global (the theme's crux) |
| S7 Payoff | 54–56 | — (see finding in §4) | Envelope pressed into ต้น's hands, father returns to work | Global |
| S8 Aftermath | 57–58 | — | Ordinary line closes the day, job-thread callback | Local, dénouement |
| S9 Cliffhanger | 59–60 | Grandma's season-length sequence resolves its FIRST beat | New jeopardy opens (what is she reaching for) — deferred to EP2 | Global, cross-episode |

---

## 2. Chain check, sequence by sequence

### S0 — Stinger (shots 1–2)
```
SEQUENCE: Cold open — the wall (1–2)

CHAIN CHECK
• Goal — Not yet establishable. No hero/goal has been introduced to the audience;
  this is a pre-Goal cold open. Retroactively it plants the GLOBAL obstacle for
  the whole episode/season.
• Obstacle — Physical violence over money. Scale: unknown to the audience yet,
  revealed as GLOBAL in hindsight.
• Tactic — N/A, character unidentified in-scene.
• Reversal — N/A, no established verdict on anyone yet to reverse.
• Value Shift — N/A.

REMOVAL TEST: Cut 1–2 — does the chain to the story goal still hold?
YES. Everything this stinger tells the audience (violence, money, a debt) is
told again, fuller and in context, at S5 (37–42). As a plot-causal scene it is
technically redundant.
VERDICT: FAILS the removal test on strict causal grounds. But this is a
retention-hook decision, not a structure decision — see CEO Q2 in §7. Flag for
the CEO's call, not an automatic cut.
```

### S1 — Ordinary rhythm (shots 3–15)
```
SEQUENCE: Morning opens the shop, rush, phone in pocket (3–15)

CHAIN CHECK
• Goal — Shots 3–11: no goal is in play, no obstacle, no jeopardy. This is pure
  atmosphere/world-building ("ordinary life established as contrast" per the
  script's own scene map — a legitimate purpose, but not a Goal-chain purpose).
  Shots 12–15: ต้น's own goal (get a job) surfaces as a real, if minor, thread.
• Obstacle — Shots 3–11: NONE. Flag as SLACK per the Obstacle audit rule
  ("if nothing is genuinely at risk, the obstacle is fake and the scene goes
  slack"). Shots 12–15: the 12th rejection email threatens ต้น's sense of
  self-worth — LOCAL, and it is real (a running personal stake).
• Tactic — Shot 14: father sees the rejection, says nothing. Reasonable given
  his established character (silence as protection), and it plants the
  silence-as-love pattern the finale depends on. Passes, but its information
  payoff is 6+ minutes away.
• Reversal — None claimed; this sequence does not resolve within the episode
  (see below), so none owed yet.
• Value Shift — None yet. Establishes baseline verdict on both characters
  ("hardworking, warm, tired shopkeeper" / "quietly frustrated new-grad") that
  later sequences will revise.

REMOVAL TEST, shot by shot:
- Shots 3, 4, 8, 11 — THIN PASS. Minimal causal freight (3 = day-open
  transition; 4 = shop's public warmth; 8 = the ONLY diegetic naming of "ต้น"
  in the whole episode; 11 = father's public warmth, later contrasted against
  his private cost). Keep, but they are doing very little work per second.
- Shots 5, 6, 7, 9, 10 — FAIL. Zero jeopardy, zero causal link, nothing
  downstream references their specific content. Cutting them does not break
  the chain to the story goal.
- Shots 12–15 — PASS (the job-thread payoff at shot 58 depends on it having
  been planted).

VERDICT: Sequence-level FAIL on shots 3–11 as a block (9 shots, 72 seconds,
15% of the runtime) — this is the single largest concrete removal-test
finding in the episode. See §6 (Weakest Point).
```

### S2 — Upstairs witness (shots 16–22)
```
SEQUENCE: Upstairs, the witness (16–22) — opening beat of a season-length sequence

CHAIN CHECK
• Goal — Grandma's private goal: warn someone before she dies. Causally linked
  forward — without this, S9's cliffhanger has no established relationship or
  stakes to pay off.
• Obstacle — Physical incapacity (can't speak clearly, can't move). GLOBAL to
  her own thread — it threatens whether she can ever act at all, not just this
  scene.
• Tactic — Shot 19, she manages one trembling syllable: "...ต้น...". Forced by
  her state, a reasonable (only) probe available to her.
  LOCAL outcome: returns ZERO information — ต้น doesn't register it as
  anything but affection (shot 20, he smiles and wipes her mouth). By the
  strict Tactic rule this is a wheel-spin IN THIS SCENE.
  GLOBAL outcome: it returns information to the AUDIENCE (she is trying,
  she is aware) that the season-length sequence needs. Net: acceptable as a
  deferred-payoff tactic, not a flaw — but name it precisely as such rather
  than calling it a clean pass.
• Reversal — Not owed here; sequence does not resolve until S9.
• Value Shift — Not owed here.

REMOVAL TEST: Cut 16–22 — does the chain still hold? NO — S9's reveal needs
this established relationship and the floor-gap detail (shot 21, sound rises
through the floor — this is the mechanism that makes "she hears everything"
plausible later). PASSES.
```

### S3 — Counting the day (shots 23–30)
```
SEQUENCE: Counting the day (23–30)

CHAIN CHECK
• Goal — Father's concealment tactic in action: hide the larger pile from ต้น.
• Obstacle — ต้น's curiosity (shot 25, "พ่อนับเงินอยู่เหรอ") threatens to expose the
  secret ahead of schedule. LOCAL (threatens this stage of concealment only).
• Tactic — Father deflects ("เปล่า เช็คยอดเฉยๆ", shot 26) — forced by the question,
  reasonable given he doesn't want his son carrying guilt. ต้น's own tactic —
  watching unseen from the stairwell (29) — is the one that actually matters:
  it returns real information (there is a secret envelope, there is a hiding
  place) and narrows his search. Passes cleanly on ต้น's side.
• Reversal — Not owed; this sequence is absorbed into S5's Big Turn, it does
  not resolve independently.
• Value Shift — Not owed yet.

REMOVAL TEST: Cut 23–30 — does the chain hold? NO — Section 6 of the script
(continuity audit) already establishes the envelope and tin box must be set
up before shots 47–58 use them. PASSES.
```

### S4 — Lender arrives, public (shots 31–36)
```
SEQUENCE: Dinner rush, a polite man walks in (31–36)

CHAIN CHECK
• Goal — Father must keep the lender's visit reading as an ordinary customer
  interaction in front of a full room (and his son).
• Obstacle — The lender's public presence risks exposing the shame/threat in
  front of witnesses. LOCAL (threatens this stage — the "keep it hidden in
  public" stage — not yet the whole goal).
• Tactic — Forced politeness, redirect to a table, then step outside privately
  (35). Reasonable, and it works exactly long enough to buy the private scene
  that follows — returns the information "this can only be handled off-stage,"
  which is what sends both men into the alley.
• Reversal — None claimed (pure escalation scene, which the skill explicitly
  allows).
• Value Shift — None yet.

REMOVAL TEST: PASSES — required transition into S5.
```

### S5 — Back alley + Big Turn (shots 37–45)
```
SEQUENCE: Out back / the number lands (37–45) — the spine of the episode

CHAIN CHECK
• Goal — Father: pacify the lender, buy one more day (39, "พรุ่งนี้ผมหาให้ครบแน่นอน").
• Obstacle — Physical threat + informational threat. GLOBAL — this is the
  first moment either the father's safety or the secret's survival is
  genuinely, seriously at risk.
• Tactic — Father's plea is forced, reasonable on his knowledge (he does not
  know ต้น is watching). It fails locally (he's shoved, 40) but the FAILURE
  returns critical information — not to him, but to the audience/ต้น, via the
  lender's own line (42, "สี่ปีแล้วนะพี่") stating the timeframe. ต้น's silent
  arithmetic (43, "...สี่ปี... ค่าเทอมผม...") is the tactic that actually resolves
  the search: he connects the four years to his own tuition timeline. This is
  a genuinely well-built asymmetric-information beat — the father's tactic
  "succeeds" from his own POV (he thinks the secret held), while its failure
  is invisible to him and total for the one person it was meant to protect.
  That's dramatic irony, not a wheel-spin — correctly used here.
• Reversal — HIDDEN AGENCY REVEALED. The money ต้น believed was his father's
  honest, ordinary earnings was secretly the site of ongoing harm the whole
  time. Textbook clean example of this reversal form.
• Value Shift — BEFORE: "a tired, hardworking, honest noodle-shop dad, quietly
  proud, protective." AFTER: "he has been absorbing violence and a 4-year debt
  in total silence to fund my life — why has he never told me; is this
  foolish pride or protection?" Clean, nameable, strong. This is the
  strongest single beat in the episode.

REMOVAL TEST: PASSES — this is the scene everything else exists to earn.
```

### S6 — Give it back (shots 46–53)
```
SEQUENCE: Give it back (46–53)

CHAIN CHECK
• Goal — ต้น's NEW goal, established "one minute ago" per the Goal rule's own
  example (the stink from the previous scene counts as the past this scene
  fixes): relieve his father of the debt by refusing the money.
• Obstacle — Father's flat refusal (50, "เอาไปเถอะ") threatens whether ต้น's new
  goal can succeed at all. GLOBAL — this is the crux of the whole series'
  theme (can love be refused back).
• Tactic — Direct refusal (48) is forced and reasonable given what he just
  learned; it fails, and the failure teaches ต้น that logic won't work, forcing
  him to escalate to naming the secret aloud (51, "ผมรู้เรื่องเชิดแล้ว") — this
  DOES return new information into the scene itself (now the father knows his
  son knows). Clean tactic-escalation, passes well.
• Reversal — MY OWN ACTION FLIPS ON ME, on สมชาย: his life's tactic (silence,
  built specifically to protect his son from guilt) produces the opposite of
  its intended effect — it is the very thing now making his son want to
  refuse the gift and feel worse, not better.
• Value Shift — BEFORE (carried over from S5): "secretly suffering to fund my
  life." AFTER: "he must now watch his own protection backfire in front of
  him, and still won't yield." Verdict deepens toward something closer to
  unshakeable, near-stubborn love — sets up the payoff correctly.

REMOVAL TEST: PASSES.
```

### S7 — Payoff (shots 54–56)
```
SEQUENCE: The line, and the noodles (54–56)

CHAIN CHECK
• Goal — Resolution of both goals: father's (the money must still mean what he
  intended) and ต้น's (relieve him of it) collide and the father's wins.
• Obstacle — None new; the standoff obstacle from S6 is what's being resolved
  here, not a fresh one.
• Tactic — Physically closing ต้น's fingers over the envelope (54) is the tactic
  that finally defeats ต้น's refusal — forced by his refusal, and it works.
• Reversal — SEE FINDING BELOW. This is the CEO's direct Q3, answered in
  full: NOT a reversal by the strict engine definition. By the end of shot 53
  ("held eye contact"), the audience already fully expects the father to
  refuse the refusal and explain himself with some form of "I did this for
  you." Shots 54–55 deliver exactly that, with total craft and the episode's
  title line — but they do not turn against any expectation the audience
  doesn't already hold after S6. The real reversal (hidden agency) and the
  real value shift already fired in S5 and sharpened in S6. Shots 54–55 are a
  CAPSTONE / thematic restatement of an already-completed shift, not a new
  reversal event.
• Value Shift — Because there is no new reversal, there is no new independent
  value shift here either — the line intensifies the S5→S6 verdict
  ("unshakeable love") rather than moving it somewhere new. It is real
  writing doing real work (it is the theme statement, and it is what
  crystallizes ต้น's OWN value-shift on his father into words) — it is not
  wasted — but if the goal was for the payoff line itself to be a reversal
  moment, it currently is not one. It is, as the CEO's own question puts it,
  functionally close to "just a sad line," dressed as a climax.

REMOVAL TEST: PASSES on Goal grounds (this is the payoff the whole episode
promises) — the finding above is about reversal mechanics, not about whether
to keep the scene.
```

### S8 — Aftermath (shots 57–58)
```
SEQUENCE: Aftermath (57–58)

CHAIN CHECK
• Goal — Dénouement; closes the job-search thread planted at 12–15 ("กินก่อน
  ไปสมัครงานนะ", 58) — a genuine callback, not an orphan.
• Obstacle/Tactic/Reversal — None claimed; correctly a quiet landing beat.
• Value Shift — Confirms the new baseline (unspoken grief/gratitude) without
  overplaying it.

REMOVAL TEST: PASSES — required to land the tone and pay off the job thread.
```

### S9 — Cliffhanger (shots 59–60)
```
SEQUENCE: What the witness reaches for (59–60) — first resolution beat of the
season-length sequence opened at S2

CHAIN CHECK
• Goal — Grandma's private goal (warn / act) from S2, still live.
• Obstacle — Same physical incapacity, now apparently being defeated for the
  first time — GLOBAL, cross-episode.
• Tactic — Her hand moving toward something hidden (60) is a NEW tactic,
  never attempted before in the episode — genuinely forced by the goal's
  urgency (this is likely her last chance), and it opens a brand-new jeopardy
  rather than resolving the old one. Correct cliffhanger mechanics.
• Reversal — HIDDEN AGENCY REVEALED, cleanly built: the character established
  all episode as purely passive/helpless turns out to have been capable of
  something all along.
• Value Shift — BEFORE: "frail, trapped, can only witness — sympathetic and
  helpless." AFTER: "she has been quietly capable of more than anyone assumed
  — what does she know, what is she about to do?" Clean, strong, and it is
  the answer to CEO Q4 (see §7).

REMOVAL TEST: PASSES — without this, the episode ends fully closed with no
reason to return for EP2.
```

---

## 3. Removal-test failure table

| Scene (scene-map #) | Shots | Verdict | Why |
|---|---|---|---|
| 1 — Cold open | 1–2 | **CONDITIONAL FAIL** | Redundant with S5 (37–42) on pure plot-causal grounds. Recommended to KEEP anyway for retention-hook reasons (CEO's call — see §7 Q2), but do not budget it as load-bearing plot. |
| 2 — Morning opens the shop | 3, 5, 6, 7, 9, 10 | **HARD FAIL** | Zero jeopardy, zero causal link forward, nothing downstream references their content. |
| 2 — Morning opens the shop | 4, 8, 11 | **THIN PASS** | Minimal causal freight (shop's public warmth, the only diegetic naming of "ต้น"). Keep, but they're doing very little work per second of runtime. |
| 3–11 (all other scenes) | 12–60 | **PASS** | Each carries a real jeopardy, a real payoff dependency, or both. |

**Count: 2 scenes fail the removal test outright** (Scene 1 conditionally,
Scene 2 hard), covering **7 individual shots** (1, 2, 5, 6, 7, 9, 10) — plus 3
more shots (4, 8, 11) flagged as thin-but-retained.

---

## 4. Inert reversals

Checked all four reversal candidates in the episode against the Value-Shift
test (name a before-verdict AND an after-verdict, or it's inert):

1. S5 Big Turn (43–45) — before/after named clearly in §2. **NOT inert.**
2. S6 refusal escalation (51–53) — before/after named clearly in §2. **NOT inert.**
3. S9 cliffhanger (59–60) — before/after named clearly in §2. **NOT inert.**
4. **S7 payoff line (54–55) — INERT AS A REVERSAL.** No before/after verdict
   distinct from what S5–S6 already established. It restates and intensifies
   an existing shift; it does not create one. This is the CEO's Q3, answered
   directly: the line is doing real thematic and dialogue work, but
   structurally it is currently "just a sad line," not a reversal.

**Count: 1 of 4 reversal candidates is inert** — and it's the title-line payoff,
which is exactly the highest-stakes place for this to go unnoticed. See §6 for
the fix.

---

## 5. Value-shift trajectory (whole episode, on สมชาย — the character the audience keeps re-judging)

```
หาเลี้ยงลูกอย่างซื่อสัตย์ (baseline, S1)
  → กำลังปิดบังบางอย่าง (S3, mild suspicion, still sympathetic)
  → พลีชีพเงียบๆ มา 4 ปี (S5 Big Turn — the major shift)
  → ดื้อรั้นจนน่าห่วง / รักที่ปฏิเสธไม่ได้ (S6 refusal standoff — deepens, doesn't repeat)
  → [S7 restates rather than advances this — see finding above]
```

**Assessment: the trajectory is a genuine deepening arc, not oscillation** —
each stage revises the verdict rather than flip-flopping, which is exactly
what the skill asks the trajectory to do. The one weak link is structural, not
directional: S7 (payoff) does not add a new rung to this ladder, it re-climbs
the top rung more loudly. Fixing S7 to add one more rung (see §6) would make
this a clean five-stage arc instead of four-stages-plus-an-echo.

Secondary arc on ต้น (for completeness, not separately audited in full):
quietly frustrated new-grad (S1) → watchful, suspicious of the money (S3) →
shattered (S5) → refusing out of guilt (S6) → grieving acceptance (S8). Also a
clean deepening arc, and it's the one S7's line is actually landing on best —
ต้น's own value-shift completes there even though สมชาย's doesn't get a new one.

---

## 6. WEAKEST POINT

**The dead zone at shots 3–11 (0:16–1:28, ~72 seconds, 9 shots, 5 of them zero-jeopardy).**

Not the payoff-line reversal finding (§4) — that's a real defect, but the
scene still works emotionally even un-fixed, and it's a five-second polish
problem, not an existential one. The dead zone is where the episode's two
explicit success criteria collide hardest: it's the biggest block of scenes
that fails the removal test (structure), AND it's exactly the runway before
the first hook where a cold Facebook stranger has nothing to hold onto (CEO
Q1, retention). Fixing it recovers both at once — that's why it's the single
highest-leverage element in the script.

### WHAT IF…

**1. Minimal fix** (preserve the shot list, touch only the weakest point):
Move the job-rejection phone-buzz cue from shot 12 forward into shot 6 — same
shot count, same shot order, same runtime, only the SOUND CUE and one gesture
move earlier. This means jeopardy is present (quietly, in the background)
from ~0:40 instead of ~1:28, halving the true dead-air window without
touching a single other shot.

```
[SHOT 6 - 8s - 9:16] — REVISED

INT. NOODLE SHOP - MORNING

TON leans toward a seated customer, notepad in hand, asking his
order. His phone buzzes once in his apron pocket -- he doesn't
check it. A flicker crosses his face before he refocuses on the
customer.

TON
(polite)
เส้นเล็กหรือเส้นใหญ่ครับ
```

**2. Clean fix** (fully works, departs more): Recompose the 9 routine shots
into 5, each carrying routine business AND a visible pressure-tell from the
first shot of the block, instead of arriving cold at shot 12. Example
replacement for the current shots 3–4:

```
[SHOT 3 - REVISED]

EXT./INT. NOODLE SHOP - MORNING

The roll-up shutter rattles open. SOMCHAI pulls it the last foot
by hand -- a wince, quickly smoothed over, as his ribs catch. He
straightens his apron and turns to the street with a customer's
smile already in place.

[SHOT 4 - REVISED]

INT. NOODLE SHOP - MORNING

SOMCHAI gestures a customer to a table, warm and unhurried. As he
turns back to the kitchen the smile drops for exactly one frame --
a hand pressed briefly to his side -- before TON glances over and
it's gone.

SOMCHAI
(warm, tired)
สวัสดีครับ นั่งได้เลยครับ
```
This folds S0's cost directly into the "ordinary" scenes instead of leaving
it to sit dormant for a minute, and gives the audience a reason to keep
watching that isn't just "trust me, something's coming." Shot count drops
from 9 to ~5 in this block, which also lowers generation cost for scenes
that were failing the removal test anyway.

**3. Optional** (only if it adds something): Thread the SOUND from the cold
open (a strained breath, a single wince-cue) faintly into shots 3–4 rather
than showing it — connecting S0 to S1 without visually repeating the alley
beating, and partially answering the S0/S5 redundancy finding in §3 at the
same time. Skip this if it starts to feel like the audience is being told
twice; it's a nice-to-have, not required.

---

## Secondary finding — fixing the inert payoff-line reversal (§4)

Not the weakest point, but named directly by CEO Q3, so given its own
(lighter) fix:

**Minimal:** Add one new piece of information to shot 55 that ต้น (and the
audience) did not have before — e.g., a single clause revealing this was
close to the LAST payment, or naming an amount that recontextualizes the
scale of what's already been sacrificed. Keeps the line, adds one clause that
turns it from restatement into revelation:

```
[SHOT 55 - REVISED]

INT. NOODLE SHOP, COUNTER - NIGHT

SOMCHAI holds his son's folded hands a moment longer.

SOMCHAI
(tender, final)
ไม่ต้องรู้ว่ามันมาจากไหน แค่ใช้มันให้คุ้ม... งวดสุดท้ายแล้ว
```
("...it's the last payment." — turns "I did this for you" into "it's almost
over," which the audience did not know and which recontextualizes everything
in S5–S6: the debt they thought was open-ended was about to end regardless —
raising, not lowering, the tragedy of what it cost, and giving S7 its own
rung on the value-shift ladder instead of echoing S6's.)

**Clean:** Reframe shot 54–55 so ต้น speaks the theme back at his father,
having pieced it together himself, and สมชาย's only reversal is that he lets
himself be SEEN reacting to it for the first time all episode (a genuine
"my own action flips on me" beat — his life-long composure fails exactly when
he's finally being understood, not exactly when he's threatened). This is a
bigger rewrite and only recommended if the CEO wants S7 to carry its own full
reversal rather than a one-clause fix.

---

## 7. CEO questions — answered directly

**Q1: Does this episode hold for 6–12 minutes?** Runtime is exactly 8:00,
inside the target band. The structural risk isn't length, it's placement: a
stranger has nothing but atmosphere from shot 3 to shot 11 (0:16–1:28) before
the first real jeopardy (the job-rejection thread) surfaces, and that thread
itself doesn't pay off until shot 58. Name the exact shots where a stranger
would leave: **shots 5, 6, 7, 9, 10** — the zero-jeopardy block. Fix in §6.

**Q2: Is the hook in the first 3 seconds?** Shot 1 reads instantly even
silent (a man shoved against a wall, near-darkness) — that mechanic works
cold, no dialogue needed, and it's already positioned as shot 1 in both the
teaser and the full cut. The finding to weigh: shots 1–2 fail the removal
test against S5, which restages the same information in full context five
minutes later — so the episode is spending its best 3-second hook on content
it's about to show properly anyway. Recommend KEEPING it for the hook (that's
a real, separate justification the removal test doesn't capture) but treating
it as a hook cost, not a plot investment — the optional fix in §6 tier 3
gives it a small callback function instead of leaving it purely redundant.

**Q3: Does the payoff line land as a reversal with a real value shift, or is
it just a sad line?** Audited in full in §2 (S7) and §4. Answer: **currently,
it is functionally a sad line, not a reversal** — no before/after verdict on
สมชาย exists at 54–55 that wasn't already established by shot 53. It is not
wasted (it's the theme statement and it completes ต้น's own arc), but it does
not do what a reversal does. Fix given above (minimal: one clause of new
information; clean: a bigger rewrite).

**Q4: Is there a reason to come back for EP2?** Yes, and it's clean: the
grandma cliffhanger (shots 59–60) is a properly built, unresolved,
GLOBAL-scale jeopardy — a hidden-agency reversal with a genuine before/after
verdict shift, deferred on purpose. The specific unresolved jeopardy: what
has she been hiding, and what is she about to do with it now that she's
apparently able to move for the first time in the episode. This is the
strongest "come back" hook in the script and needs no fix.

---

## Summary for the CEO

- **2 scenes fail the removal test outright** (Scene 1 cold-open —
  conditional, recommended to KEEP for hook reasons; Scene 2 morning
  routine — hard fail), covering 7 shots (1, 2, 5, 6, 7, 9, 10), plus 3 more
  thin-but-keep shots (4, 8, 11).
- **1 of 4 reversals is inert** — the title payoff line (shots 54–55).
- The value-shift trajectory on สมชาย is a genuine deepening arc, not
  oscillation — the one weak link is structural (S7 doesn't add a new rung).
- Weakest point: the zero-jeopardy dead zone at shots 3–11 — fixed above in
  three tiers, minimal to clean.
- The episode is NOT being recommended for shortening or clip-splitting.
  Every fix above either keeps the shot count flat (tier 1) or reduces it
  only as a side effect of cutting content that already failed the removal
  test (tier 2) — none of it is format-driven trimming.
