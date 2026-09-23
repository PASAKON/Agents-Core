import sys, json, urllib.request, urllib.parse, importlib.util
spec = importlib.util.spec_from_file_location("dc", "/Users/gob/MoonieXHQ/Agents/Core/scripts/session-deadline-check.py")
dc = importlib.util.module_from_spec(spec); spec.loader.exec_module(dc)
env = dc.load_env(dc.ENV_PATH)
url, key, uid = env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"], env["LUNGNOTE_USER_ID"]
pat = sys.argv[1]
q = {"user_id": f"eq.{uid}", "done": "eq.false", "or": pat,
     "select": "id,text,due_at,status", "order": "due_at.asc"}
req = urllib.request.Request(f"{url}/rest/v1/lungnote_todos?" + urllib.parse.urlencode(q),
      headers={"apikey": key, "Authorization": f"Bearer {key}"})
rows = json.load(urllib.request.urlopen(req, timeout=10))
for r in rows:
    print(f"- [{r['id'][:8]}] due {str(r['due_at'])[:10]} :: {r['text'][:700]}\n")
print(len(rows), "rows")
