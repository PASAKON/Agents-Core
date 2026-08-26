# absence-plates-3

## JOB 1 — downloads (done)

| Asset id | Saved as | Confirmed on disk |
|---|---|---|
| `a7d8d116-3b08-442e-89a6-e58a014c8c81` | `/Users/gob/Desktop/absence-02-hall.png` | yes, 2.8MB |
| `92235ba9-f90f-493e-86f9-f86dc73c2123` | `/Users/gob/Desktop/absence-01-wall-crack.png` | yes, 1.8MB |
| `353e587e-40b2-435a-a6d5-8550e8fce828` | `/Users/gob/Desktop/absence-00-painting.png` | yes, 1.9MB |
| `ec45f919-7fa6-440e-aea7-d987bd140f1a` | `/Users/gob/Desktop/absence-00-tag.png` | yes, 2.0MB |

Hall (the gating shot) downloaded and reported first, per instructions.

Note: the tag-plate preview page hit two consecutive `CDP sendCommand
Page.captureScreenshot` timeouts (renderer briefly unresponsive; window also
stopped honoring resize_window, stuck at 728x420 CSS px). Per the
higgsfield-unlimited-gen skill's hard rule 7, checked Usage/Credits
immediately in a separate tab before doing anything else: paid balance read
1,844 — unchanged from the task brief's stated ~1,844, confirming the
timeouts caused no spend. Recovered by closing the frozen tab and opening a
fresh one (browser-operator skill's escalation ladder), which resolved it.

Separately: on the fresh tab, screenshots came back at 1456x840 px instead of
the CSS 1024x591 that `getBoundingClientRect()` reports — a scale mismatch
between `computer` click coordinates (screenshot pixel space) and JS-computed
coordinates (CSS pixel space). Two raw-coordinate download clicks silently
missed the button because of this. Fixed by switching to `find()` + ref-based
clicks, which are scale-safe. Flagging this as a general trap for any
future replay script: never mix JS-derived pixel coordinates with the
`computer` tool's click coordinates on this site — use refs.

## JOB 2 — tag verification

In progress.

## JOB 3 — corridor generation

Not started.

## Credits

- Paid balance: 1,844 (confirmed via Account menu → Credits, mid-JOB-1)
- Soul free allowance: not yet checked

## Tab

Tab title at time of writing: "Cinema Studio 4.0 — Direct Every Detail | Higgsfield"
