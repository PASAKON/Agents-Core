# TraderMindset — Prompt Learning-Loop Metrics

Owner: `prompt_engineer`. Reported **every round** in the batch report so we can
prove the prompt is measurably getting better (CEO directive 2026-06-11:
"prompt เก่งขึ้นวัดผลได้"). Source of truth for outcomes is the claudeflow table
`claudeflow_tm_items` (one row per generated item; see the migration
`supabase/migrations/202606111400__claudeflow_tm_approvals.sql`).

`claudeflow_tm_items` columns used here: `round`, `slug`, `theme`, `status`
(`generated|emailed|approved|rejected|queued|skipped`), `reject_reason`,
`approved_at`, `created_at`, `updated_at`.

Run queries with the claudeflow service key (read-only is enough). The reject
feed for category analysis is the existing `scripts/tm-export-lessons.js`
(`[{slug, reason, date}]`); categories are derived with the same map as
`scripts/tm_prompt_evolve.py:categorize()`.

---

## The 4 metrics (per round)

### 1. approve-rate  *(higher = better)*
Share of **decided** items the CEO approved.

    approve_rate(round) = approved / (approved + rejected)

`queued` counts as approved (an approved item that already moved on); `skipped`
and still-`emailed` (undecided) are excluded from the denominator.

```sql
-- approve-rate per round
select round,
       count(*) filter (where status in ('approved','queued'))                      as approved,
       count(*) filter (where status = 'rejected')                                  as rejected,
       round( count(*) filter (where status in ('approved','queued'))::numeric
              / nullif(count(*) filter (where status in ('approved','queued','rejected')), 0), 3)
                                                                                     as approve_rate
from claudeflow_tm_items
group by round
order by round;
```

Collected by: prompt_engineer from the query above at end of each round.

### 2. repeat-reject-category  *(target = 0)*
How many reject **categories** in this round also caused a reject in an EARLIER
round — i.e. a mistake the loop should already have fixed. This is the headline
"are we still making the same mistakes?" number.

Procedure (not pure SQL — needs the categorizer):
1. `node scripts/tm-export-lessons.js --out lessons.json` (claudeflow).
2. Map each lesson to a category with `tm_prompt_evolve.categorize(reason)`.
3. `repeat-reject-category = | categories(round N) ∩ categories(rounds < N) |`.

A category that recurs **≥2 rounds** is ALSO the trigger to stop editing the
prompt and PROMOTE TO VALIDATOR (code it in `tm_checks.py`) — see
`tm_prompt_evolve.py`. Helper to compute the category counts for a round:

```bash
# rounds' reject reasons -> category tallies (paste lessons.json paths)
python - <<'PY'
import json, sys; sys.path.insert(0, "scripts")
from tm_prompt_evolve import categorize
for f in ["round_prev.json", "round_curr.json"]:
    cats = {}
    for l in json.load(open(f)):
        cats[categorize(l["reason"])] = cats.get(categorize(l["reason"]), 0) + 1
    print(f, cats)
PY
```

Collected by: prompt_engineer (export → categorize → intersect with history).

### 3. regen-count  *(lower = better)*
Total poster regeneration attempts in the round. A baked Thai hero word that
renders garbled is re-generated up to 2× per slot before the font-composite
fallback (wiki §3.5). High regen = the poster prompt is unstable.

This is a GENERATION-side number, not in `claudeflow_tm_items`. It is emitted by
the generator into the round's `meta.json` (add a `regen` count per item) and
summed for the round; until then the operator records attempts from the run log.

    regen_count(round) = Σ poster regen attempts over the round's items

Collected by: prompt_engineer from the generator run (`output/trader-mindset/round-NNN/meta.json`).

### 4. time-to-queue-full  *(lower = better)*
Wall-clock from a round being generated to the approval queue holding enough
`approved`+`queued` items to cover the ~3-week (≈9-slot) posting horizon — i.e.
how long the human-approval loop takes to refill the pipe.

```sql
-- per round: first generated -> last approval that filled the queue
select round,
       min(created_at)                                                  as generated_at,
       max(approved_at) filter (where status in ('approved','queued'))  as queue_filled_at,
       max(approved_at) filter (where status in ('approved','queued'))
         - min(created_at)                                              as time_to_queue_full
from claudeflow_tm_items
group by round
order by round;
```

Collected by: prompt_engineer from the query above (report in hours).

---

## "เก่งขึ้น" (improving) — the bar

A round N+1 counts as an improvement over round N iff BOTH hold:

> **approve-rate(N+1) ≥ approve-rate(N)**  AND  **repeat-reject-category(N+1) = 0**

regen-count and time-to-queue-full are secondary health signals — watch the
trend, but they do not by themselves gate "improving". If approve-rate drops or
any reject category repeats, the loop has NOT improved that round: investigate,
and if a category has now repeated ≥2 rounds, promote it to a code validator
instead of another prompt tweak.

## Round report block (paste into the batch report)

```
TraderMindset round NNN — prompt metrics
  approve-rate          : 0.xx   (prev 0.xx)        [≥ prev? Y/N]
  repeat-reject-category: 0                          [target 0? Y/N]
  regen-count           : N
  time-to-queue-full    : Nh
  improving vs prev?    : YES/NO
  prompt versions       : caption=vX poster=vY (registry.active)
  evolve draft proposed : caption-vX+1 (eval verdict: WIN/LOSE/—)
```
