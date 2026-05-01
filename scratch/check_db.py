import sqlite3
import os

db_path = "memory/jarvis_v2.db"
if not os.path.exists(db_path):
    print(f"DB not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
curr = conn.cursor()

print("--- NODES (settings) ---")
curr.execute("SELECT id, label, entry_value FROM nodes WHERE app_id='settings' AND (id LIKE '%display%' OR id LIKE '%sound%')")
for row in curr.fetchall():
    print(row)

print("\n--- EDGES (settings) ---")
curr.execute("SELECT id, from_id, to_id, triggers FROM edges WHERE from_id='app.settings' AND (to_id LIKE '%display%' OR to_id LIKE '%sound%')")
for row in curr.fetchall():
    print(row)

conn.close()
