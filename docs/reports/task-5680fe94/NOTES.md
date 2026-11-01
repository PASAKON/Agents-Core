# Plate Notes for Long EP1 (16:9)

## Summary of Plates Generated
- **Character Turnaround Sheets (4 plates):**
  - `NPC-hoarder`: Stocky, overconfident man hoarding bottled water in the convenience store.
  - `NPC-aunt`: Kind, stubborn elderly neighbour aunt sweeping floodwater on her porch.
  - `NPC-pet-neighbour`: Compassionate female neighbour sheltering her pet dog and cats.
  - `NPC-uncle`: Resigned elderly uncle on his porch with no vehicle or family refuge.
- **Scene Still Plates (35 plates):**
  - `L1-S01` to `L1-S35` following the approved script order for Long Episode 1.

---

## Plate Reuse Opportunities (Same Place / Same Pose / Shared Assets)

The following stills share identical locations, lighting, and camera positions, and can reuse a single base environment plate or share layered assets:

1. **Kitchen Water Preparation (`L1-S22` and `L1-S23`):**
   - **Location & Angle:** Townhouse ground-floor kitchen sink and stainless-steel prep counter under morning daylight.
   - **Reuse:** The background counter, sink, and cooking pot props are identical. `L1-S22` shows Khao Hom scrubbing the pots; `L1-S23` shows her filling the clean pots with water and covering them. A single background plate with modified character pose / water layer can serve both stills.

2. **Convenience Store Beverage Aisle (`L1-S13` and `L1-S14`):**
   - **Location & Angle:** Convenience store commercial beverage aisle with low water bottle shelving.
   - **Reuse:** The background grocery aisle can be rendered once. `L1-S13` places the hoarder and shopping cart in center-right; `L1-S14` retains the background aisle perspective while showing Khao Hom and an elderly shopper giving side-eye reactions.

3. **Ground Floor Hallway at Midnight (`L1-S31` and `L1-S32`):**
   - **Location & Angle:** Interior hallway between the front entrance and the bottom of the wooden staircase.
   - **Reuse:** Both stills share the same dark midnight atmosphere with flashlight illumination. `L1-S31` frames the creeping water across the floor tiles from the stairs; `L1-S32` frames the wall breaker box from the same dry staircase step.

4. **Bedroom Night Alert Sequence (`L1-S01` and `L1-S02`):**
   - **Location & Angle:** 3:00 a.m. dark bedroom with bedside table.
   - **Reuse:** The background bedroom environment and bedside table can share layout assets, transitioning from sleeping figure in background with glowing nightstand phone (`L1-S01`) to sitting upright holding phone (`L1-S02`).

5. **Front Door Water Level Checking (`L1-S07` and `L1-S08`):**
   - **Location & Angle:** Townhouse front doorstep looking out into the dim flooded soi at pre-dawn.
   - **Reuse:** `L1-S07` shows Khao Hom measuring water with a stick; `L1-S08` pulls back to a wider environmental shot of the quiet flooded street from the same vantage point.

6. **Daytime Soi Neighbour Encounters (`L1-S27`, `L1-S28`, `L1-S29`, `L1-S30`):**
   - **Location & Angle:** Flooded residential soi during continuous afternoon rain (shin-deep murky water, overcast light).
   - **Reuse:** Environmental background assets (water surface, street gates, cloudy sky palette) can be shared across all four plates for spatial continuity.

---

## Not checked / risk

1. **Dependency on NPC Character Sheet Generation:**
   - Stills `L1-S13` (`NPC-hoarder.png`), `L1-S28` (`NPC-pet-neighbour.png`), and `L1-S29` (`NPC-uncle.png`) require the NPC character sheets to be generated and saved to `/opt/MoonieXHQ/Work/khaohom-survival/long/ep01/stills/` prior to rendering those scene stills. If generation fails or paths are unavailable, prompts must temporarily fall back to attaching `C1.png` with text descriptions.
2. **AI Text Hallucination Suppression:**
   - Image generation diffusion models tend to synthesize pseudo-Thai or gibberish Latin text on phone screens, convenience store aisle signs, barcode packaging, banknotes, and electrical breaker labels. All prompts explicitly mandate blurred/blank screens and no text, but outputs will require manual inspection and spot-editing.
3. **Safe Zone Framing Boundaries (16:9):**
   - Top 12% (HUD stats), bottom 22% (subtitles), and right 14% (inventory slots) must remain free of character faces and critical focal points. AI generators may drift toward center-weighted framing or cut off margins. Validation against overlay masks is necessary before compositing into video timelines.
4. **Safety & Content Guidelines Compliance:**
   - The script addresses real emergency situations (rising floods, electrical shutoff, power grid blackout). Stills `L1-S21`, `L1-S32`, and `L1-S33` strictly adhere to non-violent, educational depictions (distant blue spark flash, dry wooden tool, breaker shutoff, no fire, no shock, no blood, no injury).
5. **Historical Sourced Fact Status:**
   - Fact citations for supply hoarding (T3a - 2011 Bangkok floods), cash dependency during blackout (T2a - Hurricane Maria), and Cell Broadcast alert formatting (T8a) remain classified as SNIPPET in `facts/FACTS-timeline.md` until verified against original web sources before audio production.
