# WORKLOG task-cc55e620 (iter 2, one window at a time)

Resumed after the 2 Oct OOM. seg01-05, seg11, seg12 re-verified by ffprobe (duration + frame count match segments.json); seg06/07/10 had no partial files left, seg08/09 never started.

- seg01,02,03,04,05,11,12 | kept from iter 1 | ffprobe duration and frame count match their windows | ok
- seg06 | 42.3333-48.9667 | start 02:43:50 UTC | free -m available 6054 MB | end 02:46:43 UTC | ok
- seg07 | 48.9667-56.5667 | start 02:46:43 UTC | free -m available 6337 MB | end 02:49:36 UTC | ok
- seg08 | 56.5667-64.8 | start 02:49:36 UTC | free -m available 6343 MB | end 02:50:33 UTC | ok
- seg09 | 64.8-71.5667 | start 02:50:33 UTC | free -m available 6310 MB | end 02:51:18 UTC | ok
- seg10 | 71.5667-79.2 | start 02:51:18 UTC | free -m available 6298 MB | end 02:53:39 UTC | ok
