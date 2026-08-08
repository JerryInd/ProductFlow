import urllib.request, json

# Get all pipelines
pipelines = json.loads(urllib.request.urlopen("http://localhost:8000/api/pipelines/").read())
groups = json.loads(urllib.request.urlopen("http://localhost:8000/api/groups/").read())
group_map = {g["group_id"]: g["group_name"] for g in groups}

for p in pipelines:
    print(f"\n{'='*60}")
    print(f"Pipeline: {p['name']} (id={p['id']}, enabled={p['enabled']})")
    print(f"Sources ({len(p['sources'])}):")
    for s in p["sources"]:
        jid = s["group_id"]
        name = group_map.get(jid, "UNKNOWN")
        print(f"  {jid} = {name}")
    print(f"Destinations ({len(p['destinations'])}):")
    for d in p["destinations"]:
        jid = d["group_id"]
        name = group_map.get(jid, "UNKNOWN")
        print(f"  {jid} = {name}")

# Check recent relay logs for any source groups that posted but didn't match
print(f"\n{'='*60}")
print("Checking relay logs for unmatched messages...")
