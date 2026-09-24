# BLACK LIQUIDITY Scorer

- common beats (in both truth and produced): 8
- missing (in truth, not produced): ['PATTERN-1b']
- extra (produced, not in truth): (none)
- mode agreement: 75.0% (6/8)
- mean IoU (over 6 beats with a box on both sides): 0.402

| tag | truth mode | scripter mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | COMP | yes | - |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | COMP | yes | 0.526 |
| HOOK-4 | COMP | COMP | yes | 0.000 |
| PATTERN-1 | COMP | COMP | yes | 0.312 |
| PATTERN-2 | EVID | COMP | no | 0.526 |
| PATTERN-3 | EVID | COMP | no | 0.526 |
| PATTERN-4 | EVID | EVID | yes | 0.526 |

## Scripter run cost
- backend: claude-p
- turns: 11
- tokens: input=22 cache_write=424118 cache_read=451428 output=24247
- API-equivalent $ (Sonnet 5 pricing table): $1.3931
- Max-plan reported $ (claude -p's own total_cost_usd): $0.4274
- wall seconds: 103.14
