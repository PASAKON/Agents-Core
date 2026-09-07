// Replay notes for the Google Flow recon walk (task-796a93f6, 2026-09-07).
// This is NOT an executable script — Flow has no public API/CLI/webhook surface
// discoverable anywhere in the UI (see docs/reports/google-flow-recon-20260907.md,
// section E). Every step below is a manual click-by-click browser action; nothing
// here can be driven headlessly without the claude-in-chrome MCP browser tools.
//
// Composer chips (attached Ingredients) reset silently on:
//   - expanding the prompt textbox by scrolling
//   - clicking the composer's "x" close button
// ALWAYS re-verify chip count via the "+" picker (a character excluded from the
// list = still attached) immediately before firing. See skill note "Count the
// reference chips before you fire" in browser-operator.

const STEPS = [
  // 1. New project
  { at: 'flow.google.com', click: '+ โปรเจ็กต์ใหม่ (new project tile)' },
  { click: 'project title text → rename to "AI Film" → Enter' },

  // 2. Characters (Ingredients) — FREE, 0 credits each, confirmed twice
  { nav: 'sidebar → ตัวละคร (Characters)' },
  { click: '+ ตัวละครใหม่ (new character tile)' },
  { type: '<exact character prompt> into "อธิบายตัวละครของคุณ…"' },
  { note: 'model defaults to "Nano Banana Pro" — do not change' },
  { click: 'เริ่มสร้าง (submit arrow)' },
  { wait: 'poll for % complete, ~10-15s' },
  { click: 'pencil next to title → type "ชื่อตัวละคร" (character name, e.g. @lung_somchai) → Tab' },
  { repeat: 'for the second character' },

  // 3. Ceiling test — costs nothing, do not generate video here
  { nav: 'สื่อทั้งหมด (All media) grid' },
  { click: '"+" in composer → picker opens' },
  { note: 'picker excludes already-attached characters — that IS the confirmation a chip bound' },
  { click: 'select character row → "เพิ่มไปยังพรอมต์" (Add to prompt)', repeat: 'for each ingredient' },
  { note: '4 chips attached with zero UI block, error, or greying-out — no 3-ingredient ceiling enforced at attach time (untested at generation time)' },

  // 4. Storyboard exploration — read-only, no cost
  { nav: 'sidebar → ฉาก (Scenes) — empty gallery, "เริ่มสร้างหรือวางสื่อ", no pre-gen shot-list support' },
  { nav: 'sidebar → เครื่องมือ (Tools) — community/template gallery, unrelated to storyboarding' },
  { note: 'composer "Agent" toggle → "คำสั่งสำหรับ Agent" panel is the closest thing to automation; in-app only, not an API' },

  // 5. Video generation — THE PAID STEP. Verify credit balance before AND after.
  { nav: 'สื่อทั้งหมด grid, composer at bottom' },
  { click: '"+" → attach both required character chips (re-verify per note above)' },
  { click: 'sliders icon next to composer → settings panel opens' },
  { select: 'model dropdown → "Veo 3.1 - Fast" (NEVER "Veo 3.1 - Quality" = 100 credits)' },
  { select: 'aspect → 9:16' },
  { select: 'quantity → x1' },
  { verify: 'cost readout says "การสร้างจะใช้ 20 เครดิต" before proceeding' },
  { type: '<exact 8s shot prompt> into composer textbox (after chips are visible above it)' },
  { verify_again: 're-open the "+" picker once more — confirm both chips still excluded (still attached) — composer state is fragile, see top note' },
  { read_credits: 'account menu → เครดิต Google Flow N เครดิต — record N' },
  { click: 'arrow_forward (fire)' },
  { wait: 'poll % complete, first run ~51s wall-clock, second run ~94s' },
  { read_credits: 'account menu again — record delta (expect -20 for Fast/8s/720p/9:16/x1)' },

  // 6. Upscale — NOT FOUND. Do not spend time re-searching without a product update.
  { note: 'Searched: toolbar more_vert, share icon, model dropdown, right-click clip menu, fullscreen player, "pen_magic" icon, asset filter resolution facet (only lists 720p/360p). No upscale-to-1080p control exists in this account/product state.' },

  // 7. Variance run — only if still under 60 credits cumulative
  { repeat: 're-attach both chips (composer resets between grid navigations), retype identical prompt, verify settings unchanged, fire again' },
  { note: 'repeat generations of the SAME prompt+chips land as versions of ONE asset card (small version-selector strip at top of the editor), not separate grid cards' },

  // 8. Download + probe
  { click: 'top-toolbar download icon, OR right-click clip in timeline → "ดาวน์โหลด"' },
  { note: 'second-version export can hang on "Exporting your scene…" indefinitely — reload the page once, then retry the download click; this is a free action so retrying costs nothing but time' },
  { shell: 'ffprobe -hide_banner -i <file> 2>&1 | grep -E "Duration|Stream"' },
];

module.exports = { STEPS };
