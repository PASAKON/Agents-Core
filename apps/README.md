# `apps/`

User-facing MoonieX applications. Applications consume stable Core APIs and must
not own orchestration state or directly become the source of truth.

- `desktop/` is the cross-platform Tauri application for macOS and Windows.
- Closing an app must not terminate MoonieX Core or remote Nodes.
- Provider credentials stay in Core/Node secret storage, never in frontend code.
