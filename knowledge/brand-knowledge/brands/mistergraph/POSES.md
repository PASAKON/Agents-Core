# Mr. Graph pose library (PROPOSED, CMO 26 Oct 2026; the CEO may add or cut by number)

The CEO, 26 Oct 2026, about 20:10 TH: "คุณให้ ChatGPT ออกแบบ เอกลักษณ์ ของ Mr กราฟ มาดีกว่านะ ใช้โครงสร้างเดิมได้เลย
สีและตรีแบบเดิมทุกอย่าง ให้ออกแบบมาเป็นแนว PNG แล้วเอามาขยับเป็น ภาพๆ เอา แบบ Pixel Art เขาทำกัน / ทำมาเก็บไว้หลายๆ
แบบ ที่ใช้ประจำ ๆ ได้เลย ลองคิดท่ทางที่ต้งอใช้ทั้งหมดมาดู".
**Style (decided):** the smooth cartoon of the current mascot, drawn cleaner and prettier, then moved frame by frame.
CEO, question card Q-20261026-1308-7fb5, 26 Oct 13:19Z: "ลายเส้นการ์ตูนเรียบแบบเดิม วาดให้สวยขึ้น แล้วขยับทีละภาพ".
"Pixel Art" in his order meant the frame-by-frame way of moving, not a pixel grid.

## How every pose is made
- **The art:**
  - ChatGPT draws every pose from the CEO's mascot (`/opt/MoonieXHQ/Work/mistergraph/kit/ref/badge-crop.png`,
    attached to each prompt).
  - The structure and the colours are those in `BRAND.md` §Mascot.
  - The badge ring and the wordmark are never drawn by an image model.
- **Where it runs:**
  - The ChatGPT web UI on the CEO's Plus account, in the winbox Chrome at 127.0.0.1:9224. There is no per-image
    cost; never the OpenAI API.
  - The run waits until the CEO releases winbox (`pc-lease status`; "PC: CEO" means wait).
  - Only one driver at a time: run under `flock /opt/MoonieXHQ/Work/.winbox-chatgpt.lock`.
  - The queue on that lock (CMO, 26 Oct): CnDrama EP02 plates and logos, then the Mr. Graph master sheet and pose 2,
    then the pose batches.
- **One motion = one strip.** Ask for all of a motion's frames side by side in ONE image, so the character stays
  the same across them. Then slice the strip, align the frames and check them by eye.
- **Background:** ask for a transparent background. If the file comes back without one, ask for flat magenta
  #FF00FF (no token uses it) and key it out locally.
- **File format:**
  - Each frame is a transparent PNG on one canvas size (1024x1024).
  - Every pose shares one scale and one anchor: the bottom centre of the suit.
  - Name the files `<nn>-<pose>-f<k>.png`.
  - Masters go in the Work folder. Git takes only the scripts and a sheet under 1 MB (media_guard).
- **Facing:**
  - Mr. Graph stands on the right and faces or points left, toward the chart.
  - Never mirror a frame: the quiff always sweeps up and to the right.
  - Half body (waist up) unless the pose says otherwise.
- **Colour lock:** snap every frame's flat areas to the BRAND.md tokens (orange, peach, white, slate, ink). Leave
  the edge pixels of the line art alone. Image models drift off hex.
- [DROPPED 2026-10-26, Q-20261026-1308-7fb5] Pixel art only: one true pixel grid (nearest neighbour), scaled up by a
  whole number.
- **Playback:** stepped, 8–12 frames a second, the way game sprites move. A loop's last frame must lead back into
  its first.

## The 25 poses (88 frames)

### A. Used in every video
| # | Pose | Frames | When |
|---|---|---|---|
| 1 | Idle, breathing | 4, loop | between lines, waiting |
| 2 | Point at the chart, up and to the left (the channel's main pose) | 4: raise, hold, tap | reading the chart |
| 3 | Point down at the indicator pane | 4 | reading RSI/MACD below the candles |
| 4 | Explain: open palm, mustache moves (he has no mouth) | 3, loop | under the voice |
| 5 | Glasses glint (his blink) | 3 | every 3–5 s |
| 6 | Index finger up, "remember this" | 3 | the key line |
| 7 | Count 1, 2, 3 on his fingers | 3 hand poses | rules one by one |
| 8 | Wave hello | 4 | the opening |

### B. Feelings
| # | Pose | Frames | When |
|---|---|---|---|
| 9 | Think: strokes his beard | 3, loop | the question in the title |
| 10 | Surprise: quiff jumps, glasses pop | 3 | a sharp drop or spike |
| 11 | Shake head, "no" | 4 | "not a buy signal yet" |
| 12 | Shrug | 3 | "no indicator is right every time" |
| 13 | Palm out, "careful" | 3 | when the indicator fails; next to the risk card |
| 14 | Scratch head, puzzled | 3 | "why is it still going up?" |
| 15 | Thumbs up | 3 | a correct reading, the recap |
| 16 | Arms crossed, sure of himself | 2 | the recap |

### C. With a prop
| # | Pose | Frames | When |
|---|---|---|---|
| 17 | Teacher's pointer stick | 4 | a far point on the chart |
| 18 | Marker: draws a line on the chart | 4 | the 30/70 lines, a trend line |
| 19 | Magnifying glass | 3 | zoom into the candles |
| 20 | Checks his wristwatch | 3 | "wait for the candle to close" |
| 21 | Holds a blank sign (text is set by us) | 2 | a rule or the next-episode name |

### D. Badge and transitions
| # | Pose | Frames | When |
|---|---|---|---|
| 22 | Badge sting: the ring pops in, the quiff bounces (ring and wordmark set by us) | 6 | the first 2 s |
| 23 | Head only: talk, think, surprise | 3 x 2 | a corner of the screen |
| 24 | Peeks in from the frame edge | 4 | a scene change |
| 25 | Waves goodbye, points at the next-episode card | 4 | the last 4 s |

## Order of work
1. First run: one master model sheet (front, three-quarter, the main expressions) and pose 2 as one strip, in the
   decided style. The CMO checks it by eye; the CEO then sees the sheet.
2. Then poses 1, 4 and 5.
3. Then A, B, C and D, in that order.
[SUPERSEDED 2026-10-26, Q-20261026-1308-7fb5] Style test: pose 2 in both styles, then the CEO picks.
4. Each batch goes to the CMO as one numbered contact sheet plus a looping preview per motion; the CEO answers by
   number.
5. Until the new poses pass, videos keep the hand-built SVG mascot on its own layer, so the new frames swap in as
   files.
