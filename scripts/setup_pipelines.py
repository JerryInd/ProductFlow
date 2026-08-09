import json, urllib.request

API = "http://localhost:8000"

def api_post(path, data):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# Fetch all groups
groups = json.loads(urllib.request.urlopen(f"{API}/api/groups/").read())
gmap = {g["group_name"].strip(): g["group_id"] for g in groups}

PROMPT = """You are a product listing assistant. Rewrite the product message for a WhatsApp reseller group.

RULES:
1. Keep the original product name and description
2. Add MARKUP of ₹1000 to the original price
3. Format: Product name, Price (with markup), Description, Contact info
4. Use emojis to make it attractive
5. If no price is provided, add "Price: Contact for price"
6. Keep it concise and professional
7. DO NOT add any disclaimers or AI-related text
8. DO NOT mention the original source or supplier
9. Use the format: ✨ PRODUCT NAME ✨
   💰 Price: ₹[price + 1000]
   📝 Description
   📞 Contact: JerryIndia (918169858589)

If the message has no price at all, return the original message unchanged."""

# Destination groups
dest_bags = "120363426859202955@g.us"
dest_watch = "120363343288184000@g.us"
dest_shades = "120363410816365030@g.us"
dest_shoes = "120363428017426457@g.us"
dest_test = "120363411530358187@g.us"

# Source groups by name
bags_src = [
    "Budget Bags Wholesale",
    "WHOLESALE BAGS PREMIUM",
    "ANSARI COLLECTION",
]
watch_src = [
    "Asian Watch ⌚",
    "HRS Watch ( Harish ) 🕉️ 🕉️",
    "JAYESH WATCH ⌚️ MUMBAI ",
    "Pratap Bhai watch mumbai (B.T)",
    "Rizwan  WATCH ",
    "Mw smart watch world 🌎",
    "MW smart watch world 🌎",
    "HARIOM JEWELLERS💍",
]
shades_src = [
    "Arfat Sunglasses🕶️",
    "Mw world 🌍 sunglass 🥽",
    "Sunglasses 😎 Wala Mumbai",
    "Sunglasses🕶️",
]
shoes_src = [
    "Mr.Shoes Broadcast Group3",
    "Sneaker hub broadcast ",
    "Superkicks broadcast ",
    "Zen Brodcast 2",
]
test_src = [
    "Source group test",
]

pipelines = [
    ("Bags", bags_src, [dest_bags]),
    ("Watch", watch_src, [dest_watch]),
    ("Shades", shades_src, [dest_shades]),
    ("Shoes", shoes_src, [dest_shoes]),
    ("Test", test_src, [dest_test]),
]

for name, src_names, dests in pipelines:
    src_ids = []
    for s in src_names:
        if s in gmap:
            src_ids.append(gmap[s])
        else:
            # fuzzy match
            for gn, gid in gmap.items():
                if s.lower().strip() in gn.lower().strip():
                    src_ids.append(gid)
                    break
    
    enabled = name != "Test"
    result = api_post("/api/pipelines/", {
        "name": name,
        "prompt_template": PROMPT,
        "pricing_mode": "fixed",
        "pricing_value": 1000,
        "collector_window_seconds": 90,
        "auto_publish": True,
        "enabled": enabled,
        "source_group_ids": src_ids,
        "destination_group_ids": dests,
    })
    print(f"Created pipeline '{name}' (id={result['id']}): {len(src_ids)} sources -> {len(dests)} destinations")
    for s in src_ids:
        print(f"  Source: {s}")

print("\nDone! All pipelines created.")
