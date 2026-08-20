# RunPod Console Survey — 2026-08-21

Read-only survey. No pod deployed, no network volume created, no payment
form opened, no MFA/terms accepted. Account balance $0.00 throughout.

## 1. Region list (verbatim, Secure Cloud region dropdown, `/deploy`)

The Secure Cloud region dropdown groups datacenter codes by continent
(click "All \<Continent\>" to expand):

**All Asia**
- AP-IN-1
- AP-JP-1

**All North America**
- CA-MTL-1
- CA-MTL-3
- CA-MTL-4
- US-CA-2
- US-CO-1
- US-GA-2
- US-IL-1
- US-KS-2
- US-MD-1
- US-MO-1
- US-MO-2
- US-NC-1
- US-NC-2
- US-NE-1
- US-TX-3
- US-TX-4
- US-WA-1
- US-WA-2

**All Europe**
- EU-CZ-1
- EU-FR-1
- EU-NL-1
- EU-RO-1
- EU-SE-1
- EUR-IS-1
- EUR-IS-2
- EUR-IS-3
- EUR-IS-4
- EUR-NO-1
- EUR-NO-2

**All Oceania**
- OC-AU-1

32 datacenter codes total across 4 continent groups.

**Note:** switching cloud type to Community Cloud changes the region
control entirely — it becomes a flat 11-country checklist (see §2), not
the 32-code datacenter list above. The datacenter-code list is Secure
Cloud only.

## 2. Per-region 48GB stock (Community Cloud, VRAM filter = 48, single-card GPUs only)

Region control in Community Cloud = country, not datacenter code. Rows below
exclude multi-GPU bundle listings (e.g. "4x RTX 4070 Ti") — only genuine
48GB-VRAM single cards are counted, matching the reference snapshot format.

| Region | L40S | L40 | RTX 6000 Ada | RTX PRO 5000 | RTX A6000 |
|---|---|---|---|---|---|
| Any (no filter) | $0.79/hr, 5 max | $0.69/hr, 2 max | $0.74/hr, 2 max | $0.82/hr, 4 max | unavailable |
| CA - Canada | unavailable | unavailable | unavailable | unavailable | unavailable |
| CZ - Czech Republic | unavailable | unavailable | unavailable | unavailable | unavailable |
| ES - Spain | unavailable | unavailable | unavailable | $0.82/hr, 4 max | unavailable |
| FR - France | unavailable | unavailable | unavailable | unavailable | unavailable |
| HR - Croatia | unavailable | unavailable | unavailable | unavailable | unavailable |
| PT - Portugal | unavailable | unavailable | unavailable | unavailable | unavailable |
| SE - Sweden | unavailable | unavailable | unavailable | unavailable | unavailable |
| SK - Slovakia | unavailable | unavailable | unavailable | unavailable | unavailable |
| TT - Trinidad and Tobago | unavailable | unavailable | unavailable | unavailable | unavailable |
| TW - Taiwan | $0.79/hr, 4 max | unavailable | unavailable | unavailable | unavailable |
| US - United States | unavailable | unavailable | $0.74/hr, 1 max | unavailable | unavailable |

Every unavailable cell showed "$0.00/hr" and a nominal max count (8, 10, 8,
4 respectively for L40S/L40/RTX 6000 Ada/RTX PRO 5000, 8 for RTX A6000) —
that count is a slot capacity, not live stock; "unavailable" is the live
status. Only Spain, Taiwan and United States had any 48GB single-card stock
at all; the other 8 countries showed nothing available at 48GB.

## 3. Network volume regions (`Storage` → Create Network Volume dialog)

Real path is `/user/storage/create` (`/storage` 404s directly — only
reachable via in-app nav). Opened the create dialog to read the region
list, then clicked Cancel — nothing was created.

**High-performance** (4):
- Canada — CA-MTL-4
- France — EU-FR-1
- Europe — EUR-NO-2
- United States — US-CA-2

**Standard** (15, "S3" tag = S3-compatible access):
- India — AP-IN-2 (S3)
- Japan — AP-JP-1
- Canada — CA-MTL-3
- Europe — EU-NL-1
- Europe — EU-RO-1 (S3)
- Europe — EUR-IS-1 (S3)
- Europe — EUR-IS-3
- Europe — EUR-IS-4
- Europe — EUR-NO-1 (S3)
- United States — US-IL-1 (S3)
- United States — US-MO-2 (S3)
- United States — US-NC-2 (S3)
- United States — US-NE-1 (S3)
- United States — US-TX-3
- United States — US-WA-1 (S3)

19 datacenters total, none matching the /deploy region list 1:1 (different
code set — this is the network-volume-specific set).

## 4. Volume creation at $0.00 balance

Not blocked by balance. The "Create Network Volume" entry button on
`/user/storage` is enabled at $0.00. On the creation form, the submit
button ("Create network volume") is disabled only while required fields
(data center, name, size) are empty — a plain form-validation gate, not a
balance gate. Filled in a data center (CA-MTL-4), a name
("survey-check-do-not-create") and size (10 GB) to test this, and the
button became enabled with no balance/insufficient-funds warning anywhere
on the page. The page shows "Balance: $-0.00" as plain text but that text
is not tied to the button's disabled state.

Did not click Create. Clicked Cancel instead — no volume exists on the
account from this survey.

## 5. ComfyUI template

Not under Templates (`/user/templates` is empty/"My Templates" — a
personal-templates page, no ComfyUI there). Found under the Hub
(`/hub` → search shows a "ComfyUI" group card, "Official Runpod ComfyUI
templates", tagged Official). The group contains two templates:

- **ComfyUI - CUDA 13** — publisher: Runpod (Official) — image:
  `runpod/comfyui:cuda13.0`
- **ComfyUI - CUDA 12.8** — publisher: Runpod (Official) — image:
  `runpod/comfyui:cuda12.8`

CUDA 13 variant detail page also lists: pre-installed custom nodes
(ComfyUI-Manager, ComfyUI-KJNodes, Civicomfy, ComfyUI-RunpodDirect), open
source at `github.com/runpod-workers/comfyui-base`, default 50 GB volume /
150 GB container disk, ports 8188 (ComfyUI), 8080 (FileBrowser), 8888
(JupyterLab), 22 (SSH).

## 6. Cheapest CPU instance (`/deploy` → CPU tab)

CPU tab has 3 categories (General Purpose, Compute-Optimized,
Memory-Optimized) each at two clock tiers (3 GHz / 5 GHz):

| Category | Tier | Cheapest | Specs |
|---|---|---|---|
| Compute-Optimized | 5 GHz | **$0.07/hr** | 2 vCPUs, 4 GB RAM |
| General Purpose | 3 GHz | $0.08/hr | 2 vCPUs, 8 GB RAM |
| Memory-Optimized | 5 GHz | $0.13/hr | 2 vCPUs, 16 GB RAM |

Overall cheapest: **Compute-Optimized, 5 GHz, 2 vCPUs, $0.07/hr, 4 GB RAM.**

Network volume mounting: the CPU deploy page has the same "Network volume"
filter dropdown that the GPU deploy page has, right next to the region
filter — CPU pods can mount a network volume, same as GPU pods.

## Notes on navigation

Direct deep links to nested routes (`/storage`, `/templates`) 404 or render
blank when hit via a fresh full navigation — the SPA only resolves them via
in-app client-side routing (clicking the sidebar link from an already-loaded
page like `/deploy`). Real paths behind the sidebar links: `/user/storage`,
`/user/templates`, `/hub`. `/deploy` itself loads fine on a fresh
navigation.
