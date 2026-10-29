# M4 PROOF: EP2 Shot Prompts - Current Way vs Library Way

Evaluation report comparing the current EP1 baseline prompt pattern against the new Cinematic Prompt Library (`CMO_Knowledge_CinematicPrompts`) across five representative shots from ILAG S1 EP2 "ล้มบอลซอย".

- **Target Engine:** Google Flow · Omni 1.1 Flash · Mode องค์ประกอบ (Ingredients)
- **Target Spec:** Vertical 9:16 · 720p · 8–10s · Daylight · Single Continuous Take
- **Location:** `soi__field` (red-dirt football pitch at the end of the soi, bamboo goals, trophy tent)
- **Cast Handles Reused:** `@friend__jersey`, `@boy__tiger`, `@ton__work`, `@mee__rider`, `@collector__work`, `@sri__apron`, `@fon__mint`

---

## SHOT A: The Bribe
**Beat:** เสี่ยบอย hands a "ค่าเหนื่อย" envelope to an adult soi footballer to fake an injury before the match.

### 1. Current Way (EP1 Baseline Pattern)

### SHOT A · 0:50–0:58 · 8s · E2-S08 · a red-dirt football pitch at the end of the soi · เสี่ยบอย, นักบอลซอย
**ATTACH** 1) `@boy__tiger`→REF_0 · 2) `@soi__field`→REF_1
**บทพูด** เสี่ยบอย `"รับซองค่าเหนื่อยนี้ไป พรุ่งนี้ไม่ต้องลงแข่ง แกล้งเจ็บอยู่บ้านซะ"` · arrogant smirk, thrusting white envelope
```
Use <IMAGE_REF_0> as the character reference for boy__tiger. Use <IMAGE_REF_1> as the location reference for soi__field.

In an open-air red-dirt football pitch at the end of a neighborhood soi, with crude bamboo goalposts, patchy tropical grass along the touchlines, a white canvas tournament tent shading a plastic folding table with a polished golden trophy, and sun-baked compacted red soil <IMAGE_REF_1>, the morning, bright natural morning sunlight in dry weather. a stocky Thai man of twenty-eight with a slight paunch, round face, an undercut hairstyle slicked back with wet-look pomade, gold-rimmed sunglasses pushed up on top of his head, a thick gold chain necklace around his neck, a gold wristwatch, wearing a short-sleeved rayon camp shirt printed with a bold yellow-and-black tiger stripe pattern with top buttons open, dark tailored trousers and black leather loafers, chewing gum <IMAGE_REF_0>, an athletic Thai man of twenty-four with sun-tanned skin, buzz-cut black hair, dark focused eyes, wearing an unbranded faded green cotton sports jersey with no numbers and no logos, dark athletic shorts, and worn canvas training shoes: the man in the tiger-print shirt, smirking arrogantly, thrusts a thick plain white paper envelope into the chest of the adult soi footballer; the adult footballer hesitates with lowered eyes and reluctantly takes the envelope; dry red dust kicks up around their feet; the instant he finishes, the man in the tiger-print shirt pats his shoulder with mocking familiarity.

The man in the tiger-print shirt <IMAGE_REF_0> speaks standard Central Thai with a Bangkok street slang cadence, in the loud nasal baritone voice of a Thai man of twenty-eight with a Bangkok street accent, arrogant smirk, thrusting white envelope, and says: "รับซองค่าเหนื่อยนี้ไป พรุ่งนี้ไม่ต้องลงแข่ง แกล้งเจ็บอยู่บ้านซะ"

The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Medium two-shot of a red-dirt football pitch at the end of the soi, the people stand in this order from screen-left to screen-right: the adult soi footballer then the man in the tiger-print shirt; the speaker faces the camera in three-quarter view with the mouth visible and speaks to the adult soi footballer, never looking into the lens. Contemporary Thai realist drama, vertical 9:16, shot on 35mm, strong expressive acting, faces clearly readable. Big, lively, theatrical Thai lakorn acting with no dead moments: from the first frame to the last, every person in frame keeps moving and keeps doing their own task; whoever is listening reacts with face, hands and body to every phrase and never stands still waiting for their turn.
```

### 2. Library Way

**Library entry used:** `shortfilm-ilag_lakorn-02` (Corrupt Manager Threatening Honest Adult Clerk)
**Why:** Supplies an established low-angle medium two-shot with optical compression, directional raking split daylight, and a cold moral drama color grade that turns a routine handoff into an ethical coercion standoff.

