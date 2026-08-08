import urllib.request, json

groups = json.loads(urllib.request.urlopen("http://localhost:8000/api/groups/").read())
for g in groups:
    if "rizwan" in g["group_name"].lower():
        print(f"Found: {g['group_id']} = {g['group_name']}")

pipelines = json.loads(urllib.request.urlopen("http://localhost:8000/api/pipelines/").read())
for p in pipelines:
    if p["name"] == "Watch":
        print(f"\nWatch pipeline sources: {[s['group_id'] for s in p['sources']]}")
