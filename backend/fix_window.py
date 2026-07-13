import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.database.connection import get_connection
conn = get_connection()
conn.execute('UPDATE pipelines SET collector_window_seconds = 40 WHERE id = 3')
conn.commit()
row = conn.execute('SELECT id, name, collector_window_seconds FROM pipelines WHERE id = 3').fetchone()
print(f"Pipeline {row['id']}: {row['name']} window={row['collector_window_seconds']}s")
conn.close()
