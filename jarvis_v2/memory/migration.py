"""
Memory Migration Script
=======================
Converts v1 memory/*.md recipe files into v2.1 SQLite graph entries.
Idempotent — safe to re-run.

What gets migrated:
    memory/apps.md      → APP nodes + launch edges
    memory/navigation.md→ PAGE nodes + FORWARD edges (multi-step recipes)
    memory/ui_maps.md   → ELEMENT nodes per app/window
    memory/folders.md   → FACT nodes in semantic layer (future)

Run:
    python -m jarvis_v2.memory.migration
"""

import logging
import os
import re
import sys
from pathlib import Path
from datetime import date

from jarvis_v2.memory.graph_db import GraphDB, GraphNode, GraphEdge

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MEMORY_V1_DIR = _PROJECT_ROOT / "memory"
_DB_DEFAULT = str(_MEMORY_V1_DIR / "jarvis_v2.db")


def migrate(db_path: str = _DB_DEFAULT, memory_dir: Path = _MEMORY_V1_DIR) -> None:
    """Main migration entry point."""
    db = GraphDB(db_path)
    logger.info(f"[Migration] Starting v1 → v2.1 migration. DB: {db_path}")

    _migrate_apps(db, memory_dir / "apps.md")
    _migrate_navigation(db, memory_dir / "navigation.md")
    _migrate_ui_maps(db, memory_dir / "ui_maps.md")

    db.close()
    logger.info("[Migration] Complete.")


def _migrate_apps(db: GraphDB, apps_file: Path) -> None:
    """Convert apps.md (app_name → exe_path) into APP nodes + launch edges."""
    if not apps_file.exists():
        return

    content = apps_file.read_text(encoding="utf-8")
    blocks = re.split(r"^## ", content, flags=re.MULTILINE)

    count = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        command = lines[0].strip()  # e.g. "open chrome"
        app_name = command.replace("open ", "").strip()

        # Find exe path in steps
        exe_path = ""
        for line in lines:
            if line.strip().startswith("1.") and "execute_process" in line:
                exe_path = line.strip().split("execute_process")[-1].strip()
                break

        if not app_name:
            continue

        node_id = f"app.{app_name.lower().replace(' ', '_')}"
        db.save_node(GraphNode(
            id=node_id,
            app_id=app_name.lower(),
            type="APP",
            label=app_name.title(),
            entry_strategy="path" if exe_path else "search",
            entry_value=exe_path,
        ))

        # Launch edge from a virtual "desktop" root
        desktop_id = "app.desktop"
        db.save_node(GraphNode(
            id=desktop_id, app_id="desktop", type="APP",
            label="Windows Desktop", entry_strategy="keyboard", entry_value="Win+D",
        ))
        db.save_edge(GraphEdge(
            id=f"edge.desktop_to_{app_name.lower().replace(' ', '_')}",
            from_id=desktop_id,
            to_id=node_id,
            edge_type="FORWARD",
            action_type="launch",
            action_params={"exe": exe_path} if exe_path else {},
            triggers=[f"open {app_name}", f"launch {app_name}", f"start {app_name}"],
            confidence=0.90,
            success_count=1,
            last_used=date.today().isoformat(),
        ))
        count += 1

    logger.info(f"[Migration] apps.md: {count} app nodes created.")


def _migrate_navigation(db: GraphDB, nav_file: Path) -> None:
    """Convert navigation.md multi-step recipes into graph edges."""
    if not nav_file.exists():
        return

    content = nav_file.read_text(encoding="utf-8")
    blocks = re.split(r"^## ", content, flags=re.MULTILINE)

    count = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        command = lines[0].strip()  # e.g. "open advanced display"

        steps = []
        app_precond = "any"
        for line in lines:
            line = line.strip()
            if line.startswith("- Preconditions:") and "app=" in line:
                m = re.search(r"app=(\S+)", line)
                if m:
                    app_precond = m.group(1).strip("|").strip()
            if re.match(r"^\d+\.", line):
                step = re.sub(r"^\d+\.\s*", "", line).strip()
                if step:
                    steps.append(step)

        if not steps:
            continue

        # Create a synthetic edge for this recipe
        safe_cmd = re.sub(r"[^a-z0-9_]", "_", command.lower())[:50]
        app_id = app_precond if app_precond != "any" else "unknown"

        # Ensure a root node exists for this app
        root_id = f"app.{app_id}"
        db.save_node(GraphNode(
            id=root_id, app_id=app_id, type="APP",
            label=app_id.title(), entry_strategy="search", entry_value="",
        ))

        # Target node (destination of this recipe)
        target_label = command.replace("open ", "").replace("go to ", "").strip()
        target_id = f"{app_id}.{safe_cmd}"
        db.save_node(GraphNode(
            id=target_id, app_id=app_id, type="PAGE",
            label=target_label.title(), entry_strategy="click", entry_value="",
        ))

        db.save_edge(GraphEdge(
            id=f"edge.{safe_cmd}",
            from_id=root_id,
            to_id=target_id,
            edge_type="FORWARD",
            action_type="sequence",
            triggers=[command],
            steps=steps,
            confidence=0.80,
            success_count=1,
            last_used=date.today().isoformat(),
        ))
        count += 1

    logger.info(f"[Migration] navigation.md: {count} recipe edges created.")


def _migrate_ui_maps(db: GraphDB, ui_file: Path) -> None:
    """Convert ui_maps.md snapshots into ELEMENT nodes."""
    if not ui_file.exists():
        return

    content = ui_file.read_text(encoding="utf-8")
    blocks = re.split(r"^## ", content, flags=re.MULTILINE)

    count = 0
    for block in blocks:
        block = block.strip()
        if not block or not block.startswith("ui_map"):
            continue
        lines = block.splitlines()
        header = lines[0].strip()  # e.g. "ui_map Settings - Display"

        # Parse "ui_map App - Window"
        m = re.match(r"ui_map\s+(.+?)\s+-\s+(.+)", header)
        if not m:
            continue
        app = m.group(1).strip().lower()
        window = m.group(2).strip()

        # Elements are in the steps list
        elements = []
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\.", line):
                elem = re.sub(r"^\d+\.\s*", "", line).strip()
                if elem:
                    elements.append(elem)

        # Create ELEMENT nodes
        page_id = f"{app}.{re.sub(r'[^a-z0-9_]', '_', window.lower())}"
        db.save_node(GraphNode(
            id=page_id, app_id=app, type="PAGE",
            label=window, entry_strategy="click", entry_value="",
        ))

        for elem in elements:
            elem_id = f"{page_id}.{re.sub(r'[^a-z0-9_]', '_', elem.lower())[:30]}"
            db.save_node(GraphNode(
                id=elem_id, app_id=app, type="ELEMENT",
                label=elem, entry_strategy="click", entry_value=elem,
            ))
            db.save_edge(GraphEdge(
                id=f"edge.{page_id}_to_{elem_id.split('.')[-1]}",
                from_id=page_id,
                to_id=elem_id,
                edge_type="FORWARD",
                action_type="click",
                triggers=[f"click {elem}", elem],
                confidence=0.75,
            ))
            count += 1

    logger.info(f"[Migration] ui_maps.md: {count} element nodes created.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    migrate()
    print("Migration complete. Run the graph exporter to verify:")
    print("  python -c \"from jarvis_v2.memory.graph_db import GraphDB; "
          "db = GraphDB('./memory/jarvis_v2.db'); print(db.list_apps())\"")
