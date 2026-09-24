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
- turns: 10
- tokens: input=20 cache_write=306175 cache_read=373114 output=26068
- API-equivalent $ (Sonnet 5 pricing table): $1.1008
- Max-plan reported $ (claude -p's own total_cost_usd): $0.3418
- wall seconds: 88.54
