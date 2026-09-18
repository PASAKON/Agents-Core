# Drive archive gate — new row: Cookie Run Colab training packs

**Approved by the CEO in chat, 2026-09-18**, in answer to a request that named
this exact destination and size: *"เครื่องว่างแล้วลุยเลย"*.

⚠️ **This row still needs mirroring into `org:playbooks/drive-archive-gate.md`
from the Mac.** Contabo's wiki is an rsync snapshot with no `.git` — a write
there is silently overwritten by the next sync (CLAUDE.md), so the approval is
recorded here instead. Whoever next edits the wiki on the Mac should paste the
table row below into it and delete this note.

## The row

| Source on winbox | Destination in Drive | Note |
|---|---|---|
| `Documents/CookieRunScript/colab_pack/*.npz` — training shards packed by `windows/cookierun_pack_for_colab.py` | `BACKUP/CookieRun Backup/colab_packs/` | CEO-approved in chat 2026-09-18. **Derived data, not an archive** — every shard is re-creatable from `play_rec`, which is already backed up under its own row. This exists only to get bytes to Colab, which cannot reach winbox. Upload from the box with rclone (`--transfers 1 --drive-chunk-size 64M` while the bot plays), verify `rclone check --one-way`, log to `~/.claude/logs/drive-archive.log`. Safe to delete from Drive once a training run has consumed it; deleting it costs a repack, not data. |

## Why a new row rather than reusing `CookieRun Backup/play_rec`

That row is an **archive**: one tar per take, kept because the frames are the
only copy. This is the opposite — a transfer medium, decoded and resized to the
model's 192x80, worthless the moment the model has read it. Filing throwaway
working data into an archive folder would make the archive's retention rules
mean two different things at once.

## What was uploaded

- 799,300 frames, 0 skipped, **47 shards, 11.45 GB**
- Content per shard: `x` (uint8 frames, 80x192), `y` (jump/slide labels),
  `t` (timestamps)
- Timestamps are packed deliberately: the trainer picks its 5-frame stack by
  TIME (+-110/55 ms), not by frame index, because our recorder runs at 18.2 fps
  against a claimed 24. Shipping the frames without the times would make that
  choice unreproducible on the far side.
