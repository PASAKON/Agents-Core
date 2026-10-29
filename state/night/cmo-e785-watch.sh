#!/bin/bash
# CMO e785 night watch (28-29 Oct): read-only; exits (= wakes the session) only when a line changed.
cd /opt/MoonieXHQ/Agents/Core || exit 1
PHS="3511068d 4de5b17d b2ff34d1 3f2bd16a"
state() {
  for f in ilaglakorn cndrama filmformula; do echo "$f $(tail -1 docs/plans/$f-STATUS.md 2>/dev/null | md5sum | cut -c1-8)"; done
  .venv/bin/python tools/ask_run.py list --json 2>/dev/null | python3 -c '
import json,sys
d=json.load(sys.stdin); r=d if isinstance(d,list) else d.get("cards",[])
ph=set(sys.argv[1].split())
print("cards", " ".join(sorted(c["id"][-4:]+":"+c["status"] for c in r if str((c.get("requester") or {}).get("session",""))[-8:] in ph)))' "$PHS"
  bash scripts/hub/org-python.sh -c "
from lib import db
ph=set('$PHS'.split())
with db.get_conn(readonly=True) as c:
  rows=c.execute(\"select id,status,owner_cto from tasks where updated_at > to_char(now() - interval '12 hours','YYYY-MM-DD\\\"T\\\"HH24:MI:SS') \").fetchall()
print('tasks', ' '.join(sorted(r[0][-4:]+':'+r[1] for r in rows if str(r[2] or '')[-8:] in ph)))" 2>/dev/null | grep -v infisical
  echo "disk $(df / | awk 'NR==2{print ($5+0>=90)?"OVER90":"ok"}')"
}
prev="$(state)"
while true; do
  iv="$(python3 -c "import time; from lib import wake_backoff as w; print(int(w.wake_interval(600, tier='critical', budget_json=w.load_budget(), now=time.time())))" 2>/dev/null)"
  sleep "${iv:-600}"
  cur="$(state)"
  [ "$cur" != "$prev" ] && { diff <(echo "$prev") <(echo "$cur") | grep '^>' | cut -c1-200; exit 0; }
done
