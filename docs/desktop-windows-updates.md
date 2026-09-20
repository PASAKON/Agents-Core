# MoonieX Desktop: Windows Update Contract

MoonieX Desktop uses Tauri's signed updater and GitHub Releases. Users install the
application once. A later release is downloaded, signature-verified, installed in
passive mode, and the Windows app restarts into the new version.

## Safety properties

- Every updater artifact is signed with an Ed25519 private key.
- The private key is never committed; GitHub Actions receives it from repository secrets.
- The public key is compiled into the release and rejects altered packages.
- A release is created as a draft, so it can be installed and validated before publishing.
- App updates do not replace MoonieX Core data, Node state, rooms, or user projects.
- Active remote work continues because Core and Nodes are independent of the UI process.

## Required GitHub secrets

| Secret | Purpose |
|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | Signs Windows updater artifacts |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Unlocks the signing key during CI |

The public key is safe to distribute and is committed in `tauri.conf.json`. Only the
private key and its password are secrets.

Generate the production key once on a trusted owner machine. Keep an encrypted backup;
losing it means already-installed applications cannot trust future update packages.

## Release process

1. Update the version in `apps/desktop/package.json` and
   `apps/desktop/src-tauri/tauri.conf.json`.
2. Merge an approved change to the release branch.
3. Push a `desktop-v<version>` tag or run the Windows release workflow manually.
4. Download and test the draft installer on a non-production Windows account.
5. Publish the draft GitHub Release. Installed applications can then see `latest.json`.

The workflow is `.github/workflows/desktop-windows-release.yml`. macOS is intentionally
not part of the first release pipeline and will be added only after the Windows flow is
stable.
