# Steward ingestion patch (not deployed)

`disk-hub-steward.patch` is a unified diff against the read-only snapshot of
`/opt/disk-monitor/disk-hub.py` in `tests/fixtures/disk_hub/disk-hub.py`.
The production file has not been changed and no service has been restarted.

The patch accepts an optional `steward` object with exactly `band` (nonempty
string, at most 10 characters), `tick_at` (ISO datetime containing T, at most
40 characters), and `actions` (nonnegative integer, excluding booleans).
Invalid objects receive HTTP 400 before storage. Valid reports persist the
object in `<host>.json` and the supplied band in that report's history row.
Ordinary volume-only pushes preserve the last stored steward object, so the
existing frequent pushers cannot erase the last tick. Old history rows and
volume-only requests otherwise retain their existing shape.

For deployment by the service owner: compare the current production source
with the fixture and review `patch --dry-run -p1` in the hub directory before
applying the diff through the normal deployment process. This task does not
authorize applying it or restarting the service.

The sender counts attempted maintenance CLI actions (including orphan closes),
excluding skipped/daily-already-complete actions, letters, and the hub POST.
HTTP failures are recorded locally and do not change the tick exit status.
Mac/Contabo env paths are in the machine contract. The winbox path is null
until its pusher configuration can be identified; its hub step is skipped.
