flow: bl · run: 2026-10-13-ep61
node: drive · state: waiting:Mac (paid stages run on the Mac, flow.yaml host: mac)
done: [script, approve]
blocker: none — hand-off to the Mac CTO for drive/tts/prompts/transcript/lipsync/scenes/handoff
spent: $0.00 API · script_writer task-d002e35e (free steps only)

## Approval (node: approve)

Script: prototypes/bl61-script/SCRIPT.tsv — 29 lines, 852 non-space chars, forecast 74.7 s at 11.4 chars/s, 70.4 s at 12.1.
Approved by the CEO on 13 Oct 2026 in the COO terminal (AskUserQuestion taps, relayed by SomPong to CMO c4432bad):
- Q1 "ไม่เคย ใช้ชื่อได้" — the channel has never earned money from Tickmill, so the name Tickmill may be spoken and shown.
- Q2 "อนุมัติ" — the 29-line script AND the next spend: lipsync about $0.45 + scene prompts about $0.16 = about $0.61;
  with the $0.25 voice already approved the total is at most $0.86, inside the $1.00 per-run cap (flow.yaml budget.cash_usd).
Decided for the CEO by the CMO (listed to him, not objected to): keep MAIN-2 "กูคิดเอง" ($10 pip value); keep $16 and $6
on screen together; drop #Tickmill from the caption hashtags; if TTS runs past 75 s cut CURIOSITY-2 first; the editor
crops the TradingView $3.5 card and the model photo out of tm-header / tm-classic-para.

## Watch-outs for the paid stages
- Voice gate: duration within 5% of 74.7 s. A bigger miss goes back to the CEO before lipsync.
- Cap: the watcher counts the fal + OpenRouter balance delta, not the ledger. Stop and report if spent passes $0.86.
- Numbers on the stills are dated 13 Oct 2026 (the pages carry no date): re-capture and re-run cost_check.py if posting slips past 14 Oct.
