# EP07 Story-Synced Beat Plates & Python Motion Plan (`plates.md`)

Episode: **EP07 — กฎ 5 ข้อของคนเฝ้าศาลาตั้งศพกะดึก วัดป่าห้วยหมอก**
Total Unique Beat Plates: **56 Plates (`S01-01` .. `S20-02`, including `S13-CALM` & `S13-REVEAL` for the Python Jump Scare)** — strictly **1 plate per narrated/spoken beat** (56 spoken lines across `c01..c20`), zero fixed-timer looping, zero Google Flow anywhere (per CEO picks 27 Nov 2026 `Q-20261127-1347-90cd`).

---

## Python Plate-Motion & Jump-Scare Architecture

### 1. Standard Beat Plate Motion (`/opt/MoonieXHQ/Work/tool4-demo/plate/render.py`)
Every shot (`1920x1080 @ 24fps`) separates its plate into:
- **Inpainted Clean Background (`clean`):**
  ```python
  a = fg[..., 3]
  hole = cv2.dilate((a > 140).astype(np.uint8) * 255, np.ones((11, 11), np.uint8))
  clean = cv2.inpaint(bg_bgr, hole, 12, cv2.INPAINT_TELEA)[:, :, ::-1]
  ```
- **Feathered Cutout Foreground (`obj`):**
  ```python
  al = cv2.GaussianBlur(np.clip((a.astype(np.float32) - 30) / 90, 0, 1), (0, 0), 1.0)
  obj = np.dstack([fg[..., :3].astype(np.float32), al * 255])
  ```
- **Per-Frame Affine Transform (`warp(img, cx, cy, ang, sc, dx, dy)`):**
  - Background `bgw` zooms/pans slowly (`bz = 1.0 + dz * u`, `dx_bg`, `dy_bg`).
  - Cutout `obj` moves independently (`breathe`, `rock`/`sway`, `creep`/`parallax`, `shake`, `down`, `slide`/`door`, `grow`) at stronger parallax (`dx_obj`, `dy_obj`, `ang`, `sc`) + atmospheric scrolling fog `fog(t, speed, amt)`, fluorescent flicker `fl`, radial vignette `vig`, and film grain `rng.normal(0, 5, (H, W, 1))`.

