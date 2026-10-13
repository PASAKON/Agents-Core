---
question: What does it cost per month to take the Contabo hub (Cloud VPS 10 NVMe, Singapore, 8 GB) to about 16 GB RAM, as an in-place upgrade or a second small VPS, and what downtime does each mean?
date: 2026-10-13
author: CFO (Contabo) session efca9dc4, for the org restructure plan (COO brief, CEO 2026-10-13)
sources: [https://contabo.com/en/vps/, https://contabo.com/en/vps-singapore/, https://contabo.com/blog/kb/103000269722-can-i-change-my-virtual-private-server-vps-virtual-dedicated-server-vds-plan/, https://contabo.com/blog/kb/103000269766-how-do-i-change-my-servers-region/, https://cybernews.com/best-web-hosting/the-8-best-singapore-vps-services/, https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml, https://www.temperstack.com/learn/contabo/upgrade-vps-resources/]
measured_by_us: no. Prices were read from Contabo's public pages through WebFetch, which returns a model summary of the page. The ECB rate was read raw with curl. Nothing was ordered and the control panel was not opened.
refresh_after: 2026-11-12
confidence: medium for list prices and the €33 fee (Contabo's own pages). Low for the Singapore location fee (third-party figure, not on Contabo's pages).
labels: [M] Contabo official page · [3] third party · [O] our estimate
---

# Contabo hub → ~16 GB RAM: price + downtime (look-up only, nothing bought)

## 🟢 DURABLE
- The hub is **Cloud VPS 10 NVMe, Singapore, €8/mo**. Source: ADR `decisions/2026-06-16-contabo-migration-complete.md`, which recorded the price at purchase; it has not been re-checked against an invoice since.
  Measured spec on 2026-10-13: 4 vCPU AMD EPYC, 7,941 MB RAM, 4 GB swap with about 2.1 GB in use, 75 GB disk at 89 %.
- **Contabo's Cloud VPS line has no 16 GB plan.** Its tiers are 8, 12, 24, 48, 64 and 96 GB. "16 GB" means one of three things:
  - 12 GB, which falls short of 16;
  - 24 GB, which overshoots;
  - two 8 GB boxes.
- A plan upgrade has two official methods in the Customer Control Panel [M, KB 103000269722]:
  - **Live migration.** Data is kept and the server stays online while the copy runs. It must then be restarted and reconfigured. Contabo says the downtime "cannot be given an exact timeframe".
    - Fee: a one-time service charge of **€33.00 + VAT** [M, KB 103000269766].
    - The main IPv4 is reassigned [M, KB 103000269766, region-change wording]. For us that means repointing DNS: `webhook.mooniex.com` and `n8n.mooniex.com` both point at the hub.
  - **New deployment.** Free, but it wipes the disk and issues a new IP.
- User reports of live-migration downtime vary widely [3]: some say none; one says about 16 h against an advertised 15 min; another says about 60 h. These are anecdotes, not measurements.

## 🟡 PERISHABLE — prices on 2026-10-13
| Plan | vCPU / RAM / disk | List €/mo [M] | + Singapore fee [3/O] | ≈ €/mo SG [O] | ≈ ฿/mo (ECB 37.580) |
|---|---|---|---|---|---|
| Cloud VPS 4 | 4 / 8 GB / 100 GB SSD | 5.50 | ~3 | ~8.50 | ~319 |
| Cloud VPS 6 | 6 / 12 GB / 100 GB NVMe or 200 GB SSD | 7.50 | ~3 | ~10.50 | ~395 |
| Cloud VPS 8 | 8 / 24 GB / 150 GB NVMe or 300 GB SSD | 14.00 | ~3 (may be higher on larger plans) | ~17.00 | ~639 |

- **List price** is the month-to-month price. The page states a 24-month term costs 20 % less (€4.40, €6.00 and €11.20). No setup fee is shown for any term [M].
- **Singapore location fee:** Contabo's page says one applies but gives no amount [M]. Cybernews quotes **$3.10/mo** for Cloud VPS 4 ($5.28 → $8.38) [3]. That is consistent with our €8 bill against a ~€4.5–5.5 list price [O]. The exact figure appears only in the control panel at order or upgrade time.
- **Tax:** the page toggles between incl. and excl. VAT. The figures above are before tax.
- **EUR/THB 37.580** is the ECB reference rate for 2026-10-13 [M].
