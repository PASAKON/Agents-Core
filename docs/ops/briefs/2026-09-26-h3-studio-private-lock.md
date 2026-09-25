# Brief: H3 studio private lock (password), with per-owner API access

CEO order 2026-09-26, verbatim: "ล็อกข้อมูล 18+ ด้วยรหัส ไม่ให้ใครอ่านได้นอกจากนั้นที่หน้าเว็ป ฉันอ่านคนเดียว หน้าเว็ปจะแค่ local ที่เข้าได้ AI ไม่เข้ามา AI เข้าผ่าน API เท่านั้น อ่านได้เฉพาะข้อมูลของตัวเอง ข้อมูลที่ฉันสร้าง อ่านไม่ได้ รูปภาพก็เช่นกัน แต่ในหน้าเว็ปแสดงปกติทุกอย่าง"

Project: comfy-runpod-worker (ComfyRunpod, `studio/` Next 16 on :4100, reachable over the tailnet at 100.64.2.37:4100).
Security-sensitive: model_hint=claude. Depends on the `{}`-fill task (task-baee4ed0) being merged, because it touches the same files.

## Goal, in one line
Everything the CEO creates (the "private" owner) is readable ONLY in a browser on the Mac itself, after the CEO types a password. Every AI caller reaches the studio only through the API, with its own token, and sees only what that token created. That covers text, images, videos, renders and takes. Inside the unlocked web UI, everything works exactly as today.

## Principals
- **`ceo`**: the browser UI. Unlock: `POST /api/lock/unlock {password}`, accepted ONLY from a loopback remote address (127.0.0.1 / ::1). It sets an HttpOnly, SameSite=Strict, Secure-if-https session cookie.
  - Auto-lock after 30 min idle (configurable).
  - "Lock now" button in the Sidebar.
  - Server restart = locked.
- **API clients**: each has a named token.
  - Tokens are managed ONLY from the unlocked UI (Settings → API clients: create/revoke). The token is shown once. Only a hash is stored in `~/.mooniex/studio-clients.json` (0600).
  - Requests: `Authorization: Bearer <token>`. No token and no valid UI cookie → 401 on every data route.
  - A client sees and changes only rows with `owner == its client id`.
  - First client: `contabo-cto` (the ILAG film CTO).

## Ownership
- Every entity, group, queue item, take, shot, upload, render and generated image carries an `owner`. It is set on create from the caller: `ceo` for the UI, the client id for a token.
- **Migration of existing data** (one-time, runs at first password setup):
  - ILAG entities go to `contabo-cto`: group `ILAG TopView`, the ids in the Contabo ledger `h3-entities-created.json` plus Chief/Runner/Villagers2/Hut/Turning, and any entity in that group. So do their refs, and the queue items whose name starts `ILAG-`, and those items' renders.
  - **EVERYTHING else → `ceo`**. When in doubt, it is `ceo` (private). Print only counts, never names or contents.
- API list endpoints return only the caller's rows.
  - The shared queue must still show order: other owners' items appear as `{"id","status","owner":"other","position"}`, with no name, prompt, files or seconds.
  - Pod status/start/stop/stock stays shared.

## At-rest encryption (so a local agent with a shell cannot read `studio/data/` either)
- **Keys:**
  - A random 32-byte `ceoDataKey` is wrapped with a key derived from the password (scrypt, N≥2^15, random salt).
  - It is stored wrapped in `~/.mooniex/studio-lock.json` (0600) and held in server memory only while unlocked.
  - A recovery key (random, shown ONCE at setup, the CEO writes it down) also wraps the data key.
  - A forgotten password plus a lost recovery key = the data is gone; say so on the setup screen.
- **Fields:** ceo-owned text fields (prompts, promptSource, promptTemplate, names, notes, group names/descriptions of ceo groups, take names) are sealed with `ceoDataKey` (`enc:v2:` prefix). Non-ceo rows keep the existing file-key `secretbox` (`enc:v1:`).
- **Files:** ceo-owned files under `data/uploads/` and renders/takes/images are AES-256-GCM encrypted on disk (`<file>.enc`, header + nonce).
  - Decrypt in memory to serve `/api/uploads/...` to the unlocked UI, or to upload to the pod.
  - Renders downloaded from the pod are encrypted before they touch disk.
  - Stitching (ffmpeg) decrypts to a 0600 temp dir that is deleted in `finally`.
