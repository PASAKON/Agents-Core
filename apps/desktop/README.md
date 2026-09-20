# MoonieX Desktop

Cross-platform control surface for MoonieX Core and MoonieX Nodes. The frontend is
React/TypeScript; Tauri provides a lightweight native shell for macOS and Windows.

## Development

```bash
npm install
npm run dev          # browser UI only
npm run tauri dev    # native app; requires Rust + platform prerequisites
npm run build        # typecheck + production frontend
```

The first version uses a local demo adapter so UX work can proceed independently
of Core. Replace `src/data/demo.ts` with a Core API adapter once its event contract
is approved.

## Platform builds

- Windows: build on Windows with Rust and Microsoft C++ Build Tools.
- macOS M1: build on Apple Silicon macOS with Rust and Xcode Command Line Tools.

macOS signing/notarization and Windows code signing require owner certificates and
are intentionally outside the source tree.
