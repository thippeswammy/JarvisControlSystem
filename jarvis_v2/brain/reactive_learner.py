"""
Reactive Learner
================
Singleton that stores successful paths ONLY after verification passes.
Called by VerificationLoop — never called directly by Orchestrator.

This enforces the "Execute → Verify → Learn" guarantee:
  zero false-positive paths ever stored in memory.
"""

import logging
from datetime import date
from typing import Optional

from jarvis_v2.memory.graph_db import GraphNode, GraphEdge
from jarvis_v2.memory.memory_manager import MemoryManager
from jarvis_v2.skills.skill_bus import SkillResult

logger = logging.getLogger(__name__)


class ReactiveLearner:
    """
    Stores verified navigation paths into the procedural graph.

    Usage (called by VerificationLoop after state comparison passes):
        learner.learn(
            command="open display settings",
            app_id="settings",
            from_node="app.settings",
            to_node="settings.display",
            steps=["uri:ms-settings:display"],
            result=skill_result,
        )
    """

    def __init__(self, memory: MemoryManager):
        self._memory = memory

    def learn(
        self,
        command: str,
        app_id: str,
        from_node_id: str,
        to_node_id: str,
        steps: list[str],
        result: SkillResult,
        fast_path: str = "",
        fast_path_value: str = "",
        additional_triggers: Optional[list[str]] = None,
    ) -> None:
        """
        Persist a verified successful navigation path.
        Only called when VerificationLoop confirms state change occurred.
        """
        db = self._memory.get_db()

        # Ensure both nodes exist
        for node_id in [from_node_id, to_node_id]:
            if not db.get_node(node_id):
                label = node_id.split(".")[-1].replace("_", " ").title()
                db.save_node(GraphNode(
                    id=node_id,
                    app_id=app_id,
                    type="PAGE",
                    label=label,
                    entry_strategy="click",
                ))

        # Build trigger list
        triggers = [command.lower()]
        if additional_triggers:
            triggers.extend(t.lower() for t in additional_triggers)
        triggers = list(dict.fromkeys(triggers))  # deduplicate, preserve order

        edge_id = f"edge.{from_node_id.replace('.', '_')}_to_{to_node_id.replace('.', '_')}"

        existing = db.get_edge(edge_id)
        if existing:
            # Update confidence on existing edge
            db.update_edge_confidence(edge_id, success=True)
            # Merge new triggers
            merged = list(dict.fromkeys(existing.triggers + triggers))
            db._conn.execute(
                "UPDATE edges SET triggers=? WHERE id=?",
                (__import__("json").dumps(merged), edge_id)
            )
            db._conn.commit()
            logger.info(f"[ReactiveLearner] Updated existing edge: {edge_id}")
        else:
            # Create new edge
            edge = GraphEdge(
                id=edge_id,
                from_id=from_node_id,
                to_id=to_node_id,
                edge_type="FORWARD",
                action_type="sequence" if steps else "click",
                steps=steps,
                triggers=triggers,
                fast_path=fast_path,
                fast_path_value=fast_path_value,
                confidence=0.80,
                success_count=1,
                last_used=date.today().isoformat(),
            )
            db.save_edge(edge)
            logger.info(f"[ReactiveLearner] New edge learned: {edge_id} | triggers={triggers}")

    def penalize(self, edge_id: str) -> None:
        """Decrease confidence on a failed edge. Called by VerificationLoop on mismatch."""
        self._memory.record_failure(edge_id)
        logger.info(f"[ReactiveLearner] Penalized edge: {edge_id}")
