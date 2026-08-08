import sqlite3
import os

db_path = '/home/pi/ProductFlow/database/productflow.db'
schema_path = '/home/pi/ProductFlow/database/schema.sql'

os.makedirs('/home/pi/ProductFlow/database', exist_ok=True)

conn = sqlite3.connect(db_path)
with open(schema_path) as f:
    conn.executescript(f.read())
conn.close()
print('Database created')
