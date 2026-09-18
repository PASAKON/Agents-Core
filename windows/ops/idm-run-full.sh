#!/usr/bin/env bash
# Chain the overnight Cookie Run IDM training on Contabo, unattended.
#
# Why this exists as a script rather than three commands typed in order: the
# three steps are separated by ~40 minutes each, nobody is awake for the joins,
# and a session that ends between them would leave the corpus transferred and
# nothing training. setsid detaches it from whatever started it.
#
# Order matters and is not arbitrary:
#   1. wait for the shard transfer to finish   -- training on a partial corpus
#      would silently train on whatever happened to have landed
#   2. wait for the baseline arm to finish     -- both runs on 4 cores at once
#      makes each slower than running them back to back, and the baseline is
#      the A/B's control: it must not be starved into a worse model than it is
#   3. train the full arm
#
# Everything is nice'd. This box is the org hub; the training is the least
# urgent thing running on it.
set -uo pipefail

PACKS=/root/idm-packs
LOG=/root/idm-full.log
VENV=/root/idm-venv/bin/python
SCRIPT=/opt/mooniex-agents/windows/cookierun_idm_train_colab.py
EXPECT_TRAIN=40
EXPECT_VAL=7

say() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG"; }

# Wait for the FETCH to say it is done, not for the file count to reach 40.
# Counting files in a directory that is still being written into is not a
# completion check: the count hit 40 at 19:13:18 while the last shard was still
# mid-scp, training started on it, and died with BadZipFile. The fetch writes
# its "fetch done" line last, after every file is closed.
say "waiting for the shard transfer ($EXPECT_TRAIN train + $EXPECT_VAL val)"
for _ in $(seq 1 240); do
    grep -q "fetch done" /root/idm-fetch.log 2>/dev/null && break
    pgrep -f idm-fetch.sh >/dev/null 2>&1 || break   # fetch died; stop waiting on it
    sleep 30
done
t=$(ls "$PACKS"/train_*.npz 2>/dev/null | wc -l)
v=$(ls "$PACKS"/val_*.npz 2>/dev/null | wc -l)
say "transfer settled at $t train / $v val shards ($(du -sh $PACKS | cut -f1))"
if [ "$t" -lt "$EXPECT_TRAIN" ]; then
    # Say it rather than quietly training on less. A run that reports a corpus
    # size it did not actually use is the one failure mode nobody catches later.
    say "WARNING: only $t of $EXPECT_TRAIN train shards arrived -- training on what is here"
fi

say "waiting for the baseline arm to finish"
# Two exit conditions, both needed. report.json means it finished properly.
# No training process alive means it died -- and waiting another two hours for a
# dead process to write a file it will never write is its own kind of failure.
# (Matching on the env var would not work: a variable set as a command prefix
# never appears in the process's cmdline, so pgrep could never see it.)
# report.json EXISTING does not mean the baseline finished -- the trainer
# rewrites it after every epoch so a crash never loses everything. Reading its
# mere presence made the chain announce "baseline done: 4 epochs" at 19:13 for a
# run that was on epoch 4 of 6 and finished at 19:27. Only the final write adds
# minutes_total, so that key is the actual end-of-run marker.
for _ in $(seq 1 240); do
    grep -q minutes_total /root/idm-baseline/report.json 2>/dev/null && break
    pgrep -f cookierun_idm_train_colab >/dev/null 2>&1 || break
    sleep 30
done
if [ -f /root/idm-baseline/report.json ]; then
    say "baseline done: $(python3 -c 'import json;r=json.load(open("/root/idm-baseline/report.json"));e=r["epoch_log"][-1];print(len(r["epoch_log"]),"epochs,",r["train_frames"],"frames, val thr0.5 F1",e["val"]["0.5"]["f1"])' 2>/dev/null || echo unreadable)"
else
    say "baseline produced no report.json -- continuing with the full arm anyway"
fi

say "starting the FULL arm: all shards, 2 epochs, 300 min budget, 2 workers"
IDM_LOCAL=$PACKS IDM_OUT=/root/idm-full IDM_DEVICE=cpu \
IDM_EPOCHS=2 IDM_WORKERS=2 IDM_MAX_MINUTES=300 \
    nice -n 10 "$VENV" "$SCRIPT" >> "$LOG" 2>&1
say "full arm exited with status $?"
say "done"