```
8s · 720p · 9:16 · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM

On an open-air red-dirt football pitch at the end of a neighborhood soi, crude bamboo goalposts stand against dry banana trees, while a white canvas tent shades a tournament table and a golden trophy. The morning sun bakes the dry clay earth.

Use <IMAGE_REF_0> as the character reference for boy__tiger: face, slicked undercut hair, gold chain necklace, and bold yellow-and-black tiger shirt only; ignore original background.
Use <IMAGE_REF_1> as the location reference for soi__field: red-dirt ground, bamboo goalposts, and white trophy tent only; ignore any original figures.

THE FRAME: Camera is locked off at waist height on a 50mm prime lens, framing an intimate low-angle medium two-shot. The adult soi footballer in a plain unbranded faded green jersey stands at screen-left in three-quarter view facing screen-right. The man in the tiger-print shirt <IMAGE_REF_0> stands at screen-right in three-quarter view facing screen-left, his mouth clearly visible to camera, never looking into the lens.

WHAT HAPPENS:
[0s-3s] The man in the tiger-print shirt steps aggressively into the footballer's personal space, extending a thick sealed plain white paper envelope toward the player's chest. The adult footballer tenses his shoulders and lowers his gaze.
[3s-5s] The man in the tiger-print shirt <IMAGE_REF_0>, arrogant: "รับซองค่าเหนื่อยนี้ไป พรุ่งนี้ไม่ต้องลงแข่ง แกล้งเจ็บอยู่บ้านซะ"
[5s-8s] Hold: The footballer takes the white envelope with trembling fingers; the man in the tiger-print shirt keeps his sneer locked in place; everyone holds position, no speech, no new action; only dry wind rustling the bamboo goal netting.

LIGHTING: Harsh 5600K tropical morning sunlight strikes from camera-right as a raking side key, casting deep split shadows across Boy's pomade and jawline, with dusty red earth bounce providing natural warm fill.
COLOR GRADE: Color grade: authentic Thai lakorn moral drama, rich terracotta red earth, vivid tiger yellow pop, deep shadow contrast, crisp cinematic skin tones.

CRITICAL NEGATIVES & HOUSE RULES:
The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Avoid: unnatural skin discoloration, physical strikes, brand logos on sportswear, camera shake, deformed hands.
```

### 3. 3-Line Diff
- **Camera & Optics:** Replaces uncalibrated generic 35mm with a locked-off 50mm prime lens at waist height in a low-angle two-shot to enforce visual power disparity.
- **Light & Grade:** Replaces flat natural sunlight with a 5600K raking morning side key, directional split facial modeling, and a dedicated terracotta-and-tiger lakorn grade.
- **Staging & Omni 1.1 Risk:** Introduces strict `[0s-3s]`/`[3s-5s]`/`[5s-8s]` beat timing and bounded reference scopes; risk on Flow Omni 1.1 is envelope edge warping during hand-to-chest transfer.

---

## SHOT B: Comic
**Beat:** Five adult soi footballers arrive at practice each sporting a white medical bandage in a different place; ต้น counts them in comic despair.

### 1. Current Way (EP1 Baseline Pattern)

