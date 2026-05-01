"""Task Memory Layer — stub (Phase 8 full implementation)"""
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Task:
    id: str
    label: str
    steps: list[str]
    steps_done: int = 0
    status: str = "in_progress"  # in_progress | completed | paused | failed
    created: str = field(default_factory=lambda: date.today().isoformat())
    last_touched: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def next_step(self) -> Optional[str]:
        if self.steps_done < len(self.steps):
            return self.steps[self.steps_done]
        return None

    @property
    def is_complete(self) -> bool:
        return self.steps_done >= len(self.steps)


class TaskMemory:
    """Tracks multi-step goals across sessions. Full impl in Phase 8."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._counter = 0

    def create_task(self, label: str, steps: list[str]) -> Task:
        self._counter += 1
        task = Task(id=f"task.{self._counter:03d}", label=label, steps=steps)
        self._tasks[task.id] = task
        logger.info(f"[TaskMemory] Created task: {task.id} — {label}")
        return task

    def get_active(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == "in_progress"]

    def advance(self, task_id: str) -> Optional[str]:
        """Mark current step done. Returns next step or None if complete."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.steps_done += 1
        task.last_touched = date.today().isoformat()
        if task.is_complete:
            task.status = "completed"
            logger.info(f"[TaskMemory] Task completed: {task.id}")
        return task.next_step

    def find_by_label(self, keywords: str) -> Optional[Task]:
        kw = keywords.lower()
        for task in self.get_active():
            if kw in task.label.lower():
                return task
        return None
