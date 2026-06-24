// Claude Usage — minimal pixel-art widget
// Session(5h) + Weekly(7d) utilization %, each with a "reset in ..." countdown.
// Data: VPS over HTTPS (fresh even when the Mac is off) -> Mac's iCloud file ->
// on-device last-good cache (so it never falls back to a blank "no data").
// The orange Claude mark is the real sprite, drawn pixel-for-pixel from the
// reference (extracted: 12x8 — head + two eyes, full-width arms, four legs).
// Flat background, blocky segmented bars — no glass / no gradient.
//
// NOTE: home-screen widgets are static snapshots — the countdown is accurate at
// render time and refreshes when iOS repaints (~every few min); it does not tick
// live. refreshAfterDate below is only a hint (~5 min).

const FILE      = "claude-usage.json"        // iCloud fallback (written by the Mac feed)
const LOCAL     = "claude-usage-last.json"    // on-device last-good cache
const STALE_MIN = 45
const USAGE_URL = "https://webhook.mooniex.com/claude-usage?k=__USAGE_TOKEN__"

// ---------- palette (pixel-art: clay sprite on the reference's warm black) ----------
const BG     = new Color("#211F1D")
const CLAUDE = new Color("#C9785A")   // sampled from the reference creature
const WHITE  = new Color("#EDE7E2")
const MUTE   = new Color("#8C8079")
const FAINT  = new Color("#5F564F")
const GREEN  = new Color("#5EEAA0")
const AMBER  = new Color("#FFC95E")
const RED    = new Color("#FF7A7A")
const TRACK  = new Color("#FFFFFF", 0.07)

function pctColor(p) {
  if (p == null) return FAINT
  if (p < 50) return GREEN
  if (p < 80) return AMBER
  return RED
}

// ---------- data: URL -> iCloud -> local last-good (never blank) ----------
async function fromURL() {
  if (USAGE_URL.indexOf("__USAGE_TOKEN__") !== -1) return null
  try {
    const r = new Request(USAGE_URL); r.timeoutInterval = 8
    const j = await r.loadJSON()
    return (j && j.five_hour) ? j : null
  } catch (e) { return null }
}
async function fromICloud() {
  try {
    const f = FileManager.iCloud()
    const p = f.joinPath(f.documentsDirectory(), FILE)
    if (!f.fileExists(p)) return null
    if (!f.isFileDownloaded(p)) await f.downloadFileFromiCloud(p)
    const j = JSON.parse(f.readString(p))
    return (j && j.five_hour) ? j : null
  } catch (e) { return null }
}
function localFile() { const f = FileManager.local(); return f.joinPath(f.cacheDirectory(), LOCAL) }
function saveLocal(d) { try { FileManager.local().writeString(localFile(), JSON.stringify(d)) } catch (e) {} }
function loadLocal() {
  try { const f = FileManager.local(); return f.fileExists(localFile()) ? JSON.parse(f.readString(localFile())) : null }
  catch (e) { return null }
}
async function loadData() {
  let d = await fromURL()
  if (!d) d = await fromICloud()
  if (d) { saveLocal(d); return d }
  return loadLocal()
}

// ---------- countdown ----------
function countdown(iso) {
  if (!iso) return null
  const ms = new Date(iso) - new Date()
  if (ms <= 0) return "พร้อมใช้"
  const d = Math.floor(ms / 864e5), h = Math.floor((ms % 864e5) / 36e5), m = Math.floor((ms % 36e5) / 6e4)
  if (d > 0) return `${d} วัน ${h} ชม.`
  if (h > 0) return `${h} ชม. ${m} น.`
  return `${m} นาที`
}

// ---------- the real Claude sprite (12x8), pixel-for-pixel ----------
const SPRITE = [
  "..XXXXXXXX..",
  "..X.XXXX.X..",
  "XXXXXXXXXXXX",
  "XXXXXXXXXXXX",
  "..XXXXXXXX..",
  "..XXXXXXXX..",
  "..X.X..X.X..",
  "..X.X..X.X..",
]
function claudeMark(px) {
  const w = SPRITE[0].length, h = SPRITE.length
  const c = new DrawContext()
  c.size = new Size(w * px, h * px); c.opaque = false; c.respectScreenScale = true
  c.setFillColor(CLAUDE)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
    if (SPRITE[y][x] === "X") c.fillRect(new Rect(x * px, y * px, px, px))
  return c.getImage()
}

