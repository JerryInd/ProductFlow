import json, urllib.request

data = json.loads(urllib.request.urlopen("http://localhost:8001/groups").read())
groups = sorted(data["groups"], key=lambda x: x["member_count"], reverse=True)
for g in groups:
    if g["member_count"] >= 10:
        print(f'{g["group_id"]} | {g["group_name"]} | {g["member_count"]}')