### SHOT B · 1:30–1:40 · 10s · E2-S16 · a red-dirt football pitch at the end of the soi · ต้น, นักบอลซอยห้าคน
**ATTACH** 1) `@ton__work`→REF_0 · 2) `@soi__field`→REF_1
**บทพูด** ต้น `"หัว เข่า แขน ข้อเท้า ไหล่ เจ็บพร้อมกันทั้งห้าคน พรุ่งนี้จะเอาใครลงเตะครับ"` · exasperated comic tone, pointing and counting with grease-stained fingers
```
Use <IMAGE_REF_0> as the character reference for ton__work. Use <IMAGE_REF_1> as the location reference for soi__field.

In an open-air red-dirt football pitch at the end of a neighborhood soi, with crude bamboo goalposts, patchy tropical grass along the touchlines, a white canvas tournament tent shading a plastic folding table with a polished golden trophy, and sun-baked compacted red soil <IMAGE_REF_1>, the morning, bright natural morning sunlight in dry weather. a handsome Thai young man of nineteen with rustic down-to-earth good looks, a lean athletic build from mechanical labor, sun-tanned golden-brown skin, thick straight dark eyebrows, warm expressive dark almond-shaped eyes, short black hair with tapered sides, a strong jawline, a subtle hint of a small single canine snaggletooth when he smiles, and fingertips permanently stained with dark engine grease around the cuticles, wearing a plain heather-grey crewneck T-shirt with light oil smudges near the hem, faded dark blue jeans, worn dark canvas sneakers, and a folded red cotton work rag tucked into his back right pocket <IMAGE_REF_0>, five adult Thai male footballers aged twenty to twenty-six wearing mismatched unbranded cotton jerseys and sports shorts, standing in a ragged horizontal line, each conspicuously wrapped with a clean white medical bandage in a completely different spot: the first around his forehead, the second around his left knee, the third around his right forearm, the fourth around his left ankle, and the fifth around his right shoulder: the young man in the grey T-shirt paces past the line pointing his grease-stained index finger at each white bandage in sequence, his expression shifting from confusion to stunned exasperation; the five bandaged footballers look down at the dirt avoiding eye contact; the instant he finishes, the young man in the grey T-shirt drops both arms to his sides in utter comic disbelief.

The young man in the grey T-shirt <IMAGE_REF_0> speaks standard Central Thai with an everyday youth cadence, in the clear light tenor voice of a Thai man of nineteen, exasperated comic tone, pointing and counting with grease-stained fingers, and says: "หัว เข่า แขน ข้อเท้า ไหล่ เจ็บพร้อมกันทั้งห้าคน พรุ่งนี้จะเอาใครลงเตะครับ"

The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the seventh second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; exactly six adult people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Wide medium group shot of a red-dirt football pitch at the end of the soi, the people stand in this order from screen-left to screen-right: the young man in the grey T-shirt at screen-left facing screen-right toward the row of five bandaged footballers; the speaker faces the camera in three-quarter view with the mouth visible and speaks to the five footballers, never looking into the lens. Contemporary Thai realist drama, vertical 9:16, shot on 35mm, strong expressive acting, faces clearly readable. Big, lively, theatrical Thai lakorn acting with no dead moments: from the first frame to the last, every person in frame keeps moving and keeps doing their own task; whoever is listening reacts with face, hands and body to every phrase and never stands still waiting for their turn.
```

### 2. Library Way

**Library entries used:** `movie-comedy-01` (Clumsy Waiter Balancing Towering Dessert Plates) + `movie-comedy-02` (Confused Office Worker Tangled in Cables)
**Why:** Imports the wide screwball comedy composition and shadowless high-key sitcom illumination from `movie-comedy-01` and `02`, ensuring that all five distinct bandage positions and Ton's sequential finger gestures remain readable across a 6-person vertical frame.

```
10s · 720p · 9:16 · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM

On an open-air red-dirt football pitch at the end of the soi, crude bamboo goalposts frame the dry pitch while a white tournament tent stands at the touchline. Five adult soi players stand lined up under the clear morning sky.

Use <IMAGE_REF_0> as the character reference for ton__work: face, grease-smudged grey T-shirt, jeans, and red rag in back pocket only; ignore original background.
Use <IMAGE_REF_1> as the location reference for soi__field: red dirt ground, bamboo goals, and white trophy tent only; ignore original people.

THE FRAME: Camera is locked off at chest height on a 35mm wide lens, holding a wide comedy group framing. The young man in the grey T-shirt <IMAGE_REF_0> stands at screen-left in three-quarter profile facing screen-right. Five adult Thai footballers stand side by side in a sheepish row from center to screen-right, each displaying a white bandage on forehead, left knee, right forearm, left ankle, and right shoulder respectively.

WHAT HAPPENS:
[0s-4s] The five bandaged footballers shuffle in place looking sheepish. The young man in the grey T-shirt steps forward, pointing his grease-stained index finger sequentially from the head bandage down to the shoulder bandage.
[4s-7s] The young man in the grey T-shirt <IMAGE_REF_0>, exasperated: "หัว เข่า แขน ข้อเท้า ไหล่ เจ็บพร้อมกันทั้งห้าคน พรุ่งนี้จะเอาใครลงเตะครับ"
[7s-10s] Hold: The young man in the grey T-shirt plants both hands on his hips staring wide-eyed; all five footballers freeze in their awkward poses, no speech, no new movement; only dry wind flapping the tent canvas.

LIGHTING: High-key 5000K morning sunlight with open clay ground bounce provides flat, shadowless sitcom illumination, ensuring high contrast between skin tones and pure white cotton bandages.
COLOR GRADE: Color grade: lively screwball comedy, punchy bandage white pop, sun-baked red dirt ochre, faded jersey cotton hues, clean accessible sitcom contrast.

CRITICAL NEGATIVES & HOUSE RULES:
The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the seventh second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; exactly six adult people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Avoid: unnatural skin discoloration, brand logos on jerseys, hospital medical gore, blurred hands, distorted facial anatomy.
```

