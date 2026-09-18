#!/usr/bin/env bash
# Pull the remaining colab_pack shards winbox -> Contabo. Idempotent: skips
# anything already here, so it is safe to re-run after any interruption.
#
# Throttled to ~5 MB/s on purpose. The CEO is downloading an 80 GB game onto
# winbox; this is the least urgent transfer on either machine and has no reason
# to compete for his bandwidth.
set -uo pipefail
cd /root/idm-packs || exit 1
log=/root/idm-fetch.log
# "already here" means readable, not merely present. A scp killed mid-file
# leaves a shard of the right name and nearly the right size; skipping it on
# existence alone is how train_006.npz stayed truncated at 203 MB against a
# real 262 MB, and only surfaced as a BadZipFile crash inside training.
have() { [ -f "$1" ] && python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1])" "$1" 2>/dev/null; }

for i in $(seq -w 0 39); do
    f="train_0$i.npz"
    have "$f" && continue
    rm -f "$f"
    scp -q -l 40000 -o BatchMode=yes winbox:"C:/Users/UsEr/Documents/CookieRunScript/colab_pack/$f" . \
        && echo "[$(date +%H:%M:%S)] got $f" >> "$log" \
        || echo "[$(date +%H:%M:%S)] FAILED $f" >> "$log"
done
for i in 0 1 2 3 4 5 6; do
    f="val_00$i.npz"
    have "$f" && continue
    rm -f "$f"
    scp -q -l 40000 -o BatchMode=yes winbox:"C:/Users/UsEr/Documents/CookieRunScript/colab_pack/$f" . \
        && echo "[$(date +%H:%M:%S)] got $f" >> "$log" \
        || echo "[$(date +%H:%M:%S)] FAILED $f" >> "$log"
done
echo "[$(date +%H:%M:%S)] fetch done: $(ls train_*.npz | wc -l) train, $(ls val_*.npz | wc -l) val, $(du -sh . | cut -f1)" >> "$log"
