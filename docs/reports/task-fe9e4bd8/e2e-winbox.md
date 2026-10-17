# E2E-W: a Contabo C-level starts a Project Head on winbox (HostSpawn, PH #73cfec1c)

Code: Agents-Core #387 (merge 12f8e422), winbox clone at 12f8e422, flag ORG_PH_ROLES on.
Route: `python -m tools.spawn_ph mesh --host winbox --project <P>` on Contabo → mesh `spawn_ph` verb
→ `spawn_from_mesh` on winbox → one-shot interactive scheduled task (desktop session).

## Preconditions (16 Oct 2026)
- Dispatch key installed by the CEO's card RUN-20261016-0311-eb8f; #238 closed.
- `mesh.dispatch("winbox","probe")` → ok, version 12f8e422, no probe errors.
- Refused as expected: an injected verb (`probe; whoami`), a malformed owner id, a project name with `;`,
  and a Project Head as the caller ("only a C-level session starts a Project Head").

## Run 1: CEO hold (03:20Z) — refused, correct
- Caller: CTO Main (cto-c34459eb). Dry run: `{"host": "winbox", "verb": "spawn_ph", "args": ["cto", "c34459eb", "HostSpawnE2E"], "dry_run": true}`
- Real run: `{"ok": false, "verb": "spawn_ph", "error": "the CEO is using this PC (CEO hold, windows/pc_lease.py ceo-on); no window opens until he presses his release button"}`
- Nothing opened on the CEO's desktop. The CEO-hold gate works over the mesh.

## Run 2: after the CEO releases the PC
- 18 Oct 03:08 TH, after the CEO's release (CEO: "window relese done", dota2.exe left running): caller CTO Main
  (cto-c34459eb), `python -m tools.spawn_ph mesh --host winbox --project HostSpawnE2E`.
- Result: `{"ok": true, "verb": "spawn_ph", "result": {"session_id": "ba3f3fe1", "project": "HostSpawnE2E", "owner": "cto-c34459eb", "via": "schtask"}}`
- `live-sessions.sh --all`: `WINDOWS Project Head (CTO) #ba3f3fe1` on winbox (name lacks the host emoji: follow-up).
- Round trip (SendMessage → reply): cwd C:\Users\passg\mooniex\repo\MoonieX-Agents · role Project Head (CTO)
  #ba3f3fe1, HostSpawnE2E, reports to cto-c34459eb · 115 skills (~82 org) · org MCP up, LungNote MCP failed to connect.
- PASS. Follow-ups: host emoji in the winbox name; LungNote MCP on winbox.
