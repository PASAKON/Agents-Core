# Flow shot runner — usage

Zero-token shooting for «บัญชี», per `docs/ops/flow-operator-design.md`. See
`docs/scripts/BANCHI-SHOOT-BRIEF.md` and the `google-flow-ops` skill for the
click path this script encodes.

## One-time setup (the CEO's part — a worker cannot do this)

```
bash scripts/flow/launch-chrome-debug.sh
```

Log into Google in that window **once**, open `flow.google.com`, open the
«บัญชี» project tab. Leave that Chrome window running. Port 9223 — never the
CEO's main Chrome, never Higgsfield's 9222.

## The four commands

```
python3 tools/flow_ledger.py init  <sheet.md> <ledger.tsv>       # or let `run`/`pull` do this for you
python3 tools/flow_shoot.py status --ledger <ledger.tsv>
python3 tools/flow_shoot.py run    --sheet <sheet.md> --ledger <ledger.tsv> \
    --dest <download-folder> --credit-cap <N> [--only 37-46] [--dry-run] \
    [--resolution {720p,360p}] [--force-duration N]
python3 tools/flow_shoot.py pull   --sheet <sheet.md> --ledger <ledger.tsv> \
    --dest <download-folder> [--only 53-58]
```

- **`status`** — one-screen count per status, and the next `todo` shot.
- **`run`** — shoots every row not already `verified`/`refused`. Always start
  with `--dry-run`: it does everything up to reading the credit estimate for
  the first `todo` row and stops before Submit — zero credits, and it is how
  you confirm the selectors still match the live UI before spending anything.
  `--credit-cap` is the only money safety in the loop; the run stops the
  moment the next shot would cross it, with a `CAP REACHED` line, not a crash.
  `--resolution {720p,360p}` (default `720p`) sets the composer's resolution
  facet and reads it back like every other setting. `--force-duration N` is
  **proof shots only**: it overrides the sheet's per-shot duration for both
  the duration setting and `verify_clip`'s tolerance, and the runner logs the
  override loudly at the top of the run.
- **`pull`** — download-only. For clips already generated in Flow (found by
  the shot's own dialogue line, not the prompt text — see google-flow-ops on
  why), download and verify without submitting anything new.
- **`--only 37-46`** — restrict either command to a shot-number range/list
  (`37-46`, `37,40,52`, `37-40,52`).

## What each status means

`todo` → `submitted` → `generated` → `downloaded` → `verified` is the happy
path. Off that path:

- **`refused`** — Google's policy card, twice on the byte-identical prompt
  (the runner already re-fires once, refunded, before giving up). `note`
  carries the card text verbatim. This needs a human rewrite decision, not a
  retry — see google-flow-ops "How to work when a shot is refused".
- **`needs_model`** — the script hit something it cannot decide: a chip that
  never attached after 5 retries, a prompt that didn't paste byte-for-byte
  after one retry, or a settings panel that didn't read back as expected.
  `note` says which. Fix the one thing by hand (or open a small fresh-context
  worker task pointed at just that row), then set `status` back to `todo` and
  re-run — the row is retried, nothing else is.
- **`failed`** — a timeout waiting for the result, or a downloaded clip that
  failed duration/audio verification. The file (if any) is kept with a
  `bad-` prefix so nothing is silently lost; `note` says why.

## A crash

Re-run the same `run`/`pull` command. The ledger is the memory: every write
is atomic (temp file + rename), a `verified` row is never re-fired, and
anything mid-flight when the process died is still whatever status it last
reached — re-running picks it up from there, not from the beginning.
