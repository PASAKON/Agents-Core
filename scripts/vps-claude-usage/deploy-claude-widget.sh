#!/usr/bin/env bash
# Deploy the Claude Usage widget (Scriptable) to the Mac's iCloud folder.
#
# WHY this exists: the widget .js is NOT synced by claude-usage-sync.sh — that
# script writes only claude-usage.json (the numbers). The .js (the DESIGN + fetch
# logic) reaches the iPhone only through this manual copy into iCloud. So after any
# widget redesign you MUST re-run this, or iCloud keeps serving the OLD design while
# the repo moves on. That is exactly how the pixel-art redesign "reverted" to the
# old glass look on 2026-06-24.
#
# Token is injected ONLY into the URL (k=__USAGE_TOKEN__), never globally. A global
# sed (s/__USAGE_TOKEN__/$TOK/) would also rewrite the bare placeholder inside the
# fromURL() guard, making it match the real token, so fromURL() returns null every
# time and VPS-fetch silently dies (widget falls back to iCloud-only, losing the
# whole "fresh even when the Mac is off" point). Keep the sed scoped to `k=`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_JS="$REPO_ROOT/output/iphone-shortcuts/Claude Usage.js"
ICLOUD_DIR="$HOME/Library/Mobile Documents/iCloud~dk~simonbs~Scriptable/Documents"
ICLOUD_JS="$ICLOUD_DIR/Claude Usage.js"

[ -f "$REPO_JS" ]    || { echo "repo widget not found: $REPO_JS" >&2; exit 1; }
[ -d "$ICLOUD_DIR" ] || { echo "Scriptable iCloud dir not found — is Scriptable installed + iCloud Drive on?" >&2; exit 1; }

# token source: $USAGE_TOKEN env, else reuse whatever is already deployed in iCloud
TOK="${USAGE_TOKEN:-}"
if [ -z "$TOK" ] && [ -f "$ICLOUD_JS" ]; then
  TOK=$(sed -nE 's#.*claude-usage\?k=([A-Za-z0-9]+).*#\1#p' "$ICLOUD_JS" | head -1)
fi
if [ -z "$TOK" ] || [ "$TOK" = "__USAGE_TOKEN__" ]; then
  echo "no token found. set USAGE_TOKEN=<token from VPS serve/.env> and re-run." >&2
  exit 1
fi

# scoped inject: ONLY the URL token; the fromURL() guard placeholder stays intact.
# overwrite in place (truncate-write, NOT rm+recreate) so iCloud keeps a stable
# inode and uploads incrementally instead of churning delete+create.
sed "s|k=__USAGE_TOKEN__|k=$TOK|" "$REPO_JS" > "$ICLOUD_JS"

# verify
guard=$(grep -c '__USAGE_TOKEN__' "$ICLOUD_JS" || true)
glass=$(grep -c 'Liquid Glass' "$ICLOUD_JS" || true)
echo "deployed → $ICLOUD_JS"
echo "  design : $(head -1 "$ICLOUD_JS" | sed 's#// *##')"
echo "  guard  : $guard placeholder kept (want 1 → VPS-fetch live)"
[ "$glass" -eq 0 ] || echo "  WARN   : $glass 'Liquid Glass' marker(s) — repo file may be the old design?!" >&2
echo "iCloud syncs to the iPhone in ~1-3 min; the widget repaints on the next iOS refresh."
