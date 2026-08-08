import sqlite3, json

DB = "/home/pi/ProductFlow/database/productflow.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== PIPELINES ===")
rows = conn.execute("SELECT id, name, enabled, prompt_template, pricing_mode, pricing_value FROM pipelines").fetchall()
for r in rows:
    prompt = r["prompt_template"] or ""
    print(f"  id={r['id']} name={r['name']} enabled={r['enabled']} pricing={r['pricing_mode']}:{r['pricing_value']} prompt_len={len(prompt)} prompt_preview={prompt[:80]}...")

print("\n=== PIPELINE SOURCES ===")
rows = conn.execute("SELECT ps.pipeline_id, p.name, ps.group_id FROM pipeline_sources ps JOIN pipelines p ON p.id = ps.pipeline_id ORDER BY ps.pipeline_id").fetchall()
for r in rows:
    print(f"  pipeline={r['name']}(id={r['pipeline_id']}) source={r['group_id']}")

print("\n=== PIPELINE DESTINATIONS ===")
rows = conn.execute("SELECT pd.pipeline_id, p.name, pd.group_id FROM pipeline_destinations pd JOIN pipelines p ON p.id = pd.pipeline_id ORDER BY pd.pipeline_id").fetchall()
for r in rows:
    print(f"  pipeline={r['name']}(id={r['pipeline_id']}) dest={r['group_id']}")

print("\n=== GROUPS TABLE (first 30) ===")
rows = conn.execute("SELECT id, group_id, group_name, member_count FROM groups ORDER BY group_name LIMIT 30").fetchall()
for r in rows:
    print(f"  [{r['id']}] {r['group_id']} | {r['group_name']} | members={r['member_count']}")

conn.close()
