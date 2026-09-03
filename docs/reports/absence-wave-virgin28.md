# The 28 virgin blocks — generation waves (CEO-approved 2026-08-31 ~01:30)

Prompts: v2 (both 2026-08-21 forever-lines restored, commit e7bbdb9, synced to
main + operator worktree, md5-verified). Fire from the v2 files only.

**Standing rules for every fire:** Seedance 2.5 / Unlimited only (never 2.0 —
72cr live price + $140/day subscription page confirmed 01:18). Before EVERY
Generate: verify all six spec fields — duration per the scene header below ·
720p · Seedance 2.5 · High · 1/4 · Sound ON — plus the zero-digit strike.
Duration is per-scene here, NOT always 20s. Measure every result on landing.

## Wave I — the 5-second inserts (8 clips · duration field: 5s)
P1, P2, P3 (plaque hands, s-price-inserts.txt) · D1–D5 (Dupe reactions,
s-dupe-inserts.txt). Note: P-series has NO PEOPLE (hands only) — if the
scanner or the model fights the new "every single person…" line in a
people-free frame, file the take and report; do not rewrite on your own.

## Wave II — doll's house (4 clips · 10–12s per header)
DH1–DH4 (s-dollhouse.txt). Attach the matching previz as @Video 1:
DH1..DH4-Render.MP4 in docs/ (operator worktree has them). @loc_dollhouse
binds the frame; figures small, camera locked, black void clean.

## Wave III — editor pack (9 clips · duration per header)
X1 establishing · X2 room-tone bed 20s · X3 red door · X4 row reverse ·
X5 painting macro push · X6 helicopter · X7 broadcast 15s · X8a/X8b PA 8s.
(s-extras.txt)

## Wave IV — story stragglers (3 clips · 20s)
S1C the cart detail · S1F the hands (s1-angles.txt) · S18b already in the
take-2 queue ahead of this list.

## Blocked — rewrite done, DO NOT fire (4 blocks)
S6, S6b (need the 20M wall plate variant — unverified) · S11 (needs the 100M
wall-POV plate variant) · S10b (copyright scanner rejected twice on identical
content, GH #125 — a third slot is waste until the CEO rules on it).

Order: finish the take-2 queue first (S18b → S14t2 → S16t2 → S18at2), then
Wave I → II → III → IV. File every take to Drive pass or fail; report each
with its exact prompt; CTO reviews frames per the iron rule.

## Standing exception — the gold V on char_woman (CEO, 2026-09-02)

**Do not flag a take because Collector A wears a gold V pin.** The V is baked
into the `@project_absence_char_woman` plate and the CEO ruled it acceptable as
it is, on the grounds that you do not see it unless you are looking for it. No
re-plate, no reshoot; takes already filed keep their status. Full reasoning at
the end of `absence-collectorA-goldV-plate.md`.

Keep the no-V negative lines in every prompt — they are the reason the V never
spread to any other character. But if it appears on **her** anyway, that is not
a defect and the take is a keeper.

**Her only.** A gold V on any other visitor is still a real defect and still
gets flagged. The registrar's V is correct by design and never was one.

---

## Filing convention for the repair phase (CEO 2026-09-03)

The film has moved out of the shoot-everything phase. Draft 1 is cut and the
story is close to complete, so from here generation is **ฉากซ่อม** — repairs and
additions that sharpen scenes that already exist.

**Repair takes go into a `Fix-1` folder inside the scene's own folder**, not
alongside the original takes:

```
All Scene/<SCENE>/                      ← the original takes stay here
All Scene/<SCENE>/Fix-1/                ← repair takes for that scene
```

Same file-naming rules as always — block id, take number, verdict, duration,
resolution. Same never-discard rule: a failed repair take is filed in `Fix-1`
with its verdict, not deleted.

Why the separation: the editor has a cut built from the originals. A repair that
lands in the same folder makes it ambiguous which file the cut refers to, and
the first thing anyone will need to answer is "is the version in Draft 1 still
the version we are using". Keeping repairs in their own folder answers that by
looking, not by comparing timestamps.

A later repair round becomes `Fix-2`, and so on.
