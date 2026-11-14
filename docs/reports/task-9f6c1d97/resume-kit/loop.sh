#!/bin/bash
S=/opt/MoonieXHQ/Work/task-9f6c1d97/tmp
for i in $(seq 1 30); do
  echo "$(date -u +%FT%TZ) attempt $i" >> $S/loop.log
  perl -e 'alarm 7000; exec @ARGV' -- ssh winbox powershell -NoProfile -ExecutionPolicy Bypass -File C:/mooniex/ep04-shots/attempt.ps1 > $S/attempt.out 2>&1
  echo "rc=$?" >> $S/loop.log; tail -3 $S/attempt.out >> $S/loop.log
  if grep -q '^NOSTOP' $S/attempt.out; then echo "DONE-NOSTOP" >> $S/loop.log; exit 0; fi
  if grep -q 'ramgate' $S/attempt.out; then sleep 300; else sleep 1200; fi
done
echo GAVE-UP >> $S/loop.log
