#!/bin/bash
# plain-shell quota loop: run -> on exit 5 (usage limit) wait 20 min -> rerun (ledger resumes). No model in the loop.
LOG=/opt/MoonieXHQ/Work/task-ed742f4b/ep5_loop.log
stuck=0; last_done=-1
for attempt in $(seq 1 60); do
  echo "$(date -u +%FT%TZ) attempt $attempt: guard check" >> $LOG
  n=$(ssh winbox 'powershell -NoProfile -Command "(Get-CimInstance Win32_Process | ? { $_.CommandLine -like \"*chatgpt_images*\" -and $_.Name -like \"python*\" } | Measure-Object).Count"' 2>/dev/null | tr -d '\r ')
  if [ "$n" != "0" ]; then echo "$(date -u +%FT%TZ) STOP: $n chatgpt_images python procs already on winbox" >> $LOG; exit 9; fi
  done_before=$(ssh winbox 'dir /b C:\mooniex\ep5\run\out\S*.png 2>nul | find /c ".png"' 2>/dev/null | tr -d '\r ')
  echo "$(date -u +%FT%TZ) start run, images on disk before: $done_before" >> $LOG
  ssh winbox 'C:\mooniex\pwvenv\Scripts\python.exe C:\mooniex\ep5\run\tools\chatgpt_images.py --json C:\mooniex\ep5\plates_all.json --out C:\mooniex\ep5\run\out --cdp-url http://127.0.0.1:9224 --lease-host winbox --parallel 3' >> $LOG 2>&1
  rc=$?
  done_after=$(ssh winbox 'dir /b C:\mooniex\ep5\run\out\S*.png 2>nul | find /c ".png"' 2>/dev/null | tr -d '\r ')
  echo "$(date -u +%FT%TZ) run exit $rc, images on disk after: $done_after" >> $LOG
  if [ "$rc" = "0" ]; then echo "$(date -u +%FT%TZ) ALL DONE" >> $LOG; exit 0; fi
  if [ "$rc" = "5" ]; then echo "$(date -u +%FT%TZ) QUOTA OUT after $done_after images; waiting 20 min" >> $LOG; sleep 1200; continue; fi
  if [ "$rc" = "6" ]; then
    if [ "$done_after" = "$last_done" ]; then stuck=$((stuck+1)); else stuck=0; fi
    last_done=$done_after
    if [ "$stuck" -ge 12 ]; then echo "$(date -u +%FT%TZ) STOP rc=6 12 times with no progress (human check?)" >> $LOG; exit 6; fi
    echo "$(date -u +%FT%TZ) rc=6 composer/attach hiccup after $done_after images; retry in 300 s" >> $LOG; sleep 300; continue
  fi
  echo "$(date -u +%FT%TZ) STOP rc=$rc (not quota)" >> $LOG; exit $rc
done