// ---------- blocky segmented bar (pixel meter) ----------
function barImage(pct, w, h, color) {
  const N = 16, gap = 2
  const cw = (w - gap * (N - 1)) / N
  const c = new DrawContext()
  c.size = new Size(w, h); c.opaque = false; c.respectScreenScale = true
  const filled = pct == null ? 0 : Math.round(Math.min(pct, 100) / 100 * N)
  for (let i = 0; i < N; i++) {
    c.setFillColor(i < filled ? color : TRACK)
    c.fillRect(new Rect(i * (cw + gap), 0, cw, h))
  }
  return c.getImage()
}

// ---------- pieces ----------
function header(w, d, compact) {
  const row = w.addStack(); row.layoutHorizontally(); row.centerAlignContent()
  const ic = row.addImage(claudeMark(3))
  ic.imageSize = compact ? new Size(18, 12) : new Size(24, 16)
  row.addSpacer(compact ? 6 : 8)
  const t = row.addText(compact ? "Usage" : "Claude Usage")
  t.font = Font.semiboldRoundedSystemFont(compact ? 11 : 13); t.textColor = WHITE
  row.addSpacer()
  const gen = d && d.generated_at ? new Date(d.generated_at) : null
  const stale = !gen || (new Date() - gen) > STALE_MIN * 6e4
  const tt = row.addText((stale ? "⚠ " : "") + (gen
    ? gen.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" }) : "—"))
  tt.font = Font.mediumSystemFont(compact ? 9 : 10); tt.textColor = stale ? RED : FAINT
}

function metricRow(w, label, block, barW, showCountdown) {
  const pct = block && block.utilization != null ? block.utilization : null
  const head = w.addStack(); head.layoutHorizontally(); head.centerAlignContent()
  const l = head.addText(label); l.font = Font.mediumSystemFont(10); l.textColor = MUTE
  head.addSpacer()
  const v = head.addText(pct == null ? "—" : Math.round(pct) + "%")
  v.font = Font.boldMonospacedSystemFont(15); v.textColor = pctColor(pct)
  w.addSpacer(6)
  const bar = w.addImage(barImage(pct, barW, 8, pctColor(pct))); bar.imageSize = new Size(barW, 8)
  if (showCountdown) {
    w.addSpacer(5)
    const cd = countdown(block && block.resets_at)
    const s = w.addText(cd ? "รีเซ็ตใน " + cd : " ")
    s.font = Font.mediumSystemFont(9); s.textColor = FAINT
  }
}

// ---------- layouts ----------
function buildMedium(w, d) {
  w.setPadding(15, 17, 15, 17)
  header(w, d, false)
  w.addSpacer()
  const barW = 295
  metricRow(w, "SESSION · 5 ชม.", d && d.five_hour, barW, true)
  w.addSpacer(13)
  metricRow(w, "WEEKLY · 7 วัน", d && d.seven_day, barW, true)
}

function buildSmall(w, d) {
  w.setPadding(12, 13, 12, 13)
  header(w, d, true)
  w.addSpacer()
  const barW = 129
  metricRow(w, "SESSION", d && d.five_hour, barW, false)
  w.addSpacer(10)
  metricRow(w, "WEEKLY", d && d.seven_day, barW, false)
}

// ---------- main ----------
const data = await loadData()
const fam = config.widgetFamily || "medium"
const w = new ListWidget()
w.backgroundColor = BG
if (fam === "small") buildSmall(w, data)
else buildMedium(w, data)
w.refreshAfterDate = new Date(Date.now() + 5 * 60 * 1000)

if (config.runsInWidget) Script.setWidget(w)
else if (fam === "small") w.presentSmall()
else w.presentMedium()
Script.complete()
