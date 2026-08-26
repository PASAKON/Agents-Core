# Valder — clip inventory (authoritative)

Generated 2026-08-26 14:45 by CTO from the `| Scene | Take | Clip asset id | Status |`
tables in every wave report. **Video clips only** — plate/element ids excluded.

## Why this file exists

Raw `grep` for UUIDs across `docs/` returns ~121 ids, but the overwhelming
majority are **plate (still image) ids**, not video clips. Counting those as
clips overstates coverage by roughly 2x, and it did: earlier CTO cycles
reported "31 clips" when the real figure was 16. Count only rows from a table
whose header says `Clip asset id`.

Handoff reports carry the previous wave's table forward verbatim, so raw row
count (21) also overstates. Dedupe by id.

## Coverage as of 2026-08-26 14:45

| Scene | Takes | Status |
|---|---|---|
| S1 | 6 | covered |
| S1B | 4 | covered (1 still rendering) |
| S-V | 3 | covered |
| S2 | 2 | covered — canonical + variant |
| S3 | 1 | covered, thin |
| S4A | 0 | **no footage** |
| S4 | 0 | **no footage** |
| S4B | 0 | **no footage** |
| S4C | 0 | **no footage** |
| S5 | 0 | **no footage** |
| S5B | 0 | **no footage** |
| S6 | 0 | **no footage** |
| S7A | 0 | **no footage** |
| S7B | 0 | **no footage** |
| S-MU | 0 | **no footage** — staged in composer, not yet fired |

**16 clips across 5 of 15 scenes.** Ten scenes have never been fired.

## What this means for the 3 Sep deadline

At the current out-of-window render rate (~35-50 min/clip, one slot,
account-wide), one take of each remaining scene is **~7 hours minimum**. That
is achievable overnight only if the Unlimited slot never idles — which is why
the CEO's standing order exists.

Priority if time runs short: fire ONE take of each uncovered scene before any
second take of a covered one. A film with thin coverage everywhere can be cut;
a film missing ten scenes cannot.

## Regenerating this file

```
grep -hE '^\|[^|]+\|[^|]+\|[[:space:]]*`?[0-9a-f]{8}-' docs/reports/valder-video-wave*.md docs/reports/valder-s*.md docs/reports/valder-final-two.md \
  | awk -F'|' '{gsub(/[` ]/,"",$2); gsub(/[` ]/,"",$4); if($4 ~ /^[0-9a-f]{8}-/) print $2"\t"$4}' | sort -u
```
