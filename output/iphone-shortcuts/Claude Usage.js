// Claude Usage — Session(5h) / Weekly % widget (Liquid Glass style)
// อ่าน claude-usage.json ที่ Mac sync เข้าโฟลเดอร์ Scriptable (scripts/claude-usage-sync.sh)
// bar เปลี่ยนสี: เขียว <50, เหลือง 50-79, แดง >=80 · ⚠ ถ้าข้อมูลเก่ากว่า 45 นาที

const FILE = "claude-usage.json"
const STALE_MIN = 45
// Phase B: fetch live usage from the always-on VPS first (fresh even when the
// Mac is off), then fall back to the Mac's iCloud file. Token injected on deploy.
const USAGE_URL = "https://webhook.mooniex.com/claude-usage?k=__USAGE_TOKEN__"

// ---------- palette (glass + Claude terracotta) ----------
const CLAY = new Color("#E07B53")
const WHITE = Color.white()
const FROST = new Color("#FFFFFF", 0.10)
const FROST2 = new Color("#FFFFFF", 0.15)
const RIM = new Color("#FFFFFF", 0.30)
const MUTE = new Color("#C9B8AE", 0.95)
const FAINT = new Color("#B0A29A", 0.6)
const GREEN = new Color("#5EEAA0")
const AMBER = new Color("#FFC95E")
const RED = new Color("#FF7A7A")

function pctColor(p) {
  if (p == null) return FAINT
  if (p < 50) return GREEN
  if (p < 80) return AMBER
  return RED
}

// ---------- data ----------
async function loadData() {
  // 1) always-on VPS over HTTPS — fresh even when the Mac is asleep / off / dead
  if (USAGE_URL.indexOf("__USAGE_TOKEN__") === -1) {
    try {
      const r = new Request(USAGE_URL)
      r.timeoutInterval = 8
      const j = await r.loadJSON()
      if (j && j.five_hour) return j
    } catch (e) {}
  }
  // 2) fallback: the Mac's iCloud file (works while the Mac is awake)
  try {
    const f = FileManager.iCloud()
    const p = f.joinPath(f.documentsDirectory(), FILE)
    if (!f.fileExists(p)) return null
    if (!f.isFileDownloaded(p)) await f.downloadFileFromiCloud(p)
    return JSON.parse(f.readString(p))
  } catch (e) { return null }
}

// ---------- background ----------
function hex2(n) { return Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0") }
function rgb(c) { return "#" + hex2(c[0]) + hex2(c[1]) + hex2(c[2]) }

function glow(ctx, cx, cy, r, c, a) {
  const L = 22
  for (let i = L; i >= 1; i--) {
    const rr = r * i / L
    ctx.setFillColor(new Color(rgb(c), a))
    ctx.fillEllipse(new Rect(cx - rr, cy - rr, rr * 2, rr * 2))
  }
}

function bgImage(W, H) {
  const ctx = new DrawContext()
  ctx.size = new Size(W, H)
  ctx.opaque = false
  ctx.respectScreenScale = true
  const top = [22, 14, 12], bot = [44, 24, 20]  // dark espresso → warm brown
  const N = 70
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1)
    ctx.setFillColor(new Color(rgb([
      top[0] + (bot[0] - top[0]) * t,
      top[1] + (bot[1] - top[1]) * t,
      top[2] + (bot[2] - top[2]) * t
    ]), 1))
    ctx.fillRect(new Rect(0, H * i / N, W, H / N + 1))
  }
  glow(ctx, W * 0.9, H * 0.05, W * 0.3, [224, 123, 83], 0.05)   // terracotta
  glow(ctx, W * 0.08, H * 1.0, W * 0.33, [255, 201, 94], 0.035) // amber
  return ctx.getImage()
}

// progress bar เป็นภาพ (โค้งมน + track กระจก)
function barImage(pct, w, h, color) {
  const ctx = new DrawContext()
  ctx.size = new Size(w, h)
  ctx.opaque = false
  ctx.respectScreenScale = true
  const track = new Path()
  track.addRoundedRect(new Rect(0, 0, w, h), h / 2, h / 2)
  ctx.addPath(track)
  ctx.setFillColor(new Color("#FFFFFF", 0.13))
  ctx.fillPath()
  if (pct != null && pct > 0) {
    const fw = Math.max(h, w * Math.min(pct, 100) / 100)
    const fill = new Path()
    fill.addRoundedRect(new Rect(0, 0, fw, h), h / 2, h / 2)
    ctx.addPath(fill)
    ctx.setFillColor(color)
    ctx.fillPath()
  }
  return ctx.getImage()
}

// ---------- helpers ----------
function fmtReset(iso, mode) {
  if (!iso) return ""
  const d = new Date(iso)
  if (mode === "time") {
    const ms = d - new Date()
    if (ms > 0 && ms < 86400000) {
      const hrs = Math.floor(ms / 3600000), min = Math.floor((ms % 3600000) / 60000)
      return hrs > 0 ? `รีเซ็ตใน ${hrs} ชม. ${min} น.` : `รีเซ็ตใน ${min} นาที`
    }
    return "รีเซ็ต " + d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" })
  }
  return "รีเซ็ต " + d.toLocaleDateString("th-TH", { weekday: "short", day: "numeric", month: "short" })
}

