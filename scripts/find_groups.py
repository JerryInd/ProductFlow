import urllib.request, json

req = urllib.request.Request("http://localhost:8001/groups")
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

groups = data.get("groups", [])
keywords = ["perfect", "bag", "shoe", "watch", "sunglass", "fox", "india broadcast"]
for g in groups:
    n = g["group_name"].lower()
    if any(k in n for k in keywords):
        print(f"{g['group_id']} | {g['group_name']} | members={g.get('member_count',0)}")
