import json, urllib.request

# Fetch groups
data = json.loads(urllib.request.urlopen("http://localhost:8000/api/groups/").read())
for g in data:
    print(f"{g['group_id']}|{g['group_name']}")
