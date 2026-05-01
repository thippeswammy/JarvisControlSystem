"""Phase 8 seeding script — seeds settings graph into live SQLite DB."""
import sys, os
sys.path.insert(0, ".")
os.makedirs("memory", exist_ok=True)

from jarvis.memory.graph_db import GraphDB
from jarvis.memory.layers.procedural import ProceduralMemory

db = GraphDB("memory/jarvis.db")
proc = ProceduralMemory(db)
seeded = proc.seed_settings_graph()

apps = db.list_apps()
nodes = db.get_nodes_for_app("settings")
edges = db.get_edges_for_app("settings")

print(f"Seeded      : {seeded} new nodes")
print(f"Apps in DB  : {apps}")
print(f"Total nodes : {len(nodes)}")
print(f"Total edges : {len(edges)}")
db.close()
print("Seeding complete.")
