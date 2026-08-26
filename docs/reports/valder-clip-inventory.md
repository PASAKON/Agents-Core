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

## Pre-flight on the ten uncovered scenes — 2026-08-26 15:55

Checked offline, no browser needed. Both structural failure classes are ruled
out for S4A S4 S4B S4C S5 S5B S6 S7A S7B S-MU:

- **Element ceiling** — every scene declares 9 or fewer (max is 8, in s4b / s6 /
  s7a). Ten elements fails with a generic error, so this was worth checking
  before a worker discovered it mid-fire.
- **Tag resolution** — all 26 distinct `@project_valder_*` tags used across the
  ten scenes have a real plate on disk. Zero typos. (This is the class that bit
  us once already: Elements use US `neighbor`, the prompts had said `neighbour`,
  and a plain tag that does not match exactly silently fails to bind.)

If one of these scenes now fails to fire, **the cause is runtime, not the prompt
file** — protected-content triangle, Lexical desync, or the render queue. Do not
spend a cycle re-auditing element counts or tag spelling.

Recompute with:

```
D=docs/prompts/valder
for s in s4a s4 s4b s4c s5 s5b s6 s7a s7b smu; do
  echo "$s $(grep -oE '@project_valder_[a-z0-9_]+' $D/$s-multicut.txt | sort -u | wc -l)"
done
ls docs/plates/*.webp | xargs -n1 basename | sed 's/^project_valder_//; s/\.webp$//' | sort -u > /tmp/have.txt
```
