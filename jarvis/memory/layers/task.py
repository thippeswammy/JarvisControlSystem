"""
Task Memory Layer — Full Implementation
========================================
Tracks multi-step goals that span sessions.

Design spec (Part 4, Layer 5):
  - 'Iron Man's JARVIS remembers you were building the suit yesterday,
     here's where you left off.'
  - Task nodes: id, label, steps, steps_done, status, created, last_touched
  - Orchestrator checks task memory when command contains 'continue' or 'resume'

Persistence:
  - memory/task/active/task_NNN.md    ← in-progress tasks
  - memory/task/completed/task_NNN.md ← finished tasks (archived)

Usage:
    tm = TaskMemory()
    task = tm.create_task("Set up dev environment", steps=[
        "install git", "install python", "install vscode"
    ])
    tm.advance(task.id)   # marks step 1 done
    ctx = tm.as_llm_context()
"""
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MEMORY_ROOT  = Path(__file__).resolve().parent.parent.parent.parent / "memory"
_ACTIVE_DIR   = _MEMORY_ROOT / "task" / "active"
_COMPLETE_DIR = _MEMORY_ROOT / "task" / "completed"


@dataclass
class Task:
    """A multi-step goal tracked across sessions."""
    id: str
    label: str
    steps: list[str]
    steps_done: int = 0
    status: str = "in_progress"   # in_progress | completed | paused | failed
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

    @property
    def progress_pct(self) -> int:
        if not self.steps:
            return 100
        return int(100 * self.steps_done / len(self.steps))

    def to_md(self) -> str:
        """Serialize to the .md format defined in the design spec."""
        lines = [
            f"# Task {self.id}",
            f"<!-- status={self.status} steps_done={self.steps_done}/{len(self.steps)} -->",
            "",
            f"## Node",
            f"- id: {self.id}",
            f"- type: TASK",
            f"- label: {self.label}",
            f"- status: {self.status}",
            f"- steps_total: {len(self.steps)}",
            f"- steps_done: {self.steps_done}",
            f"- next_step: {self.next_step or 'none'}",
            f"- created: {self.created}",
            f"- last_touched: {self.last_touched}",
            "",
            "## Steps",
        ]
        for i, step in enumerate(self.steps):
            done_mark = "✅" if i < self.steps_done else "⬜"
            lines.append(f"- {done_mark} {step}")
        return "\n".join(lines)

    @classmethod
    def from_md(cls, text: str) -> Optional["Task"]:
        """Parse a task from its .md representation. Returns None on error."""
        try:
            data: dict = {}
            steps: list[str] = []
            in_steps = False
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("- id: "):
                    data["id"] = line[6:]
                elif line.startswith("- label: "):
                    data["label"] = line[9:]
                elif line.startswith("- status: "):
                    data["status"] = line[10:]
                elif line.startswith("- steps_total: "):
                    pass  # derived from len(steps)
                elif line.startswith("- steps_done: "):
                    data["steps_done"] = int(line[14:])
                elif line.startswith("- created: "):
                    data["created"] = line[11:]
                elif line.startswith("- last_touched: "):
                    data["last_touched"] = line[16:]
                elif line == "## Steps":
                    in_steps = True
                elif in_steps and line.startswith("- "):
                    step_text = line[2:].lstrip("✅⬜ ").strip()
                    if step_text:
                        steps.append(step_text)

            if not data.get("id") or not data.get("label"):
                return None

            return cls(
                id=data["id"],
                label=data["label"],
                steps=steps,
                steps_done=data.get("steps_done", 0),
                status=data.get("status", "in_progress"),
                created=data.get("created", date.today().isoformat()),
                last_touched=data.get("last_touched", date.today().isoformat()),
            )
        except Exception as exc:
            logger.debug(f"[TaskMemory] Could not parse task from md: {exc}")
            return None