### 3. 3-Line Diff
- **Camera & Optics:** Uses calibrated 35mm wide comedy framing tailored for 6 figures in vertical 9:16 rather than an open unconstrained group shot.
- **Light & Grade:** Employs 5000K high-key sitcom bounce illumination to prevent bandage positions from being obscured by dark body shadows.
- **Staging & Omni 1.1 Risk:** Incorporates sequential counting beats `[0s-4s]`/`[4s-7s]`/`[7s-10s]`; severe Flow Omni 1.1 risk is facial distortion, merged limbs, and floating bandage artifacts across 6 simultaneous adult characters.

---

## SHOT C: The Turn
**Beat:** ไอ้ตี๋ secretly returns an envelope to ต้น beside the goalpost and names who took bribe money from เสี่ยบอย.

### 1. Current Way (EP1 Baseline Pattern)

### SHOT C · 4:15–4:23 · 8s · E2-S33 · a red-dirt football pitch at the end of the soi · ไอ้ตี๋, ต้น
**ATTACH** 1) `@friend__jersey`→REF_0 · 2) `@ton__work`→REF_1 · 3) `@soi__field`→REF_2
**บทพูด** ไอ้ตี๋ `"ผมเอาซองมาคืนครับช่างต้น เสี่ยบอยจ้างห้าคนนั้นแกล้งเจ็บหมดแล้วครับ"` · remorseful whisper, pressing envelope into Ton's hands
```
Use <IMAGE_REF_0> as the character reference for friend__jersey. Use <IMAGE_REF_1> as the character reference for ton__work. Use <IMAGE_REF_2> as the location reference for soi__field.

In an open-air red-dirt football pitch at the end of a neighborhood soi, with crude bamboo goalposts, patchy tropical grass along the touchlines, a white canvas tournament tent shading a plastic folding table with a polished golden trophy, and sun-baked compacted red soil <IMAGE_REF_2>, the afternoon, bright warm afternoon sun in dry weather. a lean Thai young man of nineteen with short black hair tipped with bleached-gold highlights, lively dark eyes, wearing a plain cobalt-blue sleeveless basketball jersey with white trim and no numbers, dark sports shorts, and blue rubber flip-flops <IMAGE_REF_0>, a handsome Thai young man of nineteen with rustic down-to-earth good looks, a lean athletic build from mechanical labor, sun-tanned golden-brown skin, thick straight dark eyebrows, warm expressive dark almond-shaped eyes, short black hair with tapered sides, a strong jawline, a subtle hint of a small single canine snaggletooth when he smiles, and fingertips permanently stained with dark engine grease around the cuticles, wearing a plain heather-grey crewneck T-shirt with light oil smudges near the hem, faded dark blue jeans, worn dark canvas sneakers, and a folded red cotton work rag tucked into his back right pocket <IMAGE_REF_1>: the young man in the basketball jersey, looking around anxiously, steps in close and presses a thick sealed plain white paper envelope into the young man in the grey T-shirt's grease-stained hands; the young man in the grey T-shirt lowers the soccer ball he was wiping and looks into his eyes with serious concern; the instant he finishes, the young man in the basketball jersey hangs his head in sincere remorse.

The young man in the basketball jersey <IMAGE_REF_0> speaks standard Central Thai with a fast casual youth cadence, in the fast bright tenor voice of a Thai man of nineteen, remorseful whisper, pressing envelope into Ton's hands, and says: "ผมเอาซองมาคืนครับช่างต้น เสี่ยบอยจ้างห้าคนนั้นแกล้งเจ็บหมดแล้วครับ"

The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Medium two-shot of a red-dirt football pitch at the end of the soi, the people stand in this order from screen-left to screen-right: the young man in the basketball jersey then the young man in the grey T-shirt; the speaker faces the camera in three-quarter view with the mouth visible and speaks to the young man in the grey T-shirt, never looking into the lens. Contemporary Thai realist drama, vertical 9:16, shot on 35mm, strong expressive acting, faces clearly readable. Big, lively, theatrical Thai lakorn acting with no dead moments: from the first frame to the last, every person in frame keeps moving and keeps doing their own task; whoever is listening reacts with face, hands and body to every phrase and never stands still waiting for their turn.
```

### 2. Library Way

**Library entries used:** `shortfilm-ilag_lakorn-04` (Humble Cleaner Returning Lost Golden Wallet) + `shortfilm-ilag_lakorn-10` (Reformed Adult Criminal Kneeling Before Parent)
**Why:** `shortfilm-ilag_lakorn-04` provides eye-level 50mm prime intimacy and an uplifting moral redemption grade specifically developed for ethical restitution, while `ilag_lakorn-10` provides precise micro-beats for genuine moral confession.