### 2. Python Jump Scare Beat (`S13-CALM` -> `S13-REVEAL`, `/opt/MoonieXHQ/Work/tool4-demo/scare/render.py`)
- **Pre-Scare Calm (`S13-CALM`, Beat #35 / `c13_01` + 3.0s dipped-bed hold):**
  - Ambience bed dips smoothly to `35%` (`-31.5 dB` low-passed drone retained, zero sudden silence drop).
  - Slow push-in onto the dark polished stainless-steel side of the coffin reflecting the covered portrait easel (`zoom(calm, W/2, H*0.45, 1.0 + 0.08*u, math.sin(t*7)*1.5, math.sin(t*5.3)*1.2)`), subtle flashlight tremor in the last 30% (`0.93 + 0.07*math.sin(t*50)*(u > 0.7)`), and a `0.25s` pre-sting voltage drop (`f *= 0.55`).
- **Sting & Reveal Lunge (`S13-REVEAL`, Beat #36 / `c13_02`, 6.0s Python scare):**
  - Hard cut on frame `0.0s` of `scare_sting_07_fs415510.wav` (or `scare_sting_04_fs366168.wav`) to `S13-REVEAL.png` (`FACE = (W * 0.52, H * 0.36)`).
  - Cubic punch-in lunge (`k = min(s / 0.18, 1); e = 1 - (1 - k)**3; sc = 1.55 - 0.55*e + 0.06*min(s / 6, 1)`) with decaying violent shake (`sh = 26 * math.exp(-s * 4.5)`).
  - First `0.5s`: horizontal motion smear (`cv2.blur(f, (int(1 + 30*(1 - e)), 1))`) + RGB chromatic split (`off = int(18*(1 - s/0.5))`, `np.roll` R/B channels by `±off`).
  - Frames `0..1`: white flash (`f = f*0.3 + 255*0.7`); Frames `2..4`: crimson flash (`f = f*0.75 + [150, 0, 0]*0.25`); after `0.6s`: broken fluorescent tube flicker (`0.8 + 0.2*(int(s*24) % 7 != 0)`).

---

## Shared Prompt Prefix (`<STYLE_LOC_PREFIX>`)
Every plate prompt below begins with the exact EP06-validated dark folk-horror cut-paper diorama lock:
> `Use the attached image as the exact style AND location reference: keep the identical layered cut-paper diorama texture, real paper fibre grain, crisp cut edges, quilled swirl details, charcoal and slate paper, room geometry, materials, lighting fixtures, and exact object designs from the attached plate. 16:9 wide frame. No text, no letters, no numbers, no readable writing anywhere: every sign, plaque, book cover, clock face and gauge is blank paper or unreadable scribble lines. No watermark. Layer preparation: clean uncluttered background behind each moving element, crisp closed silhouettes, clear contour gaps, no baked-in motion blur; bodies connected with distinct paper seams. Adults only (18+). Stylised dark folk-horror paper art, no gore, no blood. Pale neutral skin tone, no blush, no red face, no red ears.`

---

## Beat-by-Beat Plates Specification (56 Plates: `S01-01` .. `S20-02`)

### Block `c01` — Cold-Open Hook (Phase 1: Torn-Paper Border + Bottom Crimson Waveform, Zero Top-Left Text)

#### 1. Plate `S01-01` (Beat `c01_01` · `NARRATOR: Algenib`)
- **Beat Text:** คุณเคยสังเกตไหมครับว่า ทำไมศาลาตั้งศพไม้สักหลังในสุดของวัดป่าเก่าแก่หลายแห่ง ถึงมักจะใช้เชือกสายสิญจน์สีขาวพันคาดรอบรอยต่อฝาโลงเย็นสแตนเลสแล้วหยดเทียนขี้ผึ้งสีแดงผนึกทับไว้อีกชั้น ทั้งที่มีตัวล็อกเหล็กอยู่แล้ว... และทำไมสัปเหร่อรุ่นเก่าถึงสั่งนักสั่งหนาว่า ธูปดอกใหญ่ที่ปักอยู่ในกระถางทองเหลืองหน้าโลง ห้ามปล่อยให้ไฟมอดดับลงก่อนเวลาตีสี่เป็นอันขาด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `incense_smoke_and_thread` (`poly: [[44,34],[56,34],[56,74],[44,74]]`) — background slow push `bz = 1.0 + 0.04*u`; cutout tall incense stick + curling grey smoke + sacred thread knot sways gently (`ang = 1.4*math.sin(t*2.1)`, `dy = -4*u + 2*math.sin(t*2.8)`) with pulsing orange ember glow at `(W*0.50, H*0.56)` and cold ceiling tube flicker.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot looking straight at the elevated wooden altar dais of Funeral Pavilion 4 at night: the silver-grey stainless-steel cooling coffin bound horizontally along its lid seam with white sacred cotton thread and three dark-red wax seals, and in the foreground on the low teak table the tarnished brass incense urn holding one thick tall vigil incense stick with a glowing orange ember tip and a curling ribbon of grey paper smoke. No people.`

#### 2. Plate `S01-02` (Beat `c01_02` · `NARRATOR: Algenib`)
- **Beat Text:** ยิ่งไปกว่านั้น หากคุณเดินเข้าไปในศาลาสวดศพกะดึกแล้วเห็นขาตั้งกรอบรูปหน้าศพถูกคลุมทับด้วยผ้าดิบสีขาวและกลัดริบบิ้นดำไว้แน่นหนา จงจำไว้เลยครับว่า ห้ามเอื้อมมือไปเปิดผ้าขาวผืนนั้นขึ้นดูใบหน้าของคนในรูปเด็ดขาด ไม่ว่าคุณจะได้ยินเสียงเคาะเหล็กดังมาจากข้างในโลงเย็นสักกี่ครั้งก็ตาม
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `draped_portrait_cloth` (`poly: [[22,20],[46,20],[46,82],[22,82]]`) — background slow pull-back `bz = 1.05 - 0.03*u`; the white cloth draping the portrait frame ripples and sways at the lower hem (`ang = 1.5*math.sin(t*2.4)`, `dx = 3*math.sin(t*1.9)`, `dy = 2*math.sin(t*3.1)`), fog `fog(t, 22, 0.09)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up on the wooden tripod easel standing to the left of the stainless-steel cooling coffin: the rectangular portrait frame is completely covered by a heavy off-white cotton cloth pinned at the side with a plain black ribbon, its lower hem hanging loose in cold blue-grey shadow while the sacred-thread-bound corner of the metal coffin sits on the right. No people.`

#### 3. Plate `S01-03` (Beat `c01_03` · `NARRATOR: Algenib` — Ends with `"ย้อนกลับไปเมื่อสามวันก่อน"` into Phase 2 `THREE DAYS EARLIER`)
- **Beat Text:** เพราะความจริงแล้ว แขกในชุดไว้ทุกข์สีดำที่เดินฝ่าสายหมอกเข้ามานั่งฟังสวดบนเก้าอี้พลาสติกสีแดงหลังเที่ยงคืน อาจไม่ได้มาเพื่อไว้อาลัยให้กับศพในโลง... แต่อาจเป็นเจ้าของโลงที่ออกมายืนรอใครสักคนยื่นธูปให้ เพื่อสลับตัวเข้าไปนอนอยู่ในโลงเย็นแทนมัน... ย้อนกลับไปเมื่อสามวันก่อน
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `backrow_shadow_mourner` (`poly: [[35,28],[65,28],[65,86],[35,86]]`) — background slow push `bz = 1.0 + 0.05*u`; faint dark silhouette seated on the back-row red plastic chair breathes slowly (`sc = bz * (1 + 0.008*math.sin(t*2.0))`, `dx = -16*u` parallax) while thick grey fog drifts across the open doorway (`fog(t, 45, 0.14)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide reverse-angle shot looking from the altar down the central teak aisle of Pavilion 4 toward the open front doors and dark misty courtyard: four rows of dull crimson-red plastic chairs on left and right, and in the back row closest to the foreground sits one faint dark paper silhouette in black mourning clothes with head bowed motionless. No face visible.`

---

### Block `c02` — Arrival at Wat Pa Huai Mok (Phase 3: 100% Full-Bleed 1920x1080 Widescreen Cinema)

#### 4. Plate `S02-01` (Beat `c02_01` · `NARRATOR: Algenib`)
- **Beat Text:** เรื่องราวในคืนนี้เกิดขึ้นกับ เข้ม ช่างซ่อมระบบไฟฟ้าและเครื่องเสียงวัยยี่สิบเจ็ดปี ที่รับงานด่วนด้วยค่าแรงคืนละหนึ่งพันห้าร้อยบาท ให้เข้าไปเฝ้าเครื่องปั่นไฟสำรองที่วัดป่าห้วยหมอก วัดเก่าแก่เชิงเขาที่หม้อแปลงไฟฟ้าหลักเพิ่งถูกฟ้าผ่าเสียหายเมื่อตอนหัวค่ำ ท่ามกลางสายหมอกหนาทึบและอากาศเย็นจัดหลังฝนตกในเวลาห้าทุ่มครึ่ง
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_walking` (`poly: [[48,26],[72,26],[72,92],[48,92]]`) — background slow pan `bz = 1.0 + 0.03*u, dx_bg = -8*u`; Khem cutout creeps forward along the muddy path toward the Pavilion 4 steps (`dx = -32*u`, `dy = -2.2*abs(math.sin(t*3.8))`, `ang = 0.8*math.sin(t*3.8)`), ground mist `fog(t, 38, 0.15)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide exterior shot on the wet mud-and-gravel path outside Funeral Pavilion 4 at 11:30 PM in thick grey fog: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). walks along the puddle-strewn path carrying an aluminum flashlight toward the wooden veranda steps on the left.`

#### 5. Plate `S02-02` (Beat `c02_02` · `NARRATOR: Algenib`)
- **Beat Text:** หน้าที่ของเข้มคือการดูแลสายไฟหลักที่ลากจากเพิงเครื่องปั่นไฟดีเซลข้างเมรุเก่าท้ายวัด ไปจ่ายไฟเลี้ยงโลงเย็นสแตนเลสในศาลาตั้งศพหมายเลขสี่ ซึ่งเป็นศาลาไม้สักหลังสุดท้ายที่ตั้งแยกตัวอยู่ริมป่าไผ่ห่างจากกุฏิพระสงฆ์ออกไปเกือบสามร้อยเมตร
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `generator_and_cable` (`poly: [[55,40],[88,40],[88,88],[55,88]]`) — background push `bz = 1.0 + 0.04*u`; diesel generator cutout vibrates with engine judder (`dx = math.sin(t*42)*1.1`, `dy = math.sin(t*29)*0.9`) while the bare yellow bulb above the shed flickers (`0.85 + 0.15*math.sin(t*14)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide shot of the rear temple courtyard in dense night mist: on the right, the corrugated-tin generator shed where the dark iron diesel generator hums under a single dim yellow bulb, with a thick black rubber power cable snaking across the wet gravel past the base of the old whitewashed brick crematorium and its padlocked iron furnace door on the left. No people.`

#### 6. Plate `S02-03` (Beat `c02_03` · `KHEM: Puck`)
- **Beat Text:** ลุงอินครับ... ทำไมคืนนี้ทั้งวัดถึงเงียบเชียบไม่มีญาติผู้เสียชีวิตอยู่เฝ้าศาลาเลยสักคนล่ะครับ แล้วทำไมโลงเย็นใบนั้นถึงต้องเอาสายสิญจน์กับขี้ผึ้งแดงมาผนึกฝาโลงไว้แน่นขนาดนั้นด้วย
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_veranda` (`poly: [[42,18],[78,18],[78,94],[42,94]]`) — background slow push `bz = 1.0 + 0.05*u`; Khem cutout on the wooden veranda breathes and turns slightly toward the doorway (`sc = bz*(1 + 0.006*math.sin(t*2.3))`, `dx = -18*u`, `ang = 0.5*math.sin(t*1.5)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up on the wooden veranda of Pavilion 4: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). stands at the top of the teak steps looking uneasily through the open wooden doors toward the sacred-thread-bound cooling coffin inside.`

---

### Block `c03` — Lung In Hands Over the Red Rulebook

#### 7. Plate `S03-01` (Beat `c03_01` · `NARRATOR: Algenib`)
- **Beat Text:** ลุงอิน สัปเหร่ออาวุโสวัยหกสิบสี่ปีผู้มีผิวกร้านแดดและสวมเชือกถักลงอาคมพร้อมตะกรุดทองเหลืองดอกใหญ่รอบคอ ไม่ได้ตอบคำถามนั้นในทันที ชายชราก้าวเข้ามาที่โต๊ะเวรไม้หน้าศาลา วางสมุดปกแข็งสีแดงเข้มเล่มหนึ่งคู่กับมัดธูปเทียนดอกใหญ่และกระดิ่งทองเหลืองด้ามไม้ลงตรงหน้าของเข้ม
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `lung_in_arm_book` (`poly: [[24,18],[64,18],[64,92],[24,92]]`) — background push `bz = 1.0 + 0.04*u`; Lung In cutout lowers his arm placing the red hardbound notebook onto the wooden watch desk (`dy = 10*smooth(u/1.4)`, `ang = -1.8*smooth(u/1.4)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium two-shot at the wooden watch desk near the entrance of Pavilion 4: Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). places a dark-red hardbound notebook, a bundle of thick vigil incense sticks, and a brass hand-bell on the table in front of Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture).`

#### 8. Plate `S03-02` (Beat `c03_02` · `LUNG_IN: Charon`)
- **Beat Text:** ศพในโลงนี้จมน้ำตายในอ่างเก็บน้ำท้ายเขื่อนเมื่อคืนวันพระเดือนดับ... พระท่านสั่งห้ามเผาก่อนครบสามราตรี เอ็งรับเงินค่าจ้างไปแล้วก็ต้องนั่งเฝ้าอยู่แค่ที่โต๊ะเวรหน้าศาลาสี่จนกว่าจะหกโมงเช้า เปิดสมุดปกแดงเล่มนี้อ่านกฎห้าข้อให้ขึ้นใจ แล้วทำตามทุกบรรทัดถ้ายังอยากมีลมหายใจกลับออกไปตอนเช้า
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `lung_in_closeup` (`poly: [[26,14],[74,14],[74,95],[26,95]]`) — background slow zoom `bz = 1.0 + 0.06*u`; Lung In cutout breathes heavily and points one weathered finger down at the red notebook (`sc = bz*(1 + 0.007*math.sin(t*2.1))`, `dy = 3*math.sin(t*1.8)`, `dx = -14*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Tight medium close-up on Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). standing beside the wooden watch desk under dim cold fluorescent light, pointing one stern finger down at the dark-red hardbound notebook with a solemn warning gaze.`

#### 9. Plate `S03-03` (Beat `c03_03` · `KHEM: Puck`)
- **Beat Text:** เข้าใจแล้วครับลุงอิน ผมจะคอยดูระดับน้ำมันเครื่องปั่นไฟกับธูปหน้าโลงไม่ให้ดับตามที่ลุงบอกครับ... แต่ถ้าดึกๆ มีญาติของคนตายแวะมาจุดธูปเคารพศพ ผมเปิดไฟโถงหน้าศาลารับเขาได้ตามปกติใช่ไหมครับลุง
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_at_desk` (`poly: [[30,18],[76,18],[76,94],[30,94]]`) — background slow push `bz = 1.0 + 0.04*u`; Khem cutout rests his hand on the red notebook and leans slightly toward the open doorway (`dx = -15*u`, `sc = bz*(1 + 0.006*math.sin(t*2.4))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up of Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). standing behind the wooden watch desk with one hand resting on the dark-red hardbound notebook and the brass hand-bell beside it, looking questioningly toward the open pavilion doorway.`

---

### Block `c04` — Reading the Red Rulebook: Rules 1 & 2

#### 10. Plate `S04-01` (Beat `c04_01` · `NARRATOR: Algenib`)
- **Beat Text:** ลุงอินชะงักฝีเท้าที่หัวบันไดศาลา หันมามองหน้าเข้มด้วยแววตาขรึมจัดโดยไม่พูดอะไรสักคำ ก่อนจะก้าวลงบันไดไม้หายลับเข้าไปในม่านหมอกสีเทา ทิ้งให้เข้มยืนอยู่ลำพังภายใต้แสงไฟนีออนสีขาวซีดที่กระพริบส่งเสียงจี่เบาๆ เข้มรีบนั่งลงที่โต๊ะเวรแล้วเปิดสมุดปกสีแดงออกอ่านกฎทั้งห้าข้อทันที
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `lung_in_departing` (`poly: [[44,24],[72,24],[72,90],[44,90]]`) — background pull back `bz = 1.04 - 0.03*u`; Lung In cutout walks away down the steps into the swirling grey mist (`dx = 28*u`, `dy = 6*u`, `sc = bz*(1 - 0.04*u)`), heavy fog `fog(t, 48, 0.18)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium-wide shot from the pavilion veranda looking out into the foggy temple path: Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). steps down off the bottom wooden step and walks away into the dense grey mountain fog under the dim amber pole lamp.`

#### 11. Plate `S04-02` (Beat `c04_02` · `NARRATOR: Algenib` — Rule 1)
- **Beat Text:** กฎข้อที่หนึ่ง... ธูปดอกใหญ่ในกระถางทองเหลืองหน้าโลงเย็นต้องติดไฟอยู่ตลอดเวลา ห้ามปล่อยให้ธูปดับก่อนเวลาตีสี่เด็ดขาด เมื่อธูปไหม้ลงมาถึงขีดสีแดงที่ก้านธูป ให้ใช้ธูปดอกใหม่จ่อต่อไฟจากปลายธูปดอกเดิมแล้วปักลงไปทันที ห้ามใช้ไฟแช็กจุดใหม่เมื่อธูปดับไปแล้วเป็นอันขาด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `vigil_incense_urn` (`poly: [[36,24],[64,24],[64,86],[36,86]]`) — background tight push `bz = 1.0 + 0.06*u`; tall incense stick + smoke plume sways gently (`ang = 1.1*math.sin(t*2.2)`, `dy = -3*u`) with pulsing orange ember glow around the burning tip above the painted red ring mark on the lower stick.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme close-up on the tarnished brass incense urn on the low teak table in front of the cooling coffin: one thick tall vigil incense stick stands in the grey ash with a glowing orange ember at the top, a thin painted crimson-red ring mark near the lower third of the wooden stick, and a wisp of grey paper smoke rising in the cold blue-grey light. No people.`

#### 12. Plate `S04-03` (Beat `c04_03` · `NARRATOR: Algenib` — Rule 2)
- **Beat Text:** กฎข้อที่สอง... ขาตั้งกรอบรูปหน้าศพทางด้านซ้ายของโลงเย็นถูกคลุมด้วยผ้าดิบสีขาวไว้แล้ว ไม่ว่าลมพัดแรงแค่ไหนหรือมีใครมาถามชื่อคนตาย ห้ามเลิกผ้าขาวขึ้นดูใบหน้าในรูปถ่าย และห้ามจัดกรอบรูปนั้นใหม่เด็ดขาด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `white_cloth_easel` (`poly: [[26,16],[68,16],[68,90],[26,90]]`) — background slow push `bz = 1.0 + 0.05*u`; the draped white cloth cutout trembles slightly as if breathed on from behind (`dx = 2.0*math.sin(t*3.4)`, `ang = 0.9*math.sin(t*2.0)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Close-up on the wooden tripod portrait easel to the left of the stainless-steel cooling coffin: the portrait frame is completely concealed beneath a draped off-white cotton cloth pinned with a black mourning ribbon, a faint dark contour of a face barely suggested behind the thick fabric layers. No people.`

---

### Block `c05` — Reading the Red Rulebook: Rules 3, 4 & 5

#### 13. Plate `S05-01` (Beat `c05_01` · `NARRATOR: Algenib` — Rule 3)
- **Beat Text:** กฎข้อที่สาม... หลังเวลาตีหนึ่งเป็นต้นไป หากมีคนสวมชุดไว้ทุกข์สีดำเดินขึ้นบันไดศาลามาขอธูปไปจุดหน้าโลง ห้ามยื่นธูปจากบนโต๊ะเวรให้ และห้ามเอ่ยปากเชิญเข้ามานั่งในศาลา ให้หยิบกระดิ่งทองเหลืองบนโต๊ะเวรสั่นหนึ่งครั้ง แล้วก้มหน้ามองสมุดปกแดงนิ่งๆ จนกว่าคนคนนั้นจะเดินลงบันไดกลับไป
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `red_book_and_bell` (`poly: [[26,28],[74,28],[74,84],[26,84]]`) — background push `bz = 1.0 + 0.05*u`; Khem's hands holding the open red notebook and the brass hand-bell on the desk shift subtly (`dx = 2.2*math.sin(t*2.6)`, `ang = 1.2*math.sin(t*3.0)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Over-the-shoulder close-up looking down at the wooden watch desk: Khem's hands hold open the dark-red hardbound notebook showing five horizontal red-stamped rule bars (unreadable lines, no letters or numbers), while beside the book sit the small brass hand-bell with a wooden handle and the bundle of thick unlit incense sticks. In the blurred background are the open front doors and misty steps.`

#### 14. Plate `S05-02` (Beat `c05_02` · `NARRATOR: Algenib` — Rule 4)
- **Beat Text:** กฎข้อที่สี่... เวลาตีสามสิบเจ็ดนาที หากได้ยินเสียงเคาะเหล็กดังมาจากด้านในโลงเย็น หรือเห็นหยดน้ำสีดำไหลซึมออกมาจากช่องระบายความเย็นด้านหลังแท่นตั้งศพ ห้ามแตะต้องสายสิญจน์บนฝาโลง แต่ให้รีบไปสับคันโยกเบรกเกอร์ไฟสำรองสีแดงที่เสาหน้าศาลาลงทันทีเพื่อเร่งความเย็นสูงสุด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `breaker_lever_clock` (`poly: [[32,18],[68,18],[68,86],[32,86]]`) — background slow zoom `bz = 1.0 + 0.05*u`; the red auxiliary breaker lever and wall clock cutout has a subtle metallic parallax shift (`dx = -14*u`, `dy = 4*u`) under flickering fluorescent light.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Close-up on the right wooden entrance pillar of Pavilion 4: a grey metal electrical breaker box with a prominent bright-red auxiliary lever in the up position, and mounted on the timber post just above it an analog round wall clock with a blank paper face and hands pointing to twenty-three minutes to four. No people.`

#### 15. Plate `S05-03` (Beat `c05_03` · `NARRATOR: Algenib` — Rule 5)
- **Beat Text:** และกฎข้อที่ห้า... หลังเวลาตีสี่ หากเครื่องปั่นไฟดีเซลข้างเมรุเก่าเกิดกระตุกหรือไฟตก และได้ยินเสียงประตูเหล็กของเตาเผาศพบนเมรุเปิดออกเอง ให้เดินไปตรวจดูเฉพาะปลั๊กสายไฟในเพิงเครื่องปั่นไฟเท่านั้น ห้ามเดินขึ้นบันไดเมรุ และห้ามขานรับเสียงเรียกชื่อที่ดังมาจากหน้าเตาเผาจนกว่าจะหกโมงเช้า
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `crematorium_furnace_door` (`poly: [[22,22],[58,22],[58,82],[22,82]]`) — background slow push `bz = 1.0 + 0.05*u`; the iron chain and furnace door at the top of the crematorium stairs tremble slightly in the mist (`dx = 1.6*math.sin(t*4.5)`), heavy drifting fog `fog(t, 35, 0.16)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Low-angle medium shot looking up the narrow concrete stairs of the old whitewashed brick Thai temple crematorium at night in thick grey fog: at the top of the steps sits the heavy black iron furnace door padlocked shut with an iron chain, the tall soot-stained chimney rising into the moonless dark sky above. No people.`

---

### Block `c06` — 01:15 AM: The Incense Smoke Gets Sucked Into the Coffin

#### 16. Plate `S06-01` (Beat `c06_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มปิดสมุดปกแดงลงด้วยความรู้สึกเย็นวาบไปทั้งแผ่นหลัง เสียงเครื่องปั่นไฟดีเซลจากท้ายวัดดังครางทุ้มๆ เป็นจังหวะสม่ำเสมอ จนกระทั่งเข็มนาฬิกาบนเสาไม้เดินมาถึงเวลาตีหนึ่งสิบห้านาที ไอหมอกเย็นเฉียบจากป่าไผ่ด้านนอกเริ่มลอยเลียดผ่านธรณีประตูไม้เข้ามาในโถงศาลา จนเข้มหายใจออกมาเป็นไอสีขาวจางๆ
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_shivering_desk` (`poly: [[30,20],[74,20],[74,94],[30,94]]`) — background slow push `bz = 1.0 + 0.04*u`; Khem cutout shivers and breathes with visible cold vapor (`sc = bz*(1 + 0.007*math.sin(t*2.4))`, `dx = -12*u`), low creeping floor fog `fog(t, 28, 0.14)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up of Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). sitting behind the wooden watch desk with the closed red notebook under his hands, shivering slightly as faint white cold breath mist rises from his lips and thick grey fog creeps across the wooden threshold behind him.`

#### 17. Plate `S06-02` (Beat `c06_02` · `NARRATOR: Algenib`)
- **Beat Text:** เมื่อเข้มเงยหน้ามองไปทางแท่นตั้งโลงเย็นสแตนเลสกลางศาลา เขาก็ต้องขมวดคิ้วด้วยความประหลาดใจ เพราะเส้นควันสีเทาจากธูปดอกใหญ่ในกระถางทองเหลืองไม่ได้ลอยตรงขึ้นสู่ขื่อหลังคาเหมือนปกติ... แต่ควันธูปกลับเลื้อยโค้งเป็นเส้นตรง มุดลอดเข้าไปในร่องฝาโลงเย็นที่มีสายสิญจน์พันอยู่ราวกับมีคนกำลังสูดดมควันธูปจากข้างในโลง!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `horizontal_smoke_stream` (`poly: [[38,34],[72,34],[72,68],[38,68]]`) — background push `bz = 1.0 + 0.05*u`; the grey paper smoke ribbon cutout stretches and creeps horizontally from the incense tip into the coffin lid seam (`dx = 16*u`, `ang = -1.5*math.sin(t*2.0)`, `sc = bz*(1 + 0.02*u)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Side-angle medium close-up of the brass incense urn and the front of the stainless-steel cooling coffin: instead of rising straight up, the thick ribbon of grey paper smoke from the burning vigil incense stick bends horizontally in a tight stream and flows directly into the narrow dark seam beneath the sacred-thread-bound coffin lid. No people.`

#### 18. Plate `S06-03` (Beat `c06_03` · `KHEM: Puck`)
- **Beat Text:** ลมในศาลาก็นิ่งสนิท... แล้วทำไมควันธูปถึงถูกดูดเข้าไปในร่องฝาโลงแบบนั้นได้ล่ะ แถมก้านธูปดอกแรกเพิ่งปักไปไม่ถึงสองชั่วโมง ทำไมไฟถึงลามลงมาจวนจะถึงขีดสีแดงเร็วผิดปกติขนาดนี้
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `khem_inspecting_urn` (`poly: [[24,18],[70,18],[70,94],[24,94]]`) — background push `bz = 1.0 + 0.05*u`; Khem cutout leans forward slightly inspecting the nearly burned-down incense stick (`dx = 14*u`, `dy = 4*u`, `sc = bz*(1 + 0.006*math.sin(t*2.2))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up in front of the altar dais: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). stands beside the low teak incense table with a tense furrowed brow, looking down at the vigil incense stick which has burned almost all the way down to its red ring mark.`

---

### Block `c07` — 01:45 AM: Lighting the Second Incense Stick & The Draped Portrait Frame

#### 19. Plate `S07-01` (Beat `c07_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มรีบคว้าธูปดอกใหญ่ดอกใหม่จากบนโต๊ะเวร เดินก้าวฉับๆ ผ่านแถวเก้าอี้พลาสติกสีแดงเข้าไปหยุดหน้าแท่นตั้งศพตามกฎข้อที่หนึ่ง เขายื่นปลายธูปดอกใหม่ไปจ่อชิดหัวไฟสีส้มของธูปดอกเดิมที่เหลือความยาวไม่ถึงครึ่งนิ้ว จนไฟติดแดงวาบขึ้นมาแล้วปักลงกลางกระถางทองเหลืองได้ทันเวลาพอดี
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `khem_hand_new_incense` (`poly: [[28,22],[74,22],[74,84],[28,84]]`) — background push `bz = 1.0 + 0.05*u`; Khem's hand holding the new incense stick lowers to touch the glowing orange ember (`dy = 12*smooth(u/1.2)`, `dx = -8*smooth(u/1.2)`) with a bright orange ember flare at contact.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme close-up at the brass incense urn in front of the cooling coffin: Khem's hand presses the tip of a fresh tall vigil incense stick directly against the dying glowing orange ember of the short stub just above the red ring mark, igniting a bright orange spark and fresh grey smoke.`

#### 20. Plate `S07-02` (Beat `c07_02` · `NARRATOR: Algenib`)
- **Beat Text:** แต่ในเสี้ยววินาทีที่เข้มกำลังจะชักมือกลับ ลมเย็นยะเยือกวูบหนึ่งก็พัดกรรโชกมาจากหลังแท่นตั้งโลงเย็น จนชายผ้าดิบสีขาวที่คลุมขาตั้งกรอบรูปหน้าศพทางด้านซ้ายสะบัดเปิดขึ้นครึ่งหนึ่ง... เผยให้เห็นขอบกระจกกรอบรูปที่เปียกชื้นและมีปลายนิ้วมือซีดขาวเหมือนคนจมน้ำ ทาบดันกระจกออกมาจากด้านในรูปถ่าย!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `lifted_cloth_pale_fingers` (`poly: [[24,22],[68,22],[68,86],[24,86]]`) — background push `bz = 1.0 + 0.06*u`; the white cloth hem lifts upward and sways (`dy = -16*smooth(u/1.1)`, `ang = 3.2*smooth(u/1.1) + 1.0*math.sin(t*4.0)`) revealing the lower corner of the wet glass frame with four pale waterlogged fingertips pressed against the inside of the glass.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Tight close-up on the lower half of the wooden portrait easel to the left of the cooling coffin: the bottom hem of the white cotton covering cloth is blown upward at an angle, exposing the lower corner of the dark wet glass portrait frame where four pale waterlogged fingertips press outward from inside the photograph behind the glass. Upper face of the portrait remains hidden under the white cloth.`

