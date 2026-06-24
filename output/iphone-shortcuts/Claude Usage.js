// Claude Usage — minimal widget
// Session(5h) + Weekly(7d) utilization %, each with a "reset in ..." countdown.
// Data: VPS over HTTPS (fresh even when the Mac is off) -> Mac's iCloud file ->
// on-device last-good cache (so it never falls back to a blank "no data").
// The little orange Claude mark is drawn in code (crisp at any size, no asset).
// Bar colour: green <50, amber 50-79, red >=80.  Last-update time top-right.
//
// NOTE: home-screen widgets are static snapshots — the countdown is accurate at
// render time and refreshes when iOS repaints (~every few min), it does not tick
// live. refreshAfterDate below is a hint (~5 min).

const FILE      = "claude-usage.json"        // iCloud fallback (written by the Mac feed)
const LOCAL     = "claude-usage-last.json"    // on-device last-good cache
const STALE_MIN = 45
const USAGE_URL = "https://webhook.mooniex.com/claude-usage?k=__USAGE_TOKEN__"

// ---------- palette (minimal, Claude clay on warm black) ----------
const CLAUDE = new Color("#D97757")
const WHITE  = new Color("#F5F0EC")
const MUTE   = new Color("#9B8C82")
const FAINT  = new Color("#6E635B")
const GREEN  = new Color("#5EEAA0")
const AMBER  = new Color("#FFC95E")
const RED    = new Color("#FF7A7A")
const TRACK  = new Color("#FFFFFF", 0.08)

function pctColor(p) {
  if (p == null) return FAINT
  if (p < 50) return GREEN
  if (p < 80) return AMBER
  return RED
}

// ---------- data: URL -> iCloud -> local last-good (never blank) ----------
async function fromURL() {
  if (USAGE_URL.indexOf("__USAGE_TOKEN__") !== -1) return null   // token not injected
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
  return loadLocal()   // last-good rather than blank
}

// ---------- helpers ----------
function hex2(n) { return Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0") }
function rgb(c) { return "#" + hex2(c[0]) + hex2(c[1]) + hex2(c[2]) }

function countdown(iso) {
  if (!iso) return null
  const ms = new Date(iso) - new Date()
  if (ms <= 0) return "พร้อมใช้"
  const d = Math.floor(ms / 864e5), h = Math.floor((ms % 864e5) / 36e5), m = Math.floor((ms % 36e5) / 6e4)
  if (d > 0) return `${d} วัน ${h} ชม.`
  if (h > 0) return `${h} ชม. ${m} น.`
  return `${m} นาที`
}

// little orange Claude pixel mark, drawn from a bitmap
function claudeMark(px) {
  const P = ["..XXXXX..", "..X.X.X..", "XXXXXXXXX", "..XXXXX..", "..X.X.X.."]
  const w = P[0].length, h = P.length
  const c = new DrawContext()
  c.size = new Size(w * px, h * px); c.opaque = false; c.respectScreenScale = true
  c.setFillColor(CLAUDE)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
    if (P[y][x] === "X") c.fillRect(new Rect(x * px, y * px, px, px))
  return c.getImage()
}

function bgImage(W, H) {
  const c = new DrawContext()
  c.size = new Size(W, H); c.opaque = false; c.respectScreenScale = true
  const top = [26, 21, 18], bot = [17, 13, 9], N = 64
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1)
    c.setFillColor(new Color(rgb([top[0] + (bot[0] - top[0]) * t, top[1] + (bot[1] - top[1]) * t, top[2] + (bot[2] - top[2]) * t]), 1))
    c.fillRect(new Rect(0, H * i / N, W, H / N + 1))
  }
  return c.getImage()
}

function barImage(pct, w, h, color) {
  const c = new DrawContext()
  c.size = new Size(w, h); c.opaque = false; c.respectScreenScale = true
  const track = new Path(); track.addRoundedRect(new Rect(0, 0, w, h), h / 2, h / 2)
  c.addPath(track); c.setFillColor(TRACK); c.fillPath()
  if (pct != null && pct > 0) {
    const fw = Math.max(h, w * Math.min(pct, 100) / 100)
    const fill = new Path(); fill.addRoundedRect(new Rect(0, 0, fw, h), h / 2, h / 2)
    c.addPath(fill); c.setFillColor(color); c.fillPath()
  }
  return c.getImage()
}

// ---------- pieces ----------
function header(w, d, compact) {
  const row = w.addStack(); row.layoutHorizontally(); row.centerAlignContent()
  const ic = row.addImage(claudeMark(compact ? 2 : 3))
  ic.imageSize = compact ? new Size(18, 10) : new Size(27, 15)
  row.addSpacer(compact ? 5 : 7)
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
  w.addSpacer(5)
  const bar = w.addImage(barImage(pct, barW, 6, pctColor(pct))); bar.imageSize = new Size(barW, 6)
  if (showCountdown) {
    w.addSpacer(4)
    const cd = countdown(block && block.resets_at)
    const s = w.addText(cd ? "รีเซ็ตใน " + cd : " ")
    s.font = Font.mediumSystemFont(9); s.textColor = FAINT
  }
}

// ---------- layouts ----------
function buildMedium(w, d) {
  w.setPadding(14, 16, 14, 16)
  header(w, d, false)
  w.addSpacer()
  const barW = 297
  metricRow(w, "SESSION · 5 ชม.", d && d.five_hour, barW, true)
  w.addSpacer(12)
  metricRow(w, "WEEKLY · 7 วัน", d && d.seven_day, barW, true)
}

function buildSmall(w, d) {
  w.setPadding(12, 13, 12, 13)
  header(w, d, true)
  w.addSpacer()
  const barW = 129
  metricRow(w, "SESSION", d && d.five_hour, barW, false)
  w.addSpacer(9)
  metricRow(w, "WEEKLY", d && d.seven_day, barW, false)
}

// ---------- main ----------
const data = await loadData()
const fam = config.widgetFamily || "medium"
const w = new ListWidget()
if (fam === "small") {
  w.backgroundImage = bgImage(155, 155)
  buildSmall(w, data)
} else {
  w.backgroundImage = bgImage(329, 155)
  buildMedium(w, data)
}
w.refreshAfterDate = new Date(Date.now() + 5 * 60 * 1000)

if (config.runsInWidget) Script.setWidget(w)
else if (fam === "small") w.presentSmall()
else w.presentMedium()
Script.complete()