```
8s · 720p · 9:16 · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM

Beside a weathered bamboo goalpost on a red-dirt football pitch at the end of the soi, dry tropical trees throw soft afternoon shade across the compacted soil. A white tournament tent sits quiet in the far background.

Use <IMAGE_REF_0> as the character reference for friend__jersey: face, bleached-gold highlights, and cobalt-blue jersey only; ignore original background.
Use <IMAGE_REF_1> as the character reference for ton__work: face, rustic features, and grease-smudged grey T-shirt only; ignore original workshop elements.
Use <IMAGE_REF_2> as the location reference for soi__field: red dirt pitch, bamboo goalpost, and tournament tent only; ignore original people.

THE FRAME: Camera is locked off at eye level on a 50mm prime lens, framing an intimate medium two-shot. The young man in the basketball jersey <IMAGE_REF_0> stands at screen-left in three-quarter profile facing screen-right. The young man in the grey T-shirt <IMAGE_REF_1> stands at screen-right in three-quarter profile facing screen-left, holding a vintage leather soccer ball, his eyes locked on Tee.

WHAT HAPPENS:
[0s-3s] The young man in the basketball jersey glances furtively over his shoulder, steps forward, and holds out a thick plain white paper envelope with both hands, pressing it against Ton's forearm.
[3s-5s] The young man in the basketball jersey <IMAGE_REF_0>, remorseful: "ผมเอาซองมาคืนครับช่างต้น เสี่ยบอยจ้างห้าคนนั้นแกล้งเจ็บหมดแล้วครับ"
[5s-8s] Hold: Ton clasps the white envelope firmly with grease-stained fingers and nods once with grave understanding; Tee lowers his eyes in sincere relief; both hold position, no speech, no new movement; only dry leaves rustling along the goal line.

LIGHTING: Warm 3800K late-afternoon sunlight filters through roadside foliage, providing soft directional rim light across Ton's jaw and Tee's bowed neck, balanced by gentle red earth ambient bounce.
COLOR GRADE: Color grade: uplifting moral cinema, warm golden clay reflections, gentle amber highlights, deep cobalt blue jersey pop, sincere emotional clarity.

CRITICAL NEGATIVES & HOUSE RULES:
The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Avoid: unnatural skin discoloration, corporate logos, weeping or wailing, erratic camera drift, deformed fingers.
```

### 3. 3-Line Diff
- **Camera & Optics:** Replaces broad 35mm framing with a locked-off 50mm prime lens at eye level to isolate emotional integrity and eye contact.
- **Light & Grade:** Replaces harsh daylight with warm 3800K filtered afternoon rim lighting and a dedicated moral cinema redemption color grade.
- **Staging & Omni 1.1 Risk:** Introduces furtive approach and dual-handed envelope handoff beats `[0s-3s]`/`[3s-5s]`/`[5s-8s]`; Flow Omni 1.1 risk is hand-to-hand finger blending during envelope contact.

---

## SHOT D: The Twist
**Beat:** จ่าหมี asks the referee (the man with the brown sleeve + black waist bag) to open his pouch and exposes the bribe list envelope.

### 1. Current Way (EP1 Baseline Pattern)

