import urllib.request, json

req = urllib.request.Request("http://localhost:8001/groups", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

groups = data.get("groups", [])
search_names = ["perfect deal", "perfect deal", "bags", "watch", "sunglass", "shoe"]
for g in groups:
    name_lower = g["group_name"].lower()
    if any(s in name_lower for s in ["perfect deal", "bags", "watch", "sunglass", "shoe"]):
        print(f"  {g['group_id']} | {g['group_name']} | members={g.get('member_count',0)}")