- **Locked server:** ceo queue items stay `pending`, with the reason "locked: unlock in the browser to render". Other owners' items render normally.
- **Thumbnails / posters / frame grabs** (`lastframe`, `videoframe`): same rule, ceo-owned output is encrypted.

## Web UI is local-only
- Middleware: any non-`/api` page route from a non-loopback address → 403 "The studio UI opens only on the Mac itself".
- `/api/*` from the tailnet works with a token only. UI cookies are never issued to non-loopback addresses.
- Locked UI shows only the unlock (or first-time setup) screen, then everything as today.

## Honest limits (put them in docs, not in marketing)
- An AI given control of the CEO's own unlocked browser tab sees what the CEO sees. The idle auto-lock plus "Lock now" button limit this.
- The text sent to OpenRouter by the `{}` filler is plain text by design (CEO accepted 2026-09-26).
- While unlocked, the data key sits in server memory.

## Breaking change for the Contabo CTO
- Its curl/python calls need `Authorization: Bearer`. The CTO (Mac) delivers the token out-of-band:
  - write it to a 0600 file on Contabo via scp;
  - never put it in git, letters or chat.
- Warn it before the merge.

## Tests (scripts/test_private_lock.py, fake data dir, own :4199, localhost)
- Setup + unlock + lock + idle auto-lock.
- 401 without auth.
- Token A cannot list, read, patch or delete token B's or ceo's entities, groups, queue rows, uploads, renders or takes. Each resource type is tried directly by id, as well as via list.
- The queue shows other owners' rows redacted.
- A non-loopback page request → 403: simulate with a header the middleware trusts ONLY in test mode, or bind a second interface.
- Raw files on disk:
  - ceo text fields start `enc:v2:`;
  - ceo upload files are not valid PNG/MP4 bytes;
  - after unlock the UI endpoint serves the original bytes (sha256 equal).
- Locked server: a ceo queue item stays pending; a contabo item runs (the fake pod is fine).
- Recovery key unlock works; the wrong password is rate-limited (5 per min).
- Migration on a fake copy: the counts split correctly; nothing is left unencrypted for ceo.
- `test_entity_groups.py`, `test_groups_api.py` and `test_prompt_fill.py` still pass (with a token or cookie).
- `tsc` clean.

## Hard rules for the worker
- Never read the MAIN tree's `studio/data/`. Build and test on fake data only.
- Never call :4100. Never open images.
- The CTO runs the real migration himself after the merge, with the CEO present to set the password.

## Addendum 2026-09-26: Touch ID / passkey (CEO: "Can use passkey or touch ID ... Apple only -> make sure you can restore if it crack")
- **The Mac:** MacBook Pro M1, macOS 14.3.1 (Sonoma), Touch ID enrolled (`bioutil`: biometrics on).
- **Unlock methods, in order:**
  1. **Touch ID (primary).**
  2. **Password (backup).**
  3. **Recovery key** (shown once at setup).

  Each method wraps the same `ceoDataKey` independently, so losing one never loses the data.
- **Touch ID mechanism: verify on THIS Mac before building; do not assume.**
  - (a) A WebAuthn passkey with the **PRF extension**: the PRF output derives the wrapping key. On localhost, a secure context, in the CEO's Chrome and Safari versions. PRF on platform passkeys may need macOS 15+, so test it with a tiny local page first.
  - (b) If PRF is unavailable: a small Swift helper using LocalAuthentication (Touch ID prompt on the Mac) that releases the wrapping key from the macOS Keychain. The server calls it, and the CEO sees the system Touch ID sheet.
  - Report which one works with evidence, and why. A Touch ID prompt the CEO did not start is visible to him; note that as the tamper signal.
- **Restore ("if it cracks"):**
  - Everything needed to decrypt = `~/.mooniex/studio-lock.json` (wrapped keys only; useless without the password, Touch ID or the recovery key) + `studio/data/`.
  - Add both to the Mac machine-contract backup as IRREPLACEABLE-encrypted, and to the Drive `BACKUP/` flow. They are safe to upload because they are ciphertext.
  - Ship `scripts/lock_restore_drill.py`: on a copy, re-derive with the recovery key, unwrap, decrypt one ceo field and one file, compare sha256. The CEO runs it once after setup.
- **Passkeys and iCloud Keychain:** a Touch ID passkey stored in iCloud Keychain survives a Mac reinstall. A Keychain-helper secret does NOT (it is device-bound), so option (b) relies on the password or the recovery key for restore. Say so on the setup screen.