class TaskMemory:
    """
    Tracks multi-step goals across sessions with persistent .md files.

    All tasks are stored as individual .md files:
      active/    — in-progress tasks
      completed/ — finished tasks (for reference)
    """

    def __init__(self):
        _ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        _COMPLETE_DIR.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, Task] = {}
        self._counter = 0
        self._load()

    # ── Create / Load ─────────────────────────────────────────────────────────

    def create_task(self, label: str, steps: list[str]) -> Task:
        """Create a new in-progress task and persist it to disk."""
        self._counter += 1
        task_id = f"task.{self._counter:03d}"
        task = Task(id=task_id, label=label, steps=steps)
        self._tasks[task_id] = task
        self._save_task(task)
        logger.info(f"[TaskMemory] Created task: {task_id} — {label}")
        return task

    def _load(self) -> None:
        """Load all active tasks from disk."""
        for path in sorted(_ACTIVE_DIR.glob("*.md")):
            task = Task.from_md(path.read_text(encoding="utf-8"))
            if task:
                self._tasks[task.id] = task
                # Track highest counter seen so new tasks get unique IDs
                try:
                    num = int(task.id.split(".")[-1])
                    if num > self._counter:
                        self._counter = num
                except (ValueError, IndexError):
                    pass
        logger.debug(f"[TaskMemory] Loaded {len(self._tasks)} active tasks.")

    def _save_task(self, task: Task) -> None:
        """Write task to the appropriate directory."""
        if task.status == "completed":
            path = _COMPLETE_DIR / f"{task.id}.md"
            # Remove from active
            active_path = _ACTIVE_DIR / f"{task.id}.md"
            active_path.unlink(missing_ok=True)
        else:
            path = _ACTIVE_DIR / f"{task.id}.md"
        path.write_text(task.to_md(), encoding="utf-8")

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_active(self) -> list[Task]:
        """Return all in-progress tasks."""
        return [t for t in self._tasks.values() if t.status == "in_progress"]

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def find_by_label(self, keywords: str) -> Optional[Task]:
        """Fuzzy search active tasks by label keywords."""
        kw = keywords.lower()
        for task in self.get_active():
            if kw in task.label.lower():
                return task
        return None

    def find_resumable(self, command: str) -> Optional[Task]:
        """
        Called by Orchestrator when user says 'continue' or 'resume'.
        Returns the most recently touched active task.
        """
        active = self.get_active()
        if not active:
            return None
        # Return most recently touched
        return max(active, key=lambda t: t.last_touched)

    # ── Mutation ──────────────────────────────────────────────────────────────

    def advance(self, task_id: str) -> Optional[str]:
        """
        Mark current step as done.
        Returns the next step label, or None if task is now complete.
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"[TaskMemory] advance() called for unknown task: {task_id}")
            return None

        task.steps_done += 1
        task.last_touched = date.today().isoformat()

        if task.is_complete:
            task.status = "completed"
            del self._tasks[task_id]
            logger.info(f"[TaskMemory] Task completed: {task_id}")
        else:
            logger.info(f"[TaskMemory] Task {task_id} progress: {task.progress_pct}% — next: {task.next_step}")

        self._save_task(task)
        return task.next_step if not task.is_complete else None

    def pause(self, task_id: str) -> None:
        """Mark task as paused."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "paused"
            self._save_task(task)

    def resume(self, task_id: str) -> None:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "in_progress"
            self._save_task(task)

    def fail(self, task_id: str) -> None:
        """Mark task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "failed"
            self._save_task(task)

    # ── LLM Context (RAG) ─────────────────────────────────────────────────────

    def as_llm_context(self) -> str:
        """
        Compact task context for LLM injection.
        Token budget: ~50 tokens.
        """
        active = self.get_active()
        if not active:
            return "(no active tasks)"

        parts = ["Active tasks:"]
        for task in active[:3]:  # at most 3 tasks
            parts.append(
                f"  - '{task.label}' ({task.progress_pct}% done, next: {task.next_step})"
            )
        return "\n".join(parts)