#### 21. Plate `S07-03` (Beat `c07_03` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มสะดุ้งเฮือก นึกถึงกฎข้อที่สองได้ทันในเสี้ยววินาทีสุดท้ายว่าระวังอย่ามองใบหน้าในรูปถ่ายเด็ดขาด เขารีบกดสายตาลงมองพื้นไม้กระดานแล้วก้าวถอยหลังกลับไปที่โต๊ะเวรหน้าศาลาอย่างรวดเร็ว โดยปล่อยให้ชายผ้าดิบสีขาวค่อยๆ ตกลงมาปิดคลุมกรอบรูปตามเดิมเองท่ามกลางความเงียบกริบ
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `khem_backing_away` (`poly: [[36,18],[78,18],[78,94],[36,94]]`) — background pull-back `bz = 1.05 - 0.04*u`; Khem cutout lowers his head (`ang = -2.0*smooth(u/1.0)`, `dy = 8*smooth(u/1.0)`) and backs away down the aisle (`dx = 22*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot in front of the altar dais: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). keeps his chin pressed down and eyes fixed firmly on the dark teak floorboards as he steps backward away from the white-draped portrait easel and the cooling coffin.`

---

### Block `c08` — 02:00 AM: The Woman in Black Lace at the Pavilion Steps (Rule 3)

#### 22. Plate `S08-01` (Beat `c08_01` · `NARRATOR: Algenib`)
- **Beat Text:** เวลาตีสองตรง เสียงกบเขียดในป่าไผ่รอบศาลาสี่จู่ๆ ก็เงียบเสียงลงพร้อมกัน แทนที่ด้วยเสียงฝีเท้าเปียกน้ำเดินย่ำแอ่งโคลนบนทางเดินลูกรังหน้าศาลา... เฉอะ... แฉะ... ก่อนที่ร่างของหญิงวัยกลางคนอายุราวห้าสิบสองปีในชุดเสื้อลูกไม้สีดำเก่าเปียกชุ่ม ในมือถือดอกบัวขาวที่เหี่ยวช้ำหนึ่งดอก จะเดินมาหยุดยืนนิ่งอยู่ที่เชิงบันไดไม้หน้าศาลา
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `pa_bua_at_steps` (`poly: [[42,22],[72,22],[72,92],[42,92]]`) — background push `bz = 1.0 + 0.05*u`; Pa Bua cutout creeps slowly out of the fog to the bottom wooden step (`dx = -24*(1 - u)`, `sc = bz*(1 + 0.005*math.sin(t*1.8))`), dense fog `fog(t, 30, 0.16)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium-wide shot looking down the five wooden veranda steps of Pavilion 4 into the foggy courtyard at 02:00 AM: Pa Bua, a pale 52-year-old Thai woman with hollow dark-ringed eyes, wet hair pulled back in a tight low bun, wearing an old rain-damp black lace mourning blouse and dark skirt, holding a wilted white lotus stem (she appears at most once in the picture). stands motionless at the bottom of the wooden steps looking up toward the watch desk.`

#### 23. Plate `S08-02` (Beat `c08_02` · `PA_BUA: Kore`)
- **Beat Text:** พ่อหนุ่มคนเฝ้าศาลาจ๊ะ... ป้าชื่อป้าบัว เพิ่งเดินทางมาถึงวัดเมื่อกี้นี้เอง... ขอรบกวนหยิบธูปบนโต๊ะให้ป้าสักดอกได้ไหมจ๊ะ ป้าอยากเข้าไปจุดธูปดูหน้าคนที่นอนอยู่ในโลงข้างในสักหน่อย
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `pa_bua_closeup_hand` (`poly: [[28,16],[74,16],[74,95],[28,95]]`) — background slow push `bz = 1.0 + 0.06*u`; Pa Bua cutout raises her pale hand slightly holding the wilted white lotus (`dy = -8*smooth(u/1.5)`, `ang = 1.1*math.sin(t*1.6)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up at the wooden steps of Pavilion 4: Pa Bua, a pale 52-year-old Thai woman with hollow dark-ringed eyes, wet hair pulled back in a tight low bun, wearing an old rain-damp black lace mourning blouse and dark skirt, holding a wilted white lotus stem (she appears at most once in the picture). extends one pale wet hand slightly forward asking for an incense stick, her hollow unblinking eyes staring straight ahead under the dim veranda light.`

#### 24. Plate `S08-03` (Beat `c08_03` · `NARRATOR: Algenib`)
- **Beat Text:** มือของเข้มที่วางอยู่ข้างมัดธูปบนโต๊ะเวรแข็งค้างทันที เพราะเมื่อเขาก้มมองผ่านธรณีประตูลงไปที่พื้นไม้หน้าบันไดศาลาภายใต้แสงไฟนีออน เขากลับไม่เห็นเงาของหญิงชุดดำคนนั้นทอดลงบนพื้นไม้เลยแม้แต่นิดเดียว มีเพียงน้ำสีดำขุ่นกลิ่นโคลนก้นอ่างเก็บน้ำที่หยดติ๋งๆ จากชายกระโปรงของหล่อนลงบนขั้นบันไดไม้!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `skirt_hem_mud_drip` (`poly: [[32,26],[70,26],[70,92],[32,92]]`) — background push `bz = 1.0 + 0.05*u`; the wet black skirt hem and bare feet cutout sways subtly (`dx = 2.0*math.sin(t*2.1)`) as dark pond mud drips onto the shadowless wooden step (`dy = 4*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Low-angle close-up on the bottom wooden veranda step of Pavilion 4 under the overhead lamp: the hem of Pa Bua's soaked black skirt and her pale wet bare feet stand on the teak plank with zero cast shadow on the wood around her, while dark murky pond water drips from the fabric onto the step.`

---

### Block `c09` — Ringing the Brass Hand-Bell & The Invisible Mourners on the Red Chairs

#### 25. Plate `S09-01` (Beat `c09_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มกัดกรามแน่นจนมือสั่น เขาจำกฎข้อที่สามในสมุดปกแดงได้อย่างแม่นยำว่า หลังตีหนึ่งห้ามยื่นธูปให้คนในชุดดำและห้ามเอ่ยปากเชิญเข้าศาลาเด็ดขาด เข้มจึงไม่ปริปากตอบแม้แต่คำเดียว แต่ใช้มือขวาหยิบกระดิ่งทองเหลืองด้ามไม้บนโต๊ะเวรขึ้นมาสั่นหนึ่งครั้ง... กริ๊ง! แล้วรีบก้มหน้าจ้องตัวหนังสือในสมุดปกแดงนิ่ง
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_ringing_bell` (`poly: [[26,18],[76,18],[76,94],[26,94]]`) — background push `bz = 1.0 + 0.04*u`; Khem's hand holding the brass hand-bell shakes in a sharp ringing motion (`ang = 6.5*math.sin(t*16)*math.exp(-t*1.2)`, `dx = 2.5*math.sin(t*16)*math.exp(-t*1.2)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up at the wooden watch desk: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). keeps his eyes locked downward on the open red hardbound notebook while his right hand lifts and rings the small brass hand-bell above the desk.`

#### 26. Plate `S09-02` (Beat `c09_02` · `PA_BUA: Kore`)
- **Beat Text:** สัปเหร่ออินคงสอนกฎเอ็งไว้ดีสินะ... ไม่ยอมยื่นธูปให้ป้าก็ไม่เป็นไร... เดี๋ยวพอถึงเวลาตีสามครึ่ง ป้าค่อยลุกออกมาหยิบเองจากข้างในก็ได้...
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `pa_bua_head_tilt_retreat` (`poly: [[34,18],[70,18],[70,92],[34,92]]`) — background slow pull-back `bz = 1.04 - 0.03*u`; Pa Bua cutout tilts slightly and glides backward into the grey fog (`ang = -3.0*smooth(u/1.4)`, `dx = 22*u`, `sc = bz*(1 - 0.03*u)`), fog `fog(t, 42, 0.18)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot at the bottom of the Pavilion 4 wooden steps: Pa Bua, a pale 52-year-old Thai woman with hollow dark-ringed eyes, wet hair pulled back in a tight low bun, wearing an old rain-damp black lace mourning blouse and dark skirt, holding a wilted white lotus stem (she appears at most once in the picture). tilts her head at an unnatural angle with a cold blank stare as she steps backward into the swirling grey temple mist.`

#### 27. Plate `S09-03` (Beat `c09_03` · `NARRATOR: Algenib`)
- **Beat Text:** เสียงฝีเท้าเปียกน้ำของหญิงชุดดำค่อยๆ ถอยห่างลงบันไดหายลับเข้าไปในสายหมอก แต่เมื่อเข้มค่อยๆ เหลือบตามองเข้าไปในโถงเก้าอี้พลาสติกสีแดงกลางศาลา เขากลับได้ยินเสียงพลาสติกลั่นเอี๊ยดเบาๆ และเห็นเก้าอี้สีแดงสามตัวในแถวหลังสุดหน้าโลงเย็น ยุบตัวแอ่นลงเหมือนมีคนสามคนกำลังนั่งเรียงกันอยู่ พร้อมรอยเท้าเปียกโคลนสามคู่ที่วางนิ่งอยู่หน้าขาเก้าอี้!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `three_red_chairs_depressed` (`poly: [[24,30],[78,30],[78,88],[24,88]]`) — background push `bz = 1.0 + 0.05*u`; the three red plastic chairs in the row cutout settle downward under invisible weight (`dy = 8*smooth(u/1.5)`, `sc = bz*(1 - 0.008*smooth(u/1.5))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot of the back row of crimson-red plastic chairs inside Pavilion 4 facing the altar: three adjacent red plastic seat cushions are noticeably bowed and pressed downward as if three heavy invisible people are sitting in them, with three pairs of wet dark muddy bare footprints on the teak floorboards directly in front of the chair legs. No people.`

---

### Block `c10` — 02:45 AM: The Disconnected Rotary Phone & Dark Drops Behind the Coffin

#### 28. Plate `S10-01` (Beat `c10_01` · `NARRATOR: Algenib`)
- **Beat Text:** หัวใจของเข้มเต้นรัวแรงจนแทบทะลุออกมานอกอก เขาไม่กล้าลุกเดินผ่านเก้าอี้แถวหลังสุดที่มีรอยเท้าเปียกโคลนนั้นอีก จนกระทั่งเวลาตีสองสี่สิบห้านาที โทรศัพท์สายตรงรุ่นเก่าสีดำบนโต๊ะเวร ซึ่งต่อสายเชื่อมไว้กับกุฏิสัปเหร่อหน้าวัดเพียงจุดเดียว จู่ๆ ก็ส่งเสียงกริ่งเหล็กดังขึ้นหนึ่งครั้ง... กริ๊ง! แล้วเงียบกริบไป
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `black_rotary_phone` (`poly: [[28,28],[72,28],[72,84],[28,84]]`) — background tight push `bz = 1.0 + 0.06*u`; the black rotary handset cutout vibrates sharply on its metal cradle (`dx = 3.2*math.sin(t*36)*math.exp(-t*0.9)`, `ang = 1.5*math.sin(t*36)*math.exp(-t*0.9)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme close-up on the weathered wooden watch desk: the old black rotary intercom telephone sits beside the red hardbound notebook and aluminum flashlight, its black receiver trembling slightly on the metal cradle under cold blue-grey fluorescent light. No people.`

#### 29. Plate `S10-02` (Beat `c10_02` · `KHEM: Puck`)
- **Beat Text:** เป็นไปไม่ได้... สายโทรศัพท์ภายในพ่วงอยู่กับตู้ไฟหลักที่โดนฟ้าผ่าตัดไฟไปตั้งแต่หัวค่ำแล้ว ไม่น่าจะมีกระแสไฟวิ่งมาสั่นกริ่งโทรศัพท์เครื่องนี้ได้เลย...
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_recoiling_phone` (`poly: [[28,16],[78,16],[78,94],[28,94]]`) — background push `bz = 1.0 + 0.04*u`; Khem cutout pulls back slightly in his chair gripping the flashlight (`dx = 12*u`, `sc = bz*(1 + 0.007*math.sin(t*2.8))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up of Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). pulling his hands back from the black rotary telephone on the watch desk, gripping his metal flashlight tightly with cold sweat on his temple.`

#### 30. Plate `S10-03` (Beat `c10_03` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มชักมือถอยห่างจากโทรศัพท์สีดำเครื่องนั้นโดยไม่ยอมยกหูขึ้นมาฟัง แต่ในความเงียบสงัดของศาลาสี่ เสียงน้ำหยดกระทบพื้นไม้กระดาน... ติ๋ง... ติ๋ง... ก็เริ่มดังรัวขึ้นมาจากช่องทางเดินแคบๆ ด้านหลังแท่นตั้งโลงเย็นสแตนเลส พร้อมกับกลิ่นคาวตะไคร่น้ำเน่าเหม็นที่โชยตลบอบอวลไปทั่วทั้งศาลา
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `dark_puddle_under_dais` (`poly: [[26,48],[74,48],[74,92],[26,92]]`) — background push `bz = 1.0 + 0.05*u`; dark puddle creeping out from beneath the rear corner of the wooden coffin dais expands slowly (`sc = bz*(1 + 0.028*smooth(u/2.0))`, `dx = -10*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Low-angle close-up on the dark teak floorboards at the right rear corner of the wooden altar dais: a trickle of thick dark murky water seeps out from the shadow behind the stainless-steel cooling coffin, pooling near the base of the wilted funeral wreath stands. No people.`

---

### Block `c11` — 03:15 AM: Behind the Cooling Coffin & The Sliding Iron Window Bolt

#### 31. Plate `S11-01` (Beat `c11_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มตัดสินใจคว้าไฟฉายกระบอกอะลูมิเนียม เดินอ้อมเลียบผนังไม้ด้านขวาเข้าไปส่องดูในซอกแคบหลังแท่นตั้งโลงเย็น และภาพที่เห็นในลำแสงไฟฉายก็ทำให้เขาเย็นสันหลังวาบ เพราะท่อทองแดงระบายความเย็นท้ายโลงที่มีเกล็ดน้ำแข็งเกาะอยู่ กำลังละลายกลายเป็นหยดน้ำสีดำข้นไหลนองลงบนพื้นไม้ใกล้ขันน้ำมนต์ทองเหลือง พร้อมแถบไฟเตือนสีแดงบนกล่องควบคุมท้ายโลงที่กระพริบถี่รัว
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-05_coffin_back_storage.png`
- **Cutout Object & Python Motion:** `compressor_grille_and_box` (`poly: [[14,20],[56,20],[56,88],[14,88]]`) — background push `bz = 1.0 + 0.05*u`; the rear compressor box and dripping copper pipes vibrate (`dx = 2.0*math.sin(t*32)`, `dy = 1.5*math.sin(t*24)`) while the red indicator strip pulses rapidly (`0.6 + 0.4*abs(math.sin(t*20))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium close-up in the narrow passage behind the altar dais lit by a flashlight beam: on the left, the rear stainless-steel compressor grille of the cooling coffin shows melting white frost on the copper pipes dripping dark murky water onto the teak floor beside the brass lustral water bowl, while the blank red indicator bar on the control box glows crimson. No people.`

#### 32. Plate `S11-02` (Beat `c11_02` · `NARRATOR: Algenib`)
- **Beat Text:** ยิ่งไปกว่านั้น ที่บานหน้าต่างไม้เกล็ดด้านหลังแท่นตั้งศพซึ่งลงกลอนเหล็กเก่าไว้ กลอนเหล็กขึ้นสนิมนั้นกำลังสั่นคลอนและค่อยๆ เลื่อนถอยออกจากสลักทีละมิลลิเมตรตามแรงสั่นของโลงเย็น โดยมีเงาร่างสีดำสูงโย่งของคนหลายร่างยืนเรียงรายอยู่ในดงไผ่ด้านนอก จ้องลอดซี่เกล็ดไม้เข้ามาในความมืด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-05_coffin_back_storage.png`
- **Cutout Object & Python Motion:** `iron_bolt_sliding` (`poly: [[38,24],[84,24],[84,82],[38,82]]`) — background push `bz = 1.0 + 0.06*u`; the rusted iron slide-bolt cutout rattles and slides slowly left out of its keeper (`dx = -16*smooth(u/2.0)`, `dy = 0.8*math.sin(t*28)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Tight close-up on the rear wooden louvered shutter window behind the altar dais: the heavy rusted iron slide-bolt is halfway slid back out of its metal latch, and through the narrow horizontal gaps between the wooden slats outside in the bamboo fog stand the dark silhouettes of three tall figures peering inward.`

---

### Block `c12` — 03:37 AM: Three Heavy Knocks Inside the Cooling Coffin (Rule 4)

#### 33. Plate `S12-01` (Beat `c12_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มรีบเอื้อมมือไปดันกลอนเหล็กหน้าต่างหลังแท่นตั้งศพกลับเข้าที่ล็อกสุดแรง แต่ในจังหวะที่เขาก้าวถอยออกมาหน้าโถงศาลา เข็มนาฬิกากลมบนเสาไม้หน้าศาลาก็ตีบอกเวลาตีสามสิบเจ็ดนาทีตรง... ทันใดนั้น เสียงทุบแผ่นเหล็กจากด้านในโลงเย็นสแตนเลสก็ดังก้องสะท้อนไปทั่วทั้งศาลาสามครั้งติดกัน... ปัง! ปัง! ปัง!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `shaking_cooling_coffin` (`poly: [[20,26],[80,26],[80,82],[20,82]]`) — background push `bz = 1.0 + 0.05*u`; the entire stainless-steel cooling coffin cutout jolts violently three times from internal impacts (`dx = 4.5*math.sin(t*34)*(int(t*2)%2==0)`, `dy = -3.5*abs(math.sin(t*28))`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot of the elevated altar dais in Pavilion 4 under flickering cold blue-grey fluorescent light: the silver-grey stainless-steel cooling coffin bound with white sacred cotton thread and red wax seals shudders on its wooden platform while the burning vigil incense stick in the brass urn trembles in the foreground. No people.`

#### 34. Plate `S12-02` (Beat `c12_02` · `NARRATOR: Algenib`)
- **Beat Text:** แรงกระแทกจากภายในทำให้โลงเย็นสแตนเลสทั้งใบสั่นสะเทือนอย่างรุนแรง เชือกสายสิญจน์สีขาวที่พันคาดรอบรอยต่อฝาโลงถูกดันจนตึงเปรี๊ยะและเริ่มปริขาดทีละเส้น ส่วนตราขี้ผึ้งสีแดงทั้งสามจุดแตกร้าวออก พร้อมกับฝาโลงสแตนเลสที่ค่อยๆ แง้มยกตัวสูงขึ้นเป็นช่องมืดยาวประมาณครึ่งนิ้ว!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `cracked_seal_coffin_lid` (`poly: [[22,22],[78,22],[78,78],[22,78]]`) — background tight push `bz = 1.0 + 0.06*u`; the upper coffin lid and frayed white sacred thread cutout lifts slowly upward (`dy = -12*smooth(u/1.8)`, `ang = 0.8*smooth(u/1.8)`, `dx = 1.8*math.sin(t*25)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme close-up on the horizontal lid seam of the stainless-steel cooling coffin: the dark-red wax seal is cracked in two, the taut white sacred cotton thread is fraying strand by strand, and the heavy silver-grey metal lid is pried upward by half an inch revealing a pitch-black gap underneath. No people.`

#### 35. Plate `S12-03` (Beat `c12_03` · `PA_BUA: Kore`)
- **Beat Text:** พ่อหนุ่ม... ข้างในนี้มันมืดและอึดอัดเหลือเกิน... ช่วยแกะเชือกสายสิญจน์บนฝาโลงเปิดให้ป้าออกไปสูดควันธูปข้างนอกหน่อยเถอะจ๊ะ...
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `fingers_under_coffin_lid` (`poly: [[28,28],[72,28],[72,78],[28,78]]`) — background slow push `bz = 1.0 + 0.06*u`; pale waterlogged fingers cutout slides slowly outward through the half-inch gap under the lifted steel lid (`dx = -14*smooth(u/1.8)`, `dy = 1.5*math.sin(t*12)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme close-up on the half-inch dark gap beneath the lifted stainless-steel coffin lid bound with frayed white sacred thread: four pale grey waterlogged fingers with cracked nails curl outward from the darkness inside the coffin and hook onto the lower metal rim while wisps of white freezing vapor leak out.`

---

### Block `c13` — The 03:37 AM Python Jump Scare (`S13-CALM` -> `S13-REVEAL`)

#### 36. Plate `S13-CALM` (Beat `c13_01` · `NARRATOR: Algenib` — Pre-Scare Calm Lead-In)
- **Beat Text:** เสียงกระซิบแหบพร่าที่ลอดออกมาจากร่องฝาโลงเย็น คือเสียงเดียวกับป้าบัวหญิงชุดดำที่มาขอธูปเมื่อตอนตีสองไม่มีผิดเพี้ยน! เข้มกลั้นหายใจแน่น ก้าวถอยหลังตามกฎข้อที่สี่โดยไม่แตะต้องสายสิญจน์แม้แต่ปลายนิ้ว มือที่สั่นเทาส่องไฟฉายต่ำลงไปที่แผ่นสแตนเลสขัดเงาข้างโลง ซึ่งสะท้อนภาพขาตั้งกรอบรูปหน้าศพในความเงียบสงัดก่อนพายุความตายจะปะทุขึ้น
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion (`/opt/MoonieXHQ/Work/tool4-demo/scare/render.py` Calm Phase):** `flashlight_coffin_reflection` (`poly: [[24,20],[76,20],[76,88],[24,88]]`) — during `c13_01` and the `3.0s` pre-sting calm hold (ambience bed dipped to `35%`), Python executes `zoom(calm, W/2, H*0.45, 1.0 + 0.08*u, math.sin(t*7)*1.5, math.sin(t*5.3)*1.2)` with high-frequency beam hum `0.93 + 0.07*math.sin(t*50)*(u > 0.7)` and a `0.25s` voltage drop `f *= 0.55` right before the sting frame.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Close-up over Khem's trembling hand holding the aluminum flashlight aimed low at the polished dark stainless-steel side panel of the cooling coffin: in the dim metallic reflection, the wooden portrait easel covered with the white cloth stands eerily still behind him under the cold blue-grey fluorescent light.`

#### 37. Plate `S13-REVEAL` (Beat `c13_02` · `NARRATOR: Algenib` — **THE ONE JUMP SCARE BEAT**)
- **Beat Text:** และในเสี้ยววินาทีนั้นเอง ผ้าดิบสีขาวที่คลุมกรอบรูปหน้าศพก็ร่วงหลุดลงสู่พื้น พร้อมกับร่างของศพหญิงวัยกลางคนใบหน้าบวมเป่งคล้ำดำด้วยโคลนก้นเขื่อน คอหักพับเอียงผิดรูป ดวงตาข้างหนึ่งเหลือกขาวขุ่นไร้แววและอ้าปากกว้างจนกรามค้าง พุ่งกระแทกฝาโลงเย็นชะโงกหน้าทะลุร่องสายสิญจน์ออกมาประชิดหน้าของเข้มในระยะเผาขน!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion (`/opt/MoonieXHQ/Work/tool4-demo/scare/render.py` Reveal Phase — ZERO Google Flow):** `drowned_corpse_lunge` (`FACE = (W * 0.52, H * 0.36)`, `poly: [[16,10],[86,10],[86,95],[16,95]]`) — hard cut on `scare_sting_07_fs415510.wav` (`0.0s` attack):
  - Cubic punch-in from the face: `k = min(s / 0.18, 1); e = 1 - (1 - k)**3; sc = 1.55 - 0.55*e + 0.06*min(s / 6, 1)`
  - Decaying camera shake: `sh = 26 * math.exp(-s * 4.5)`
  - Horizontal blur + RGB split (`s < 0.5`): `cv2.blur(f, (int(1 + 30*(1 - e)), 1))`, `off = int(18*(1 - s/0.5))`, `np.roll` R/B channels by `±off`
  - Flash + tube flicker: 2 frames white flash (`s < 2/24`), 3 frames crimson flash (`s < 5/24`), broken tube flicker (`s > 0.6`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Extreme terrifying close-up horror reveal: the stainless-steel coffin lid is forced wide open against the taut white sacred cotton threads, and lunging straight out toward the camera at point-blank range is the bloated mud-darkened corpse of the 52-year-old woman in the wet black lace blouse, her neck bent sharply at a wrong angle, one huge unblinking milky-white eye staring dead ahead while the other socket lies in deep shadow, and her jaw gaping unnaturally wide as the white cloth falls from the portrait frame behind her. No blood, no gore.`

---

### Block `c14` — Throwing the Red Auxiliary Breaker Lever

#### 38. Plate `S14-01` (Beat `c14_01` · `KHEM: Puck`)
- **Beat Text:** อย่ามองกรอบรูป... อย่าแตะสายสิญจน์! ต้องรีบไปสับเบรกเกอร์ไฟสำรองสีแดงที่เสาหน้าศาลาเดี๋ยวนี้!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_sprinting_aisle` (`poly: [[30,16],[74,16],[74,94],[30,94]]`) — background rapid pull-back `bz = 1.08 - 0.06*u`; Khem cutout lunges forward down the central aisle away from the altar (`dx = -28*u`, `dy = -3.5*abs(math.sin(t*6.0))`, `ang = -2.2*math.sin(t*6.0)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Dynamic medium shot in the central teak aisle of Pavilion 4 between the rows of red plastic chairs: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). stumbles and sprints forward toward the front entrance pillar in terror, keeping his face turned sharply away from the altar behind him.`

#### 39. Plate `S14-02` (Beat `c14_02` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มผงะถอยหลังเกือบล้มทั้งยืน เขาเบือนหน้าหนีจากกรอบรูปหน้าศพและร่องฝาโลงทันที แล้วออกวิ่งสุดชีวิตฝ่าทางเดินไม้กลางศาลา ตรงไปยังตู้เหล็กควบคุมไฟฟ้าที่เสาไม้ด้านขวาหน้าประตูศาลา ก่อนจะใช้สองมือกระชากคันโยกเบรกเกอร์ไฟสำรองสีแดงสับลงจนสุดแรงเกิด!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_pulling_red_breaker` (`poly: [[24,18],[78,18],[78,92],[24,92]]`) — background push `bz = 1.0 + 0.05*u`; Khem's hands and the red breaker lever cutout slam downward (`dy = 18*smooth(u/0.9)`, `ang = -3.5*smooth(u/0.9)`) with a sharp electrical spark flash on the metal box.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Tight close-up at the grey metal electrical breaker box on the right front wooden pillar of Pavilion 4: Khem's both hands grip the bright-red auxiliary breaker lever and yank it forcefully downward into the emergency engage position.`

#### 40. Plate `S14-03` (Beat `c14_03` · `NARRATOR: Algenib`)
- **Beat Text:** ทันทีที่คันโยกสีแดงถูกสับลง เสียงมอเตอร์คอมเพรสเซอร์ทำความเย็นกำลังสูงก็คำรามกระหึ่มขึ้นทั่วศาลา ไอเย็นจัดติดลบพุ่งผ่านท่อทองแดงจนเกิดเกล็ดน้ำแข็งสีขาวหนาเตอะเกาะผนึกรอยแง้มของฝาโลงเย็นและเชือกสายสิญจน์ให้แข็งตัวติดตายในพริบตา เสียงขูดเล็บและเสียงกรีดร้องจากด้านในโลงค่อยๆ จมหายไปใต้ชั้นน้ำแข็งโดยที่เข้มยืนหอบหายใจตัวสั่นเทาอยู่ข้างเสาหน้าศาลา
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `frost_sealed_coffin_seam` (`poly: [[20,24],[80,24],[80,82],[20,82]]`) — background push `bz = 1.0 + 0.05*u`; thick white rime frost and freezing vapor plume cutout expands across the clamped steel lid seam (`sc = bz*(1 + 0.025*smooth(u/2.0))`, `dx = 2.0*math.sin(t*18)*math.exp(-t*0.7)`), dense cold mist `fog(t, 24, 0.16)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Close-up on the stainless-steel cooling coffin on the altar dais: thick crystalline white ice and rime frost encase the entire horizontal lid seam and freeze over the frayed white sacred cotton thread, locking the metal lid shut as clouds of freezing white vapor spill down the sides of the coffin. No people.`

---

### Block `c15` — 04:15 AM: The Diesel Generator Sputters & The Clang From the Crematorium

#### 41. Plate `S15-01` (Beat `c15_01` · `NARRATOR: Algenib`)
- **Beat Text:** แต่ค่ำคืนอันเลวร้ายในวัดป่าห้วยหมอกยังไม่สิ้นสุดลงง่ายๆ เมื่อเวลาล่วงเข้าสู่ตีสี่สิบห้านาที เสียงเครื่องปั่นไฟดีเซลที่ตั้งอยู่ในเพิงสังกะสีข้างเมรุเก่าท้ายวัด ก็เริ่มสำลักน้ำมันดังกระตุก... ตับ... ตับ... ตับ... จนหลอดไฟนีออนบนเพดานศาลาสี่กระพริบวูบวาบสลับกับความมืดมิด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `sputtering_diesel_generator` (`poly: [[46,34],[88,34],[88,88],[46,88]]`) — background push `bz = 1.0 + 0.04*u`; generator and exhaust smoke cutout lurches erratically (`dx = 4.2*math.sin(t*19)*(int(t*4)%3==0)`, `dy = 3.0*math.cos(t*15)`) while the yellow shed bulb drops in and out (`0.35 + 0.65*(int(t*10)%4 != 0)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot inside the open-sided corrugated-tin generator shed behind the temple at 04:15 AM: the dark iron diesel generator shudders violently, puffing a dark grey paper smoke cloud from its exhaust pipe while the single yellow bulb overhead dims to a weak flicker. No people.`

#### 42. Plate `S15-02` (Beat `c15_02` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มหันไปมองกระถางธูปหน้าโลงเย็น เห็นว่าธูปดอกใหญ่ไหม้ผ่านขีดสีแดงและพ้นเวลาตีสี่ตามกฎข้อที่หนึ่งอย่างปลอดภัยแล้ว แต่ถ้าเครื่องปั่นไฟดับลงตอนนี้ น้ำแข็งที่ผนึกฝาโลงเย็นไว้จะต้องละลายออกอีกครั้ง เข้มจึงคว้ากระเป๋าสะพายเครื่องมือกับไฟฉาย ก้าวลงบันไดไม้หน้าศาลาเดินตามสายไฟสีดำเส้นใหญ่ไปทางเพิงเครื่องปั่นไฟท้ายวัด
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_descending_steps` (`poly: [[32,22],[68,22],[68,92],[32,92]]`) — background pan `bz = 1.0 + 0.04*u, dx_bg = -10*u`; Khem cutout steps down off the wooden veranda following the black rubber power cable (`dx = 26*u`, `dy = 8*u`, `ang = 1.0*math.sin(t*3.5)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium-wide exterior shot at the front steps of Pavilion 4: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). steps down the wet wooden stairs into the grey fog, shining his aluminum flashlight along the thick black power cable on the ground.`

#### 43. Plate `S15-03` (Beat `c15_03` · `NARRATOR: Algenib`)
- **Beat Text:** เมื่อเข้มเดินฝ่าหมอกหนามาถึงเพิงสังกะสีข้างเมรุเก่า เขารีบหมุนวาล์วไล่อากาศและเสียบปลั๊กสายไฟหลักที่หลวมให้แน่นจนเครื่องปั่นไฟกลับมาเดินเรียบอีกครั้ง... แต่ในจังหวะที่เขากำลังจะหันหลังกลับ เสียงโซ่เหล็กกระทบกันดังเคร้งใหญ่ก็ตามมาด้วยเสียงบานประตูเหล็กบนยอดเมรุเก่าที่เปิดอ้าออกเองท่ามกลางความมืด!
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `khem_at_generator` (`poly: [[44,24],[84,24],[84,92],[44,92]]`) — background push `bz = 1.0 + 0.05*u`; Khem cutout crouches beside the generator locking the heavy power plug and turns his head sharply toward the crematorium on the left (`ang = -2.2*smooth(u/1.2)`, `dx = -10*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot at the corrugated-tin generator shed: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). kneels beside the iron diesel generator gripping the thick black power cable plug, turning his head in alarm toward the old whitewashed crematorium staircase on the left.`

---

### Block `c16` — The Open Crematorium Furnace Door & Fake Lung In's Voice (Rule 5)

#### 44. Plate `S16-01` (Beat `c16_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มยืนตัวแข็งทื่ออยู่ใต้หลอดไฟสีเหลืองสลัวของเพิงเครื่องปั่นไฟ เมื่อมองขึ้นไปตามขั้นบันไดปูนแคบๆ ของเมรุเก่าสีขาวหม่น เขาก็เห็นว่าบานประตูเหล็กสีดำของเตาเผาศพ ซึ่งถูกล็อกด้วยโซ่และแม่กุญแจเหล็กไว้ตั้งแต่ตอนห้าทุ่ม บัดนี้กลับเปิดอ้าค้างไว้ เผยให้เห็นช่องเตาเผาดำมืดที่เต็มไปด้วยขี้เถ้า
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `open_iron_furnace_door` (`poly: [[26,22],[62,22],[62,78],[26,78]]`) — background low-angle push `bz = 1.0 + 0.06*u`; the heavy black iron furnace door and dangling chain cutout swings slowly outward to the left (`dx = -14*smooth(u/2.0)`, `ang = 1.2*smooth(u/2.0)`), thick fog `fog(t, 32, 0.16)`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Low-angle close-up looking up the narrow concrete staircase of the old whitewashed brick crematorium in swirling night fog: the heavy iron chain hangs unhooked on the side, and the black iron furnace door stands swung open revealing a pitch-black rectangular cremation chamber inside. No people.`

#### 45. Plate `S16-02` (Beat `c16_02` · `LUNG_IN: Charon` [Imitated by the Entity])
- **Beat Text:** เข้มเอ๊ย... ขึ้นมาช่วยลุงบนเมรุหน่อยสิไอ้หนุ่ม... ส่องไฟฉายขึ้นมาดูตะแกรงเหล็กในเตาเผาให้ลุงที เหมือนจะมีคนเข้าไปนอนขวางอยู่ข้างในเตา...
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `silhouette_inside_furnace` (`poly: [[32,20],[66,20],[66,82],[32,82]]`) — background slow zoom `bz = 1.0 + 0.06*u`; dark hunched silhouette just inside the open furnace doorway breathes and sways slowly (`sc = bz*(1 + 0.01*math.sin(t*1.9))`, `dx = -8*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Tight medium shot at the top landing of the old crematorium stairs in cold grey mist: just inside the gaping black doorway of the open iron cremation furnace stands a motionless dark paper silhouette shaped like an old man with head bent forward in shadow, no facial features visible, beckoning one hand slowly at the threshold.`

#### 46. Plate `S16-03` (Beat `c16_03` · `NARRATOR: Algenib`)
- **Beat Text:** เสียงแหบห้าวที่ร้องเรียกลงมาจากหน้าปากเตาเผาบนยอดเมรุ คือเสียงที่เลียนแบบลุงอินสัปเหร่อได้อย่างแนบเนียนที่สุด! แต่เข้มจำกฎข้อที่ห้าได้ขึ้นใจว่าห้ามเดินขึ้นบันไดเมรุและห้ามขานรับเสียงเรียกหน้าเตาเผาจนกว่าจะเช้า และเมื่อเขาส่องไฟฉายไปที่เชิงบันไดเมรุ เขาก็เห็นเพียงรอยเท้าเปลือยเปียกโคลนที่เดินขึ้นบันไดไปสู่หน้าเตาเผา... โดยไม่มีรอยเท้าเดินกลับลงมาเลยแม้แต่รอยเดียว
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-04_crematorium_path.png`
- **Cutout Object & Python Motion:** `flashlight_beam_on_stairs` (`poly: [[24,30],[72,30],[72,94],[24,94]]`) — background push `bz = 1.0 + 0.05*u`; flashlight cone + wet muddy bare footprints ascending the concrete steps (`dx = 2.0*math.sin(t*5.5)`, `dy = -10*u` beam sweep up the steps).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> High-contrast close-up of the lower concrete steps of the old whitewashed crematorium illuminated by Khem's flashlight beam: a single trail of wet dark muddy bare footprints points exclusively upward from the gravel ground onto the stairs toward the furnace above, with zero downward footprints. No people.`

---

### Block `c17` — 04:45 AM: Sealing the Pavilion Entrance & The Tolling Eave Bell

#### 47. Plate `S17-01` (Beat `c17_01` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มปิดปากเงียบสนิท ไม่ยอมขานรับเสียงเรียกจากบนเมรุแม้แต่คำเดียว เขารีบก้าวถอยหลังตามแนวสายไฟสีดำกลับมายังศาลาตั้งศพหมายเลขสี่ วิ่งขึ้นบันไดไม้แล้วคว้าม้วนสายสิญจน์สำรองจากหลังโต๊ะเวร มาขึงพาดขวางระหว่างเสาไม้หน้าทางเข้าศาลาทั้งสองฝั่งอย่างรวดเร็ว
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_tying_entrance_thread` (`poly: [[24,18],[76,18],[76,92],[24,92]]`) — background push `bz = 1.0 + 0.05*u`; Khem cutout pulls the white sacred cotton thread taut across the wooden entrance pillar (`dx = -16*smooth(u/1.3)`, `dy = 2*math.sin(t*4.0)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot at the top of the wooden veranda entrance of Pavilion 4: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). wraps and pulls a white sacred cotton thread horizontally across the open doorway from the left wooden pillar to the right pillar.`

#### 48. Plate `S17-02` (Beat `c17_02` · `NARRATOR: Algenib`)
- **Beat Text:** เวลาตีสี่สี่สิบห้านาที ลมหนาวพัดกรรโชกผ่านดงไผ่รอบศาลา ระฆังทองเหลืองใบใหญ่ที่แขวนอยู่ใต้ชายคาหน้าศาลาสี่เริ่มแกว่งไกวและส่งเสียงดังเหง่งหง่างขึ้นเองโดยไม่มีคนตี ขณะที่ในลานดินเปียกโคลนด้านนอกแนวสายสิญจน์ มีเงาร่างสีดำสี่ร่างยืนเรียงแถวจ้องมองเข้ามาในศาลาอย่างไม่วางตา
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `swinging_bronze_bell` (`poly: [[18,14],[48,14],[48,68],[18,68]]`) — background push `bz = 1.0 + 0.04*u`; the heavy bronze eave bell cutout swings back and forth on its beam (`ang = 7.5*math.sin(t*3.2)`, `dx = 6*math.sin(t*3.2)`) while four dark silhouettes stand in the misty background on the right.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide shot from the veranda of Pavilion 4 looking out into the dark foggy temple path at 04:45 AM: in the upper-left foreground under the timber eave, the heavy bronze temple bell swings by itself, while out on the wet mud path beyond the white sacred thread stand four tall dark faceless paper silhouettes in a row facing the pavilion.`

#### 49. Plate `S17-03` (Beat `c17_03` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มทรุดตัวลงนั่งหลังโต๊ะเวรไม้ ก้มหน้ากอดสมุดปกแดงและกำกระดิ่งทองเหลืองไว้แน่นแนบอก หลับตาสวดมนต์อยู่ในใจโดยไม่ยอมเงยหน้ามองออกไปนอกธรณีประตูอีกเลย แม้จะได้ยินเสียงฝีเท้าเปียกน้ำเดินวนเวียนอยู่บนชานระเบียงไม้หน้าศาลาห่างจากโต๊ะเวรไปเพียงไม่ถึงสองเมตรตลอดชั่วโมงสุดท้ายก่อนรุ่งสาง
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `khem_praying_behind_desk` (`poly: [[26,20],[76,20],[76,94],[26,94]]`) — background slow push `bz = 1.0 + 0.05*u`; Khem cutout clutches the red rulebook to his chest with rapid trembling breathing (`sc = bz*(1 + 0.009*math.sin(t*3.4))`, `dx = 1.5*math.sin(t*14)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Close-up behind the wooden watch desk inside Pavilion 4: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). sits crouched low with his eyes squeezed tightly shut, clutching the dark-red hardbound notebook and the brass hand-bell against his chest while dark shadows fall across the wooden veranda planks behind the white sacred thread.`

---

### Block `c18` — 06:00 AM: Golden Dawn & The Three Mud-Stained White Lotuses

#### 50. Plate `S18-01` (Beat `c18_01` · `NARRATOR: Algenib`)
- **Beat Text:** จนกระทั่งเข็มนาฬิกาเดินมาแตะเวลาหกโมงเช้าตรง แสงอาทิตย์สีทองอร่ามยามรุ่งอรุณก็สาดส่องทะลุยอดไม้ไผ่และม่านหมอกลงมาต้องหลังคาศาลาสี่ เสียงระฆังทองเหลืองใต้ชายคาที่แกว่งดังอยู่ตลอดคืนหยุดนิ่งลงในพริบตา พร้อมกับเงาร่างทั้งสี่บนลานดินหน้าศาลาที่จางหายไปกับสายหมอกยามเช้า
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `still_bell_morning_sun` (`poly: [[18,14],[48,14],[48,68],[18,68]]`) — background slow pull-back `bz = 1.05 - 0.04*u`; the bronze eave bell settles to a halt (`ang = 1.5*math.sin(t*2.5)*math.exp(-t*0.9)`) as warm golden morning light beams fade in across the empty courtyard (`fog(t, 18, 0.08)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide atmospheric exterior shot of Funeral Pavilion 4 at 06:00 AM dawn: warm golden-amber morning sunlight breaks through the bamboo grove and pale morning mist onto the wooden veranda and empty gravel path; the bronze temple bell hangs completely still under the eave and all dark figures are gone. No people.`

#### 51. Plate `S18-02` (Beat `c18_02` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มค่อยๆ ลืมตาขึ้นและถอนหายใจออกมาอย่างหมดเรี่ยวแรง เมื่อเขามองเข้าไปในโถงศาลาที่เริ่มสว่างด้วยแสงแดดอ่อนๆ เก้าอี้พลาสติกสีแดงทุกตัวกลับมาว่างเปล่า ฝาโลงเย็นสแตนเลสยังคงถูกน้ำแข็งสีขาวผนึกแน่นหนา แต่บนพื้นไม้กระดานหน้าเก้าอี้แถวหลังสุด กลับมีดอกบัวขาวที่เหี่ยวช้ำและเปื้อนโคลนก้นเขื่อนวางทิ้งไว้สามดอก
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `three_wilted_lotuses_on_floor` (`poly: [[28,50],[72,50],[72,92],[28,92]]`) — background slow push `bz = 1.0 + 0.05*u`; the three mud-stained white lotus stems on the teak floor sit in stronger foreground parallax (`dx = -18*u`, `dy = -4*u`) under warm morning sunbeams.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot inside Pavilion 4 bathed in pale golden morning daylight: in the background the stainless-steel cooling coffin sits sealed in white frost on the altar dais, while in the foreground on the dark teak floorboards directly in front of the empty back-row red plastic chairs lie three wilted white lotus stems smeared with dark pond mud. No people.`

---

### Block `c19` — 06:20 AM: Lung In Returns & The Fate of the Previous Watchman

#### 52. Plate `S19-01` (Beat `c19_01` · `NARRATOR: Algenib`)
- **Beat Text:** เวลาหกโมงยี่สิบนาที เสียงฝีเท้าหนักๆ ของคนจริงก็เดินขึ้นบันไดไม้หน้าศาลามา ลุงอินตัวจริงเดินถือถุงพวงมาลัยดาวเรืองสดและขันทองเหลืองเข้ามาในศาลา เมื่อชายชราเห็นคันโยกเบรกเกอร์ไฟสำรองสีแดงถูกสับลง และเห็นสายสิญจน์หน้าประตูศาลาที่เข้มขึงกั้นไว้ ลุงอินก็พยักหน้าช้าๆ ด้วยสีหน้าโล่งอก
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `lung_in_entering_morning` (`poly: [[32,18],[70,18],[70,94],[32,94]]`) — background push `bz = 1.0 + 0.04*u`; Lung In cutout steps inside past the white sacred thread carrying fresh marigold garlands and nods slowly (`dy = 4*math.sin(t*2.0)`, `dx = -14*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot at the front entrance of Pavilion 4 in warm morning daylight: Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). stands inside the doorway holding a brass bowl and fresh yellow marigold garlands, looking with quiet relief at the pulled-down red breaker lever on the right pillar.`

#### 53. Plate `S19-02` (Beat `c19_02` · `LUNG_IN: Charon`)
- **Beat Text:** เอ็งทำตามกฎครบทุกข้อจริงๆ สินะไอ้หนุ่ม... ศพในโลงนี้คือป้าบัวที่จมน้ำตายในอ่างเก็บน้ำท้ายเขื่อนพร้อมชุดลูกไม้สีดำเมื่อสามวันก่อน ตอนกลางคืนวิญญาณแกจะออกมายืนรอหน้าบันไดศาลาเพื่อหลอกขอธูปจากคนเฝ้าศาลา ถ้าใครเผลอยื่นธูปจากมัดบนโต๊ะให้แกเท่ากับเป็นการรับปากเชิญแกเข้ามาสลับที่ทันที
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-01_pavilion_altar.png`
- **Cutout Object & Python Motion:** `lung_in_redraping_cloth` (`poly: [[22,18],[64,18],[64,94],[22,94]]`) — background push `bz = 1.0 + 0.05*u`; Lung In cutout lifts the fallen white cotton cloth and drapes it back over the portrait easel without looking at the frame (`dy = -12*smooth(u/1.4)`, `ang = 1.2*smooth(u/1.4)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot beside the altar dais in morning daylight: Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). keeps his eyes averted downward while his hands drape the off-white cotton cloth back over the wooden portrait easel beside the frost-sealed cooling coffin.`

#### 54. Plate `S19-03` (Beat `c19_03` · `LUNG_IN: Charon`)
- **Beat Text:** เอ้านี่เงินค่าจ้างหนึ่งพันห้าร้อยบาทของเอ็ง รับไปซะ... คนเฝ้าไฟคนก่อนหน้าเอ็งเห็นว่าเป็นผู้หญิงแก่เปียกฝนมาขอธูปตอนตีสอง เลยใจดียื่นธูปให้แกไปแล้วเดินตามเสียงเรียกขึ้นไปบนเมรุ... เช้าวันรุ่งขึ้นลุงต้องไปไขกุญแจเปิดเตาเผาเอาศพเขาออกมาจากในเมรุแทน
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-02_pavilion_seating.png`
- **Cutout Object & Python Motion:** `lung_in_handing_banknotes` (`poly: [[24,18],[76,18],[76,94],[24,94]]`) — background slow push `bz = 1.0 + 0.04*u`; Lung In cutout extends his hand placing three crisp folded banknotes on the wooden watch desk toward Khem (`dx = 14*smooth(u/1.3)`, `dy = 6*smooth(u/1.3)`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium two-shot at the wooden watch desk in morning light: Lung In, a gaunt 64-year-old Thai temple undertaker with weathered tan skin, short bristle-white hair, faded dark-brown cotton button shirt with rolled sleeves, loose black trousers, a braided black sacred cord and brass talisman cylinder around his neck (he appears at most once in the picture). places three folded paper banknotes (blank paper rectangles, no numbers or text) onto the desk in front of Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture).`

---

### Block `c20` — Khem's Departure & Final Warning

#### 55. Plate `S20-01` (Beat `c20_01` · `KHEM: Puck`)
- **Beat Text:** ขอบคุณสำหรับค่าแรงครับลุงอิน... สายไฟกับเครื่องปั่นไฟข้างเมรุผมซ่อมให้เรียบร้อยหมดแล้ว ส่วนคืนที่สองกับคืนที่สาม ผมขอไม่กลับมาเฝ้าต่อนะครับลุง ผมขอลาออกตั้งแต่วันนี้เลยครับ
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_shouldering_bag` (`poly: [[30,18],[74,18],[74,94],[30,94]]`) — background push `bz = 1.0 + 0.04*u`; Khem cutout grips the strap of his black tool sling bag and bows slightly in farewell (`dy = 5*math.sin(t*1.8)`, `dx = 12*u`).
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Medium shot on the wooden veranda of Pavilion 4 in morning sunlight: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). tightening the strap of his black tool sling bag over his shoulder, speaking earnestly to Lung In before turning to descend the wooden steps.`

#### 56. Plate `S20-02` (Beat `c20_02` · `NARRATOR: Algenib`)
- **Beat Text:** เข้มรับเงินค่าจ้างหนึ่งพันห้าร้อยบาท เก็บกระเป๋าเครื่องมือขึ้นสะพายบ่าแล้วรีบเดินก้าวฉับๆ ออกจากวัดป่าห้วยหมอกตั้งแต่เช้าตรู่วันนั้นโดยไม่หันหลังกลับไปมองศาลาสี่อีกเลย... จำเรื่องนี้ไว้เป็นคำเตือนนะครับ หากคืนไหนคุณต้องไปนั่งเฝ้าศาลาตั้งศพกะดึกในวัดเก่าแก่ที่กรอบรูปหน้าศพถูกคลุมด้วยผ้าขาวและฝาโลงเย็นถูกผนึกด้วยสายสิญจน์ ไม่ว่าดึกดื่นแค่ไหนจะมีคนในชุดไว้ทุกข์สีดำเดินฝ่าสายหมอกมาขอธูปจากคุณด้วยน้ำเสียงน่าสงสารเพียงใด อย่ายื่นธูปในมือให้เขาและอย่าเปิดผ้าขาวคลุมกรอบรูปดูเป็นอันขาด เพราะคนที่มายืนขอธูปหน้าศาลาในยามวิกาล... อาจกำลังหาคนเข้าไปนอนในโลงเย็นแทนตัวเองอยู่ครับ
- **Attach:** `C:\Users\passg\ghostrules-paper\ep07_loc\LOC-03_pavilion_veranda.png`
- **Cutout Object & Python Motion:** `khem_walking_away_morning` (`poly: [[38,24],[66,24],[66,90],[38,90]]`) — background slow pull-back `bz = 1.06 - 0.05*u`; Khem cutout walks briskly away along the morning temple path without looking back (`dx = 34*u`, `dy = -2.0*abs(math.sin(t*3.8))`, `sc = bz*(1 - 0.06*u)`), soft fade to black over final `0.6s`.
- **ChatGPT Prompt:** `<STYLE_LOC_PREFIX> Wide cinematic morning shot along the forest-temple dirt path outside Funeral Pavilion 4: Khem, a lean 27-year-old Thai electrician with short cropped black hair, dark navy canvas work jacket over a faded charcoal crewneck t-shirt, dark slate work trousers, black tool sling bag across his chest (he appears at most once in the picture). walks briskly away from the wooden pavilion steps toward the sunlit bamboo gate in the distance without looking back.`