### SHOT D · 6:45–6:53 · 8s · E2-S30 · a red-dirt football pitch at the end of the soi · จ่าหมี, คนเก็บค่าแผง
**ATTACH** 1) `@mee__rider`→REF_0 · 2) `@collector__work`→REF_1 · 3) `@soi__field`→REF_2
**บทพูด** จ่าหมี `"เปิดกระเป๋าคาดเอวหน่อยครับจารย์ ซองรายชื่อที่เสี่ยบอยให้มาอยู่ในนี้ใช่ไหม"` · firm authoritative voice, pointing at waist pouch
```
Use <IMAGE_REF_0> as the character reference for mee__rider. Use <IMAGE_REF_1> as the character reference for collector__work. Use <IMAGE_REF_2> as the location reference for soi__field.

In an open-air red-dirt football pitch at the end of a neighborhood soi, with crude bamboo goalposts, patchy tropical grass along the touchlines, a white canvas tournament tent shading a plastic folding table with a polished golden trophy, and sun-baked compacted red soil <IMAGE_REF_2>, the afternoon, bright warm afternoon sun in dry weather. a stocky Thai man of forty-five with short cropped black hair, a thick moustache, calm sharp dark eyes and a broad build, wearing a plain navy-blue riding jacket with no badge and no logo, dark trousers and black boots, a black full-face motorcycle helmet resting under his left arm <IMAGE_REF_0>, a weathered Thai man of forty-five with flat impassive features, wearing a navy-blue baseball cap with no logo, a plain brown short-sleeved polo shirt with no badge and no insignia, dark brown trousers, a black canvas zippered waist pouch buckled around his waist, and worn black slip-on shoes <IMAGE_REF_1>: the stocky man in the navy-blue riding jacket, firm and commanding, points an authoritative index finger directly at the man in the brown polo shirt's black canvas waist pouch; the man in the brown polo shirt stiffens in guilt and slowly pulls the pouch zipper open with trembling fingers, revealing a thick white paper envelope inside; the instant he finishes, the man in the riding jacket reaches forward to secure the envelope.

The stocky man in the navy-blue riding jacket <IMAGE_REF_0> speaks standard Central Thai with a calm friendly cadence, in the warm steady baritone voice of a Thai man of thirty-four, firm authoritative voice, pointing at waist pouch, and says: "เปิดกระเป๋าคาดเอวหน่อยครับจารย์ ซองรายชื่อที่เสี่ยบอยให้มาอยู่ในนี้ใช่ไหม"

The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Medium two-shot of a red-dirt football pitch at the end of the soi, the people stand in this order from screen-left to screen-right: the stocky man in the navy-blue riding jacket then the weathered man in the brown polo shirt; the speaker faces the camera in three-quarter view with the mouth visible and speaks to the weathered man in the brown polo shirt, never looking into the lens. Contemporary Thai realist drama, vertical 9:16, shot on 35mm, strong expressive acting, faces clearly readable. Big, lively, theatrical Thai lakorn acting with no dead moments: from the first frame to the last, every person in frame keeps moving and keeps doing their own task; whoever is listening reacts with face, hands and body to every phrase and never stands still waiting for their turn.
```

### 2. Library Way

**Library entries used:** `shortfilm-ilag_lakorn-08` (Disloyal Partner Caught Burning Financial Ledgers) + `movie-thriller-01` (Detective Inspects Locked Office at Midnight)
**Why:** Adapts the investigative tension, slow forward camera creep, directional beam keying, and moral justice color grade from `movie-thriller-01` and `ilag_lakorn-08` into an intense daytime legal exposure beat.

```
8s · 720p · 9:16 · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM

At the sideline tournament tent on a red-dirt football pitch at the end of the soi, a golden trophy sits on a plastic table under white canvas, overlooking the dusty field in late afternoon sun.

Use <IMAGE_REF_0> as the character reference for mee__rider: moustache, broad build, and plain navy-blue riding jacket only; ignore original motorbike.
Use <IMAGE_REF_1> as the character reference for collector__work: weathered face, navy-blue cap, brown polo shirt, and black canvas waist pouch only; ignore original market stalls.
Use <IMAGE_REF_2> as the location reference for soi__field: red dirt pitch, tournament tent, and trophy table only; ignore original background figures.

THE FRAME: Camera dollies forward slowly at waist height on a 35mm lens, closing in on a tense medium two-shot standoff. The stocky man in the navy-blue riding jacket <IMAGE_REF_0> stands at screen-left in three-quarter view facing screen-right. The weathered referee in the brown polo shirt <IMAGE_REF_1> stands backed against the tent pole at screen-right, his black canvas waist pouch prominent in the lower center frame.

WHAT HAPPENS:
[0s-3s] The stocky man in the riding jacket steps forward deliberately, leveling a rigid index finger at the referee's waist pouch. The referee gasps, freezing in cornered guilt.
[3s-5s] The stocky man in the navy-blue riding jacket <IMAGE_REF_0>, commanding: "เปิดกระเป๋าคาดเอวหน่อยครับจารย์ ซองรายชื่อที่เสี่ยบอยให้มาอยู่ในนี้ใช่ไหม"
[5s-8s] Hold: The referee slowly unzips the black canvas pouch with trembling hands, exposing a crisp white paper envelope corner; Cha Mee holds his piercing stare, no speech, no new movement; only the low hum of distant soi motorcycles.

LIGHTING: Raking 4500K late-afternoon sunbeam cuts through the tent canopy edge, creating high-contrast split lighting across the referee's anxious brow while keeping Cha Mee in authoritative silhouette.
COLOR GRADE: Color grade: criminal thriller climax, deep charcoal shadows, weathered earth browns, stark paper white pop, high drama moral justice.

CRITICAL NEGATIVES & HOUSE RULES:
The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most two people in the shot. The scene is lit entirely by bright natural daytime sunlight, with no night lighting, no darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Avoid: unnatural skin discoloration, physical violence, police badges, brand logos, erratic camera wobble, distorted hands.
```

