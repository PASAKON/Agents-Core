# Trailer bible: the water world (draft 1, 2026-09-23)

Story is the CEO's (see `STORY-OPTIONS.md`, Draft 3). Everything below is a CTO
design proposal for the CEO to change. Nothing is generated until he approves it.
Rules carried from `ai-film-production`: one character per reference plate,
location plates contain no characters, this file is the single source of truth
for every look (a shot may not describe a character in words that disagree with it).

## Colour script (CEO, 2026-09-23)

> ช่วงต้นจะเป็นสีแบบ Colorful ช่วงฟ้ามืด อันตรายมาถึง จะเป็นแบบ Dark with colorful

| Act | Time | Look | Palette |
|---|---|---|---|
| Home, leaving | 0:00-0:35 | their daylight: bright blue-white sky like a brilliantly lit night, a huge close moon, stars; neon-green glowing grass on wooden houses; clear water with light rays | sky white-blue #DDF3FF, sky blue #7FB8FF, neon green #39FF14, water turquoise #2EC4B6, moon silver #E8ECF2 |
| The wrong sea | 0:35-0:55 | the colour drains: bruised violet sky, indigo water, the aliens' gills fading pale | transition |
| Scale, the question | 0:55-1:25 | near-black sea lit only by bioluminescence: the creature, the heroes' freckles, seed-light | abyss #05070F, indigo #1A1446, cyan #00F0FF, magenta #FF2E88, amber #FFB000 |

Lens and motion throughout: anamorphic 2.39 feel inside 16:9, shallow focus on
faces, wide lenses for scale, smooth gliding camera underwater, handheld only in
the storm.

## World

CEO, 2026-09-24, verbatim:

> หมู่บ้านอยากได้ฟีลแนวๆ ไม้สูง รากลงไปข้างล่าง คล้ายๆ ต้นโกงกาง ไม่มีแผ่นดิน บ้านทำจากไม้
> ที่มีลักษณะเหมือนมีตะไคร้เรืองแสงสีเขียวนีออนติดอยู่ ประมาณนั้น
>
> และตอนเช้าของเขาจะไม่ใช่สีแดงส้มเหมือนบ้านเรา แต่จะเป็นสีฟ้า ขาว อารมณ์เหมือนท้องฟ้า
> ยามค่ำคืนแต่สว่างมาก และมีดาว ดวงจันทร์ที่ใกล้ดาวมาก มองเห็นได้ชัดเลย

A planet with no land at all, only ocean to every horizon.

**Their daylight is not ours.** Morning and day are blue and white, never red or
orange: the mood of a night sky, but brilliantly bright. A huge moon hangs very
close to the planet, sharp and clearly detailed, with stars still visible in the
bright sky. (This replaces the ringed planet in draft 1.)

**The trees.** Tall mangrove-like giants standing in open water with no shore:
long arching stilt roots plunge from high up the trunk down into the sea and keep
going deep underwater. Several trees stand close together: that is the village.

**The houses.** Built of wood, lashed among the branches and on platforms over the
roots, and grown over with tufts of something like lemongrass that glows neon
green. The glowing grass is the village's signature colour, day and night.

**The resource.** The trees grow glow-seeds, pods of soft light that the village
uses as lamps. The trees are making fewer, the lamps are dimming, and wild
seed-beds grow only out in the deep. That is why the heroes leave.

## Cast (CAST, one row per character)

CEO 2026-09-24 on the first plates: "รูป 1-2 ผ่านแล้ว รูป 3 แก้ไข" (young and elder approved, mount to be
revised). "สัตว์พาหนะควรมีที่นั่งด้วยนะ ทำจากไม้ เหมือนเรานั่งบนช้าง" and "ขอ Character
อีก 1 เป็นชายเหมือนกัน แต่ร่างใหญ่ แข็งแรง ขอสีเขียวได้". The three aliens are male.
Approved plates: `char_young`, `char_elder` (ChatGPT, task-e3000e68).

