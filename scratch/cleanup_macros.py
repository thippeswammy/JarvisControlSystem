import sqlite3

db_path = 'memory/jarvis.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Find all macros that call ask_user
cursor.execute("SELECT id, triggers FROM edges WHERE action_type='macro' AND action_params LIKE '%ask_user%'")
to_delete = cursor.fetchall()

if to_delete:
    print(f"Found {len(to_delete)} macros to delete:")
    for id, triggers in to_delete:
        print(f"  - {id}: {triggers}")
    
    cursor.execute("DELETE FROM edges WHERE action_type='macro' AND action_params LIKE '%ask_user%'")
    conn.commit()
    print("Cleanup complete.")
else:
    print("No problematic macros found.")

conn.close()