### 3. 3-Line Diff
- **Camera & Optics:** Replaces static framing with a slow waist-height 35mm dolly creep to heighten investigative pressure during the confrontation.
- **Light & Grade:** Replaces flat ambient daylight with a directional 4500K sunbeam key slicing across the tent canvas and an authentic moral justice thriller grade.
- **Staging & Omni 1.1 Risk:** Adds structured accusation and unzipping beats `[0s-3s]`/`[3s-5s]`/`[5s-8s]`; Flow Omni 1.1 risk is fine-motor zipper animation and pouch cavity distortion.

---

## SHOT E: The AI Gag
**Beat:** The football abruptly changes direction mid-air and curves into the goal; เสี่ยบอย reacts in utter shock from the sideline.

### 1. Current Way (EP1 Baseline Pattern)

### SHOT E · 8:10–8:18 · 8s · E2-S35 · a red-dirt football pitch at the end of the soi · เสี่ยบอย
**ATTACH** 1) `@boy__tiger`→REF_0 · 2) `@soi__field`→REF_1
**บทพูด** เสี่ยบอย `"ลูกบอลมันเลี้ยวกลับลำกลางอากาศได้ยังไงวะเนี่ย โกงชัดๆ"` · loud baffled shout, clutching hair in disbelief
```
Use <IMAGE_REF_0> as the character reference for boy__tiger. Use <IMAGE_REF_1> as the location reference for soi__field.

In an open-air red-dirt football pitch at the end of a neighborhood soi, with crude bamboo goalposts, patchy tropical grass along the touchlines, a white canvas tournament tent shading a plastic folding table with a polished golden trophy, and sun-baked compacted red soil <IMAGE_REF_1>, the golden evening hour, low warm golden sunlight raking across the pitch, long soft shadows. a stocky Thai man of twenty-eight with a slight paunch, round face, an undercut hairstyle slicked back with wet-look pomade, gold-rimmed sunglasses pushed up on top of his head, a thick gold chain necklace around his neck, a gold wristwatch, wearing a short-sleeved rayon camp shirt printed with a bold yellow-and-black tiger stripe pattern with top buttons open, dark tailored trousers and black leather loafers, chewing gum <IMAGE_REF_0>: the man in the tiger-print shirt, watching from the sideline, gawks in wild disbelief as a black-and-white soccer ball floating through the air suddenly changes direction mid-air at an impossible sharp angle and flies into the bamboo goal; the instant he finishes, he clutches his slicked-back hair with both hands, mouth hanging wide open in utter shock.

The man in the tiger-print shirt <IMAGE_REF_0> speaks standard Central Thai with a Bangkok street slang cadence, in the loud nasal baritone voice of a Thai man of twenty-eight with a Bangkok street accent, loud baffled shout, clutching hair in disbelief, and says: "ลูกบอลมันเลี้ยวกลับลำกลางอากาศได้ยังไงวะเนี่ย โกงชัดๆ"

The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most one person in the shot. The scene is lit by warm low golden-hour sunlight, with no night darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Medium shot of a red-dirt football pitch at the end of the soi, the speaker faces the camera in three-quarter view with the mouth visible and speaks to someone just off-screen ahead, never looking into the lens. Contemporary Thai realist drama, vertical 9:16, shot on 35mm, strong expressive acting, faces clearly readable. Big, lively, theatrical Thai lakorn acting with no dead moments: from the first frame to the last, every person in frame keeps moving and keeps doing their own task; whoever is listening reacts with face, hands and body to every phrase and never stands still waiting for their turn.
```

### 2. Library Way

**Library entries used:** `movie-comedy-03` (Pompous Art Critic Staring at Wall) + `shortfilm-thai_everyday-04` (Motorcycle Taxi Rider Resting at Corner)
**Why:** Reconstructs the reaction using deadpan satirical comedy framing from `movie-comedy-03` on a 50mm prime lens, establishing sharp spatial depth separation between Boy's foreground pomposity and the surreal airborne physics behind him.