The species: amphibious, cheerful, about 1.4 m tall, slender swimmer's build,
webbed three-fingered hands, a flat tail fin, large round glossy eyes with a
bright ring, a wide smiling mouth, and a mane of frilly external gills framing
the head. Skin smooth and slightly translucent, pastel, with bioluminescent
freckles. **Gill colour follows feeling: warm when happy, fading pale when afraid.**

| Plate | Who | Look (colours named) | Carries | Never | Register |
|---|---|---|---|---|---|
| `char_young` | THE YOUNG ONE, the lead | smaller; coral-pink skin; orange-gold gill frills; gold freckles across the cheeks | a woven kelp satchel; an empty glass-shell lantern | any weapon | curious, brave, quick to smile |
| `char_elder` | THE ELDER, the guide | taller; deep teal-blue skin; violet gill frills, one frill torn (old scar) | a long bone steering-pole; a necklace of spent seed husks | hurry | calm, watchful, few words |
| `char_strong` | THE STRONG ONE, the driver (new, CEO 2026-09-24) | male, the biggest of the three, broad and heavily muscled, about 1.9 m; deep moss-green skin with darker mottling on shoulders and back; lime-green glowing freckles along the arms; emerald gill frills tipped gold | a coiled kelp rope over one shoulder; a woven kelp belt | a weapon | cheerful, steady, protective |
| `char_mount` | THE MOUNT, their ride | a manta-like swimmer, wing span about 4 m, sea-green mottled back, lime-green glow on its underside; **carries a carved wooden howdah strapped to its back ridge, like an elephant's seat** (CEO 2026-09-24) | the riders | a face that talks | loyal, fast, skittish |

Villagers are the same species in other pastel colours and appear only as
background, generated inside the shots, never as plates. Names are the CEO's to
give; screen them for collisions before any prompt uses them (ai-film-production 10).

## Locations (no characters in any location plate)

| Plate | Where |
|---|---|
| `loc_village_above` | the mangrove-giant village standing in open water: tall trunks, arching stilt roots, wooden houses grown over with neon-green glowing grass, blue-white daylight, the huge close moon |
| `loc_village_roots` | underwater among the stilt roots going down into the deep, light rays from the blue-white sky, glow-seeds on the roots, neon-green glow drifting down |
| `loc_open_sea` | open ocean in their blue-white day, no land anywhere, the huge moon over the horizon |
| `loc_storm_sea` | the same sea gone wrong: violet-grey sky, waves taller than the trees, spray tearing sideways |
| `loc_deep_dark` | the deep at night: near-black water, drifting specks of light |

## What they meet

1. **The current-river.** A sharp-edged band of racing water crossing the open
   sea, streaked with plankton light, whitecaps along its edge.
2. **The wrong weather.** Noon turns to dusk; waves rise against the wind.
3. **The fleeing.** Underwater, vast shoals of glowing fish and larger beasts
   stream past the heroes the other way, ignoring them.
4. **The primordial.** CEO's scale: it is to them what the Sun is to the Earth.
   Proposal: kilometres long, so its back reads as a mountain range on a planet
   that has no land. Ancient reef and forests of barnacles on its back, its own
   clouds; along its flanks rows of cyan, magenta and amber light that wake like
   a city at night; one eye, a slow amber disc bigger than the whole village.
   When it moves, the sea tilts: that is the current and the storm (suggestion;
   the trailer never says it).

| Plate | What |
|---|---|
| `crt_mountain` | its back on the horizon as a mountain range, dark sky |
| `crt_skin` | macro of its skin: barnacle forest, lights waking |
| `crt_eye` | the eye opening, amber, filling the frame |
| `prop_seed_lantern` | the glass-shell lantern, full and glowing, then empty |

## Open for the CEO

1. ~~Two or three aliens~~ settled: three aliens plus the mount. Their names.
2. Scale: kilometres (proposal) or a literal 109x (about 220 m)?
3. Title.
4. Where the plates are made (Google Flow on the Ultra plan vs TopView), and TopView Pro $29.
