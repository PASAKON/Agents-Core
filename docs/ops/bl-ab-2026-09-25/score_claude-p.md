# BLACK LIQUIDITY Scorer

- common beats (in both truth and produced): 8
- missing (in truth, not produced): ['PATTERN-1b']
- extra (produced, not in truth): (none)
- mode agreement: 50.0% (4/8)
- mean IoU (over 6 beats with a box on both sides): 0.189

| tag | truth mode | scripter mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | EVID | no | - |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | EVID | no | 0.178 |
| HOOK-4 | COMP | EVID | no | 0.084 |
| PATTERN-1 | COMP | EVID | no | 0.337 |
| PATTERN-2 | EVID | EVID | yes | 0.178 |
| PATTERN-3 | EVID | EVID | yes | 0.178 |
| PATTERN-4 | EVID | EVID | yes | 0.178 |

## Scripter run cost
- backend: claude-p
- turns: 3 (API calls; 10 transcript lines -- deduplicated by message.id, corrected 2026-09-25)
- tokens: input=6 cache_write=56979 cache_read=164157 output=8103
- API-equivalent $ (Sonnet 5 pricing table): $0.2563 (first published $1.1008 = raw line sum)
- Max-plan reported $ (claude -p's own total_cost_usd): $0.3418
- wall seconds: 88.54
