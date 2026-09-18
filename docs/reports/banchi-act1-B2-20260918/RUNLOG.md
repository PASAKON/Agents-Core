# Run log — B2 shots 25-48 (working notes, folded into REPORT.md at end)

Start balance: 9953 credits (read 16:0x, before shot 25)

| shot | submit | visible | elapsed_s | cr_before | cr_after | chips (order) | downloaded |
|---|---|---|---|---|---|---|---|
| 25 | 16:04:16 | | | 9953 | | @lung_somchai,@nong_daeng,@noodle_shop | |
| 26 | 16:05:31 | | | | | @nong_daeng,@staircase | |
| 27 | 16:06:28 | | | | | @nong_daeng,@grandma_pranom,@upstairs_bedroom | |
| 28 | 16:08:xx | | | | | @grandma_pranom,@upstairs_bedroom,@nong_daeng(off-frame) | |
| 29 | 16:09:xx | | | | | @grandma_pranom,@upstairs_bedroom | |
| 30 | 16:10:xx | | | | | @nong_daeng,@grandma_pranom,@upstairs_bedroom | |
| 31 | 16:11:xx | | | | | @grandma_pranom,@upstairs_bedroom,@nong_daeng(off-frame) | |
| 32 | 16:12:xx | | | | | @grandma_pranom,@nong_daeng,@upstairs_bedroom | |

BALANCE CHECK after shot 32: shared account balance = 9761 (start 9953, delta -192 = BOTH operators combined, other operator's shots 1-24 also draw this pool). My own running estimate: 8 shots submitted (25-32) x 12cr = 96cr against my 340cr cap.
| 33 | 16:13:xx | | | | | @nong_daeng,@grandma_pranom,@upstairs_bedroom | |
| 34 | 16:14:xx | | | | | @lung_somchai,@noodle_shop | |
| 35 | 16:15:xx | | | | | @lung_somchai,@noodle_shop | |
| 36 | 16:16:xx | | | | | @lung_somchai,@noodle_shop | NOTE: CTO letter mid-run updated this shot's spoken line to "แล้วอันนี้...เก็บไว้ก่อน" (longer); re-read from disk before firing per instruction, confirmed via innerText.includes() before submit |
| 37 | 16:17:xx | | | | | @nong_daeng,@lung_somchai,@noodle_shop | |
| 38 | 16:19:xx | | | | | @nong_daeng,@noodle_shop | NOTE: a "+" click after shot37 submit landed on background feed instead of composer (feed had scrolled), wrong chip (@test_char4-adjacent unrelated woman asset) got attached to draft; caught via zoom before typing prompt, cleared composer (X), redid attach with fresh screenshots each step, correct chips confirmed before submit. No credits spent on the mistake (never reached submit). |
| 39 | 16:21:xx | | | | | @cop_wit,@noodle_shop | NEW voice observed: @cop_wit bound to "achird" (Male, friendly, mid pitch) - not previously in cast ledger, flag for CTO |
| 40 | 16:22:xx | | | | | @cop_wit,@noodle_shop | |
| 41 | 16:23:xx | | | | | @lung_somchai,@noodle_shop | |

BALANCE CHECK after shot 41: shared balance = 9557 (prev 9761, delta -204). My own running estimate: 17 shots submitted (25-41) x 12cr = 204cr against 340cr cap. NOTE: the virtual-scroll feed can drift far down (scrollTop 22951px observed) after several submits, which silently moved click coordinates off-target between shots 37->38 (wrong chip attached, caught before submit, no credits lost). From shot 38 onward: reset scrollTop to 0 via JS periodically, prefer find()-based ref clicks over hardcoded pixel coords for anything outside the fixed composer, and zoom-verify chip thumbnail row before every insert.
| 42 | 16:26:xx | | | | | @cop_wit,@noodle_shop | |
| 43 | 16:29:xx | | | | | @lung_somchai,@noodle_shop | |
| 44 | 16:31:xx | | | | | @cop_wit,@lung_somchai,@noodle_shop | |
| 45 | 16:33:xx | | | | | @cop_wit,@lung_somchai,@noodle_shop | |
| 46 | 16:38:xx | | | | | @cop_wit,@lung_somchai,@money_fold,@noodle_shop | FINDING: with 4 chips attached, the 4th (@noodle_shop, REF_3) is silently marked class="chip-image-wrapper inactive" with a "disabled-error-icon" overlay in the composer DOM - a real UI-enforced 3-active-ingredient cap in THIS project, contradicting google-flow-ops skill's "up to 10 image references" claim (that number is the documented API ceiling, not what this project's UI actually allows). Fired anyway per "fire as written, report the finding, don't improvise" instruction - REF_3/location may not actually be honored by the model. Needs CTO review of the resulting clip. |
| 47 | 16:40:xx | | | | | @lung_somchai,@money_fold,@noodle_shop | 3 chips, all active (no cap issue) |
| 48 | 16:42:xx | | | | | @nong_daeng,@lung_somchai,@noodle_shop | FINAL SHOT of Act1 B2. All 4 dialogue lines confirmed present via innerText check before submit. |

FINAL BALANCE after shot 48 (all 24 submitted): shared balance = 9413 (start 9953, total shared delta -540 across both operators). My own estimate: 24 shots x 12cr = 288cr against 340cr cap - under cap. Never touched Upgrade/Subscribe/Buy credits.
