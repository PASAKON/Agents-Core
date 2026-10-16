# ADR 00XX — Contabo is the Main node; GitHub is the file source; peers pull

- **Date:** 2026-10-16
- **Owner:** OrgMesh PH
- **Destination:** Agents-Rules `decisions/`; PH copies this draft there and assigns its number.

## Status

Accepted, CEO plan approval 2026-10-16. This file is the draft for filing in
Agents-Rules; Mac SSH dispatch remains planned, ADR 0034.

## Context

Bare-launched winbox PHs had no org kit. Contabo wikis were stale rsync copies
from the Mac. Hosts could start sessions with different rules, wikis and memory.
The org needs one centre for work and one file source for every host.

## Decision

1. **Contabo is the Main node.** It owns the Postgres hub, Run cards, dispatcher
   and `tools/mesh_check.py` collector. Orders go over ssh through
   `node_dispatch` with the `org_dispatch` key.
2. **GitHub is the file source.** Agents-Rules, Agents-Wikis and Agents-Memory
   are plain git checkouts on Contabo, Mac and winbox. Every launcher pulls at
   session start: `tools/kit_sync.py pull` for wiki roots (PR #396),
   `tools/memory_sync.py pull` for memory. Never rsync these repos from the Mac.
3. **Peers pull files and take orders.** Contabo checkouts live at
   `/opt/MoonieXHQ/Agents/{Rules,Wikis,Memory}`. winbox checkouts live at
   `%USERPROFILE%\mooniex\repo\Agents-{Rules,Wikis,Memory}`; Wikis uses a
   read-only deploy key and Memory a read-write deploy key. Edits on any host
   travel by commit + push to the relevant repo, with write-authorized access.
4. **Mac dispatch is planned, ADR 0034.** The Mac will join as an ssh dispatch
   target with a key-only sshd drop-in and forced command `node_dispatch`.
   This step is pending, not done.

## Consequences

- Work has one centre on Contabo; dispatch and collection depend on that host.
- File updates reach peers through GitHub at session start. No rsync copy can
  overwrite local edits; changes must be committed and pushed to be shared.
- The winbox Wikis deploy key can pull but cannot publish edits.
- Mac SSH dispatch must not be counted as ready until ADR 0034 is applied.

## How it is checked

Run on Contabo:

```bash
bash scripts/hub/org-python.sh -m tools.mesh_check --expect w5
```

The KIT level (PR #397) checks that every host runs the same org kit. Contabo
collects the results; a missing or stale kit is a failed check, not a reason to
restore rsync.
