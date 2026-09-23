---
title: Official regulator license-lookup registers (Thai SEC, FCA, ASIC, CySEC, NFA, MAS, Japan FSA)
date: 2026-09-23
refresh_after: 2026-12-23
source: verified directly via Claude-in-Chrome browser (real page load) + curl HTTP status, one by one, 2026-09-23
---

# Official public registers for checking a broker/exchange's license

Used as source for `prototypes/bl-reply-packs/EP55-regulator-sites.md`
(BL EP55 CTA deliverable, task-6cc24a28). Every URL below was opened live in
a real browser on 2026-09-23 and confirmed to be the regulator's own site,
not a guess or a third-party mirror.

| Regulator | Country/region | URL | Confirmed page title / content |
|---|---|---|---|
| ก.ล.ต. (Thai SEC) | Thailand | https://market.sec.or.th/LicenseCheck/Search | "SEC Check First" — official license/product lookup, linked from sec.or.th's own nav (`www.sec.or.th/TH/Pages/main.aspx`) |
| FCA | UK | https://register.fca.org.uk/s/ | Page heading "The Financial Services Register", live search box "Enter a name or reference number" |
| ASIC | Australia | https://service.asic.gov.au/search/ | Browser tab title "ASIC Professional Registers Search" — reached via ASIC's own hub page `asic.gov.au/online-services/search-asic-registers` → "Professional registers search" → "Go to register" |
| CySEC | Cyprus | https://www.cysec.gov.cy/en-GB/entities/investment-firms/cypriot/ | "Investment Firms (Cypriot)" — official CIF regulated entities list |
| NFA BASIC | USA | https://www.nfa.futures.org/BasicNet/ | "BASIC \| NFA" — NFA's free registration/background-check database |
| MAS | Singapore | https://eservices.mas.gov.sg/fid | "Financial Institutions Directory" on mas.gov.sg, official .gov.sg domain |
| FSA | Japan | https://www.fsa.go.jp/en/regulated/licensed/index.html | "List of licensed (registered) Financial Institutions" — official FSA list of PDF/Excel registers, English |

## Notes / traps hit while verifying
- `www.sec.or.th/TH/Pages/LawandRegulations/CheckFirst.aspx` (a guessed URL)
  404s — the real Check First tool lives on a different subdomain
  (`market.sec.or.th`), only findable via the SEC homepage's own nav link.
- `connectonline.asic.gov.au/...` guesses all 403 (WAF blocks bots); the
  correct live tool turned out to be on a different subdomain entirely
  (`service.asic.gov.au`), only reachable by clicking through ASIC's own
  hub page — never construct an ASIC register URL by guessing.
- `www.fsa.go.jp/en/regulated/index.html` (guessed) 404s; correct path is
  `/en/regulated/licensed/index.html`.
- WebFetch alone is not sufficient for WAF-protected govt sites (sec.or.th,
  asic.gov.au registries returned 403 to both WebFetch and curl) — a real
  browser session (Claude-in-Chrome) was required to confirm these.
