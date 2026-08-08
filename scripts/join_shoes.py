import urllib.request, json, time

# Join via invite code
code = "Cxp4cp0zBJW3VoC4T9fD1c"
data = json.dumps({"code": code}).encode()
req = urllib.request.Request("http://localhost:8001/join-invite", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("Join result:", resp.read().decode())
except Exception as e:
    print(f"Error: {e}")

time.sleep(3)

# Re-fetch groups
req2 = urllib.request.Request("http://localhost:8001/groups")
with urllib.request.urlopen(req2, timeout=15) as resp:
    data = json.loads(resp.read())
groups = data.get("groups", [])
for g in groups:
    n = g["group_name"].lower()
    if "perfect deal" in n:
        print(f"  {g['group_id']} | {g['group_name']} | members={g.get('member_count',0)}")