```
8s · 720p · 9:16 · ONE CONTINUOUS TAKE, NO CUTS, NO ZOOM

On the sideline of a red-dirt football pitch at the end of the soi, the low evening sun casts long dramatic shadows past crude bamboo goalposts. The white tournament tent stands at the far touchline.

Use <IMAGE_REF_0> as the character reference for boy__tiger: face, slicked undercut hair, gold chain necklace, and yellow-black tiger shirt only; ignore original street setting.
Use <IMAGE_REF_1> as the location reference for soi__field: red dirt ground, bamboo goals, and tournament tent only; ignore original figures.

THE FRAME: Camera is locked off at chest height on a 50mm prime lens, holding a deadpan medium shot. The man in the tiger-print shirt <IMAGE_REF_0> occupies the foreground at screen-left in three-quarter profile facing screen-right. In the deep background at screen-right, the bamboo goal stands open under the golden sky.

WHAT HAPPENS:
[0s-3s] In the background, an unbranded soccer ball sails toward the far post, then unnaturally pivots ninety degrees in mid-air with zero momentum loss, rocketing straight into the bamboo goal.
[3s-5s] The man in the tiger-print shirt <IMAGE_REF_0>, shocked: "ลูกบอลมันเลี้ยวกลับลำกลางอากาศได้ยังไงวะเนี่ย โกงชัดๆ"
[5s-8s] Hold: The man in the tiger-print shirt freezes clutching his pompadour hair with bulging eyes and mouth wide open, holding position completely; no speech, no new movement; only triumphant cheers echoing from off-screen.

LIGHTING: Raking 3200K golden-hour sun sweeps from camera-left, throwing warm specular highlights across Boy's pomade and casting long horizontal shadows across the red clay field.
COLOR GRADE: Color grade: satire comedy realism, vivid tiger yellow pop, deep sun-baked red dirt ochre, warm evening gold highlights, clean theatrical contrast.

CRITICAL NEGATIVES & HOUSE RULES:
The face of whoever is speaking stays in frame for the whole line.
This is one single continuous take with no cuts: the camera never cuts away to a close-up of anyone, and stays on the same framing for the whole clip.
Every line is finished by the fifth second; in the last three seconds nobody speaks and nothing new starts: everyone holds their position and only the ambient sound of the football pitch continues.
No subtitles, no captions and no on-screen text of any kind appear anywhere in the frame. Nobody else is in the frame: no passers-by, no customers, no crowds, no children; at most one person in the shot. The scene is lit by warm low golden-hour sunlight, with no night darkness and no neon glow. Nobody wears a uniform, an official badge, a lanyard or government emblems. Nobody holds, counts or hands over banknotes, paper currency, bills, cash or coins.
Avoid: unnatural skin discoloration, commercial brand logos on football, cartoon smoke trails, camera wobble, distorted hands.
```

### 3. 3-Line Diff
- **Camera & Optics:** Replaces unguided medium framing with a 50mm prime deadpan composition separating foreground character from background goal physics.
- **Light & Grade:** Replaces generic evening light with warm 3200K raking golden-hour sunbeams and a dedicated satire comedy realism color grade.
- **Staging & Omni 1.1 Risk:** Defines exact trajectory snap timing `[0s-3s]` followed by shock reaction `[3s-5s]` and frozen hold `[5s-8s]`; severe Flow Omni 1.1 risk is ball warping or generative morphing during mid-air vector transition.

---

## CMO Head-to-Head Comparison

| Shot | Expected Winner | Why |
|---|---|---|
| **A. The Bribe** | **Library Way** | The 50mm low-angle framing and 5600K raking split key elevate routine envelope handling into an intense lakorn moral confrontation. |
| **B. Comic** | **Current Way** | Flat staging and uniform lighting are significantly safer for Flow Omni 1.1 than complex comedy micro-beats across 6 simultaneous characters. |
| **C. The Turn** | **Library Way** | Eye-level 50mm moral cinema framing and warm 3800K rim light deliver the emotional weight of restitution cleanly. |
| **D. The Twist** | **Library Way** | The 35mm slow camera creep and directional 4500K beam key transform the referee confrontation into genuine investigative drama. |
| **E. The AI Gag** | **Current Way** | Simpler baseline staging reduces prompt density, giving Flow Omni 1.1 better odds of rendering the surreal mid-air ball physics without morphing. |

### Summary Recommendation for the CMO
The Cinematic Prompt Library (`CMO_Knowledge_CinematicPrompts`) is decisively superior for dramatic two-shots and moral confrontations (Shots A, C, D), where optical focal choice, directional color temperature, and timed three-beat structures substantially improve emotional tension and visual storytelling. However, for crowded group shots (Shot B with 6 people) and surreal physical gags (Shot E), the simpler baseline format remains safer against Flow Omni 1.1 generative failure modes (facial drift, limb fusion, and object morphing). We recommend adopting the library way as the default standard for all 1-to-2 character story beats, while falling back to baseline simplicity on high-complexity physical or multi-character scenes.
