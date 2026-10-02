#!/bin/bash
# run_fbx.sh <actions.json> <prefix> : copies actions to winbox, runs tools/fb_cdp_do.py (CDP :9281), brings <prefix>.png/.txt back to $S/fb
S=${FBX_WORK:-/tmp/fbx}
scp -q "$1" winbox:C:/mooniex/khaoniao/sched/ && ssh winbox "set PYTHONIOENCODING=utf-8&& C:\\mooniex\\pwvenv\\Scripts\\python.exe C:\\mooniex\\Agents\\Core\\tools\\fb_cdp_do.py C:\\mooniex\\khaoniao\\sched\\$(basename $1) C:\\mooniex\\khaoniao\\sched\\$2" 2>&1 | tr -d '\r' | tail -${3:-14}
scp -q winbox:C:/mooniex/khaoniao/sched/$2.png winbox:C:/mooniex/khaoniao/sched/$2.txt $S/fb/ 2>&1 | tail -1
