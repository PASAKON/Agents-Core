# REPORT task-9ba3e449

## Summary

Implemented the TikTok Content Posting API v2 & Login Kit v2 CLI (`tools/tiktok_post.py`), unit test suite (`tests/test_tiktok_post.py`), `.gitignore` exclusions for `state/tiktok/`, and the MoonieX-Console callback route specification (`docs/reports/task-9ba3e449/console-callback.patch.md`) for Order `O-20261119-0006-c311`.

## Files changed

- `.gitignore`: Added `state/tiktok/` and `state/tiktok/tokens-*.json` so OAuth pending states, callback codes, and user tokens are never committed.
- `tools/tiktok_post.py`:
  1. `auth-url --account black_liquidity`: Builds and prints the TikTok Login Kit v2 authorize URL (`https://www.tiktok.com/v2/auth/authorize/`) with `client_key` (from `TIKTOK_CLIENT_KEY`), `response_type=code`, `scope=user.info.basic,video.upload,video.publish`, `redirect_uri=https://terminal.mooniex.com/tiktok/callback`, and a random URL-safe `state` (`[A-Za-z0-9_-]{16,64}`). Saves `state/tiktok/pending-<state>.json` with `0600` permissions. Per TikTok's official web Login Kit (`doc/login-kit-web`) and token docs (`doc/oauth-user-access-token-management`), `code_verifier` (PKCE) is marked *"Required for mobile and desktop apps"* and is omitted for web confidential-client flows.
  2. `callback-file --state <s>` & `exchange --state <s>`: Waits up to 10 minutes (`600s`) for `/opt/MoonieXHQ/Agents/Core/state/tiktok/callback-<state>.json` (`{"state","code"}`), exchanges the authorization code via `POST https://open.tiktokapis.com/v2/oauth/token/` (`application/x-www-form-urlencoded` with `client_key`, `client_secret`, `code`, `grant_type=authorization_code`, `redirect_uri`), stores `access_token`, `refresh_token`, `open_id`, and `expiry` (`expires_in`, `expires_at`, `refresh_expires_in`, `refresh_expires_at`) in `state/tiktok/tokens-<account>.json` (`0600`), and deletes `callback-<state>.json` in a `finally` block.
  3. `refresh --account` & `creator-info --account`:
     - `refresh`: POSTs `grant_type=refresh_token` to `https://open.tiktokapis.com/v2/oauth/token/` and persists the rotated `refresh_token` and new `access_token` (`0600`).
     - `creator-info`: POSTs `{}` to `https://open.tiktokapis.com/v2/post/publish/creator_info/query/` and prints `creator_nickname`, `privacy_level_options`, and `max_video_post_duration_sec`.
  4. `post --account --file <mp4> --caption "..." [--draft]`:
     - Computes chunks per TikTok's Media Transfer Guide (`< 5 MiB` -> single chunk of `video_size`; `>= 5 MiB` -> `total_chunk_count = floor(video_size / chunk_size)` with trailing remainder merged into the final chunk up to `128 MiB`).
     - Default Direct Post calls `POST https://open.tiktokapis.com/v2/post/publish/video/init/` with `post_info` (`title`, `privacy_level: "SELF_ONLY"`, `disable_comment`, `disable_duet`, `disable_stitch`) and `source_info` (`source: "FILE_UPLOAD"`, `video_size`, `chunk_size`, `total_chunk_count`).
     - `--draft` calls `POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/` with `source_info`.
     - Uploads each byte slice sequentially via `PUT <upload_url>` with `Content-Type: video/mp4`, `Content-Length`, and `Content-Range: bytes <start>-<end>/<video_size>`.
     - Polls `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/` with `{"publish_id": ...}` until `PUBLISH_COMPLETE` (or `SEND_TO_USER_INBOX` in `--draft` mode) or `FAILED`, printing only `publish_id` and final `status`.
     - Scrubs `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, authorization `code`, `access_token`, and `refresh_token` from any error output.
- `tests/test_tiktok_post.py`: Unit tests with the HTTP layer completely mocked covering authorize URL generation, `0600` permissions on `pending-<state>.json` and `tokens-<account>.json`, callback file polling and deletion, refresh token rotation, `creator_info/query` output, chunk calculation math, Direct Post and `--draft` chunked PUT upload, status polling (`PROCESSING_UPLOAD` -> `SEND_TO_AUDIT` -> `PUBLISH_COMPLETE` and `FAILED`), and secret redaction on stdout/stderr.
- `docs/reports/task-9ba3e449/console-callback.patch.md`: Standalone patch description and implementation for CTO to apply to `MoonieX-Console` for public `GET /tiktok/callback`.

## Validation performed

- Followed the AGY file-only worker contract (no shell execution of `python`/`pytest` inside the print-mode worker); verified all imports, function signatures, mock hooks, and assertions by line-by-line inspection so `python -m pytest tests/test_tiktok_post.py` runs cleanly with `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` during review.
- Verified official TikTok v2 endpoint URLs and exact JSON/form field names against `developers.tiktok.com` documentation (`login-kit-web`, `oauth-user-access-token-management`, `content-posting-api-reference-get-creator-info`, `content-posting-api-reference-direct-post`, `content-posting-api-reference-upload-video`, `content-posting-api-media-transfer-guide`, `content-posting-api-reference-get-upload-status`).

## Not checked / risk

- **Shell pytest execution deferred to review**: Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process"), `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_tiktok_post.py` was not executed in a shell inside this session.
- **No live TikTok API call**: Per the task brief ("Do not call TikTok for real"), no live OAuth flow or video upload against TikTok's servers was executed.
- **Console callback route deployment**: `docs/reports/task-9ba3e449/console-callback.patch.md` must be applied to `MoonieX-Console` and the service reloaded by the CTO before running a live browser OAuth callback to `https://terminal.mooniex.com/tiktok/callback`.
- **Unaudited sandbox app constraints**: Until "MoonieX Poster" passes TikTok audit, Direct Post only allows `privacy_level="SELF_ONLY"` and the target TikTok account (`@black_liquidity`) must be added as a Sandbox Target User in the TikTok Developer Portal.

## Blockers

- (none)

## Skill learning

- (none)
