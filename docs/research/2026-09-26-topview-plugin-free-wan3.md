---
question: What exactly does TopView's "install the plugin for 5 H3 + 5 Wan 3 + 10 GPT Image 2.5 free" give, and may the ILAG challenge entry use it?
date: 2026-09-26
sources: [https://www.topview.ai/plugin, https://github.com/topviewai/plugins, https://github.com/topviewai/plugins/blob/main/docs/claude.md, https://github.com/topviewai/plugins/blob/main/docs/codex.md, docs/promo/TOPVIEW-WAN3-RULES.md]
measured_by_us: no
refresh_after: 2026-10-26
confidence: medium
---

## 🟡 PERISHABLE (TopView's product; spot-check the line you rely on)

- **Offer, verbatim (official, topview.ai/plugin, read 2026-09-26):** "Install the plugin for 5 H3 + 5 Wan 3 + 10 GPT
  Image 2.5 free" · "Pro plan and above only. Benefits are auto-granted after authorization. Wan 3 only—Wan 3 Prime is
  not supported. 720p/480p only. GPT Image 2.5 is limited to 1K + Medium."
- **Not stated anywhere read:** how long one free Wan 3 generation may be, whether the grant is one-time or monthly,
  its expiry, how it is redeemed, watermark, where the output is stored.
- **The challenge counts it (official, the activity page's own API, read 2026-09-23, TOPVIEW-WAN3-RULES.md):** the free
  Wan3 routes table lists "Install the plugin | +5"; grants "expire 7 days after grant". The standard route's two
  free generations are described there as 30-second generations, so a free generation is probably up to 30 s
  (inference; not stated for the plugin).
- **What the plugin is (official, GitHub README, MIT):** "Official public plugin source for the browser-based Topview
  Canvas integration": an MCP server named `topview-browser` that lets an agent "create, organize, and edit Canvas
  content through MCP" and returns "an authorized normal web URL" to the Canvas. Supported: Claude, Codex, Cursor,
  Grok Bot, Hermes.
- **Claude Code install (official, docs/claude.md):**
  `claude plugin marketplace add https://github.com/topviewai/plugins --scope user --sparse .claude-plugin plugins`
  then `claude plugin install topview-browser@topview --scope user`; "Complete OAuth on first use and start a new
  conversation". The OAuth scopes are not stated.
- Challenge line that matters: "The primary AI video generation for the entry must be completed with the Wan3 model on
  the Topview platform"; the organiser may verify "the creation process, Topview project, and material licenses".
  Whether a plugin Canvas counts as the "Topview project" is not stated (inference: it lives in the same account).

## 🟢 DURABLE

- Nothing measured yet. The first plugin generation must record: seconds allowed per free generation, whether several
  shots may share one generation, the resolution delivered, and where the file appears in the account.
- Not done on purpose (CEO 2026-09-26: "ห้ามใช้นะ เข้าไปอ่านกฎให้ก่อน"): the plugin is not installed anywhere.
