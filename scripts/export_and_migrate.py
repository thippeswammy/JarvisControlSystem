"""Phase 8 export + migration script."""
import sys, os
sys.path.insert(0, ".")

# Export graph.md for settings
from jarvis.memory.graph_db import GraphDB
from jarvis.memory.exporter import GraphExporter

db = GraphDB("memory/jarvis.db")
exporter = GraphExporter(db, export_root="memory/procedural/apps")
path = exporter.export_app("settings")
print(f"Exported : {path}")

# Run v1 migration (no-op if files don't exist)
from jarvis.memory.migration import migrate
migrate(db_path="memory/jarvis.db")
print("Migration complete.")

apps = db.list_apps()
print(f"Apps after migration: {apps}")
db.close()