function glassStack(parent, radius, fill) {
  const s = parent.addStack()
  s.backgroundColor = fill || FROST
  s.cornerRadius = radius
  s.borderWidth = 1
  s.borderColor = RIM
  s.centerAlignContent()
  return s
}

function usageRow(parent, label, pct, sub, barW) {
  const head = parent.addStack()
  head.layoutHorizontally()
  head.centerAlignContent()
  const l = head.addText(label)
  l.font = Font.semiboldRoundedSystemFont(10)
  l.textColor = MUTE
  head.addSpacer()
  const v = head.addText(pct == null ? "—" : Math.round(pct) + "%")
  v.font = Font.boldMonospacedSystemFont(13)
  v.textColor = pctColor(pct)
  parent.addSpacer(3)
  const bar = parent.addImage(barImage(pct, barW, 5, pctColor(pct)))
  bar.imageSize = new Size(barW, 5)
  if (sub) {
    parent.addSpacer(2)
    const s = parent.addText(sub)
    s.font = Font.mediumSystemFont(8)
    s.textColor = FAINT
  }
}

// ---------- layouts ----------
function buildHeader(w, d) {
  const row = w.addStack()
  row.layoutHorizontally()
  row.centerAlignContent()
  const pill = glassStack(row, 12, FROST2)
  pill.setPadding(3, 9, 3, 10)
  const sf = SFSymbol.named("sparkle")
  const ic = pill.addImage(sf.image)
  ic.imageSize = new Size(11, 11)
  ic.tintColor = CLAY
  pill.addSpacer(5)
  const t = pill.addText("Claude Usage")
  t.font = Font.boldRoundedSystemFont(11)
  t.textColor = CLAY
  row.addSpacer()

  // เวลาอัปเดต + เตือนข้อมูลเก่า
  const gen = d && d.generated_at ? new Date(d.generated_at) : null
  const stale = !gen || (new Date() - gen) > STALE_MIN * 60000
  const tp = glassStack(row, 10, FROST)
  tp.setPadding(2, 8, 2, 8)
  const tt = tp.addText((stale ? "⚠ " : "") + (gen
    ? gen.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" })
    : "ไม่มีข้อมูล"))
  tt.font = Font.mediumSystemFont(9)
  tt.textColor = stale ? RED : MUTE
}

function buildMedium(w, d) {
  w.setPadding(12, 14, 10, 14)
  buildHeader(w, d)
  w.addSpacer()

  const row = w.addStack()
  row.layoutHorizontally()

  const cardW = 137, barW = cardW - 24
  const c1 = glassStack(row, 16, FROST)
  c1.layoutVertically()
  c1.setPadding(9, 12, 9, 12)
  usageRow(c1, "SESSION · 5 ชม.", d?.five_hour?.utilization, fmtReset(d?.five_hour?.resets_at, "time"), barW)

  row.addSpacer(8)

  const c2 = glassStack(row, 16, FROST)
  c2.layoutVertically()
  c2.setPadding(9, 12, 9, 12)
  usageRow(c2, "WEEKLY · 7 วัน", d?.seven_day?.utilization, fmtReset(d?.seven_day?.resets_at, "date"), barW)

  w.addSpacer()

  // แถวล่าง: sonnet/opus weekly + extra usage
  const foot = w.addStack()
  foot.layoutHorizontally()
  foot.centerAlignContent()
  const bits = []
  if (d?.seven_day_sonnet?.utilization != null) bits.push("Sonnet " + Math.round(d.seven_day_sonnet.utilization) + "%")
  if (d?.seven_day_opus?.utilization != null) bits.push("Opus " + Math.round(d.seven_day_opus.utilization) + "%")
  if (d?.extra_usage?.is_enabled && d?.extra_usage?.used_credits != null) {
    bits.push("Extra $" + (d.extra_usage.used_credits / 100).toFixed(2) + " (" + (d.extra_usage.utilization ?? 0).toFixed(1) + "%)")
  }
  const f1 = foot.addText(bits.join(" · ") || "Max plan")
  f1.font = Font.mediumSystemFont(8)
  f1.textColor = FAINT
  foot.addSpacer()
}

function buildSmall(w, d) {
  w.setPadding(11, 12, 10, 12)
  buildHeader(w, d)
  w.addSpacer()
  const card = glassStack(w, 14, FROST)
  card.layoutVertically()
  card.setPadding(8, 10, 8, 10)
  const barW = 111
  usageRow(card, "SESSION", d?.five_hour?.utilization, null, barW)
  card.addSpacer(7)
  usageRow(card, "WEEKLY", d?.seven_day?.utilization, null, barW)
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
w.refreshAfterDate = new Date(Date.now() + 10 * 60 * 1000)

if (config.runsInWidget) {
  Script.setWidget(w)
} else if (fam === "small") {
  w.presentSmall()
} else {
  w.presentMedium()
}
Script.complete()
