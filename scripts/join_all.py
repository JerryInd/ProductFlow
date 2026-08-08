import urllib.request, json, time

invites = [
    ("Cxp4cp0zBJW3VoC4T9fD1c", "Perfect Deal Shoes"),
    ("IGvNX1d553G4Fii28PHN0I", "Perfect Deal Sunglasses"),
    ("CG2neRXMTzj0s7VUfoLkwV", "Perfect Deal Bags"),
]

for code, name in invites:
    data = json.dumps({"code": code}).encode()
    req = urllib.request.Request("http://localhost:8001/join-invite", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            print(f"  {name}: {result}")
    except Exception as e:
        print(f"  {name}: Error {e}")
    time.sleep(2)

print("\nUpdated groups:")
time.sleep(3)
req2 = urllib.request.Request("http://localhost:8001/groups")
with urllib.request.urlopen(req2, timeout=15) as resp:
    data = json.loads(resp.read())
groups = data.get("groups", [])
for g in groups:
    n = g["group_name"].lower()
    if "perfect deal" in n:
        print(f"  {g['group_id']} | {g['group_name']} | members={g.get('member_count',0)}")
