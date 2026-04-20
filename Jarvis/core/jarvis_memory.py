"""
Jarvis Memory Manager
=====================
Reads and writes self-learning recipes to human-readable .md files
stored in the project-root `memory/` folder.

Memory file layout:
    memory/
        navigation.md   ← multi-step UI/Explorer navigation paths
        apps.md         ← how to open apps (especially unusual ones)
        folders.md      ← folder names → resolved real paths

Each recipe entry in a .md file looks like:
─────────────────────────────────────────────────────────
## open advanced display
- Preconditions: app=settings | location=display | window=Settings - Display
- Learned: 2026-04-09
- Success: 3
### Steps
1. open settings system
2. open settings display
3. scroll down
4. click advanced display
─────────────────────────────────────────────────────────

Design:
- Recipes are matched by command similarity (difflib) AND by precondition
  compatibility (app + location overlap), so "advanced display" from
  the desktop vs from the Settings page returns DIFFERENT recipes.
- The entire content of all .md files is included in the LLM system prompt
  so the LLM can reason about past learning even for novel commands.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from typing import Optional

from Jarvis.core.context_collector import ContextSnapshot

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
MEMORY_DIR = os.path.join(_PROJECT_ROOT, "memory")

MEMORY_FILES = {
    "navigation": os.path.join(MEMORY_DIR, "navigation.md"),
    "apps":       os.path.join(MEMORY_DIR, "apps.md"),
    "folders":    os.path.join(MEMORY_DIR, "folders.md"),
}


# ─────────────────────────────────────────────
#  Recipe Dataclass
# ─────────────────────────────────────────────
@dataclass
class MemoryRecipe:
    command: str                          # e.g. "open advanced display"
    steps: list[str]                      # ordered command strings to replay
    precondition_app: str = "any"         # e.g. "settings"
    precondition_location: str = "any"    # e.g. "display"
    precondition_window: str = "any"      # e.g. "Settings - Display"
    learned_date: str = ""
    success_count: int = 1
    category: str = "navigation"          # which .md file this belongs to

    def matches_context(self, snap: ContextSnapshot, threshold: float = 0.5) -> float:
        """
        Returns a score 0.0–1.0 of how well this recipe's preconditions
        match the current context snapshot.
        1.0 = perfect match, 0.0 = incompatible.
        """
        score = 0.0

        # App match (most important — weight 0.5)
        if self.precondition_app == "any":
            score += 0.3
        elif self.precondition_app == snap.active_app:
            score += 0.5
        elif self.precondition_app in snap.active_app or snap.active_app in self.precondition_app:
            score += 0.3

        # Location match (weight 0.4)
        if self.precondition_location == "any":
            score += 0.2
        elif self.precondition_location.lower() in snap.current_location.lower():
            score += 0.4
        elif snap.current_location.lower() in self.precondition_location.lower():
            score += 0.3

        # Window title match (weight 0.1)
        if self.precondition_window == "any":
            score += 0.1
        elif self.precondition_window.lower() in snap.active_window_title.lower():
            score += 0.1

        return min(score, 1.0)


# ─────────────────────────────────────────────
#  Memory Manager
# ─────────────────────────────────────────────
class MemoryManager:
    """
    Manages all memory recipe .md files.

    Usage:
        mem = MemoryManager()

        # Try to find a known recipe before calling LLM:
        recipe = mem.recall("open advanced display", context_snap)
        if recipe:
            for step in recipe.steps:
                engine.process(step)

        # After success, save so Jarvis learns:
        mem.save(command="open advanced display",
                 steps=["open settings system", "open settings display",
                        "scroll down", "click advanced display"],
                 snapshot=context_snap)
    """

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._ensure_memory_files()

    # ── Public: Recall ───────────────────────────
    def recall(
        self,
        command: str,
        snapshot: ContextSnapshot,
        command_threshold: float = 0.65,
        context_threshold: float = 0.4,
    ) -> Optional[MemoryRecipe]:
        """
        Search all memory files for a recipe that:
          1. Has a command similar to the given one (fuzzy string match)
          2. Has preconditions compatible with the current context snapshot

        Returns the best-matching MemoryRecipe, or None.
        """
        all_recipes = self._load_all_recipes()
        best: Optional[MemoryRecipe] = None
        best_score = 0.0

        cmd_lower = command.lower().strip()

        for recipe in all_recipes:
            # Command similarity
            cmd_sim = SequenceMatcher(None, cmd_lower, recipe.command.lower()).ratio()
            if cmd_sim < command_threshold:
                continue

            # Context compatibility
            ctx_score = recipe.matches_context(snapshot)
            if ctx_score < context_threshold:
                continue

            combined = cmd_sim * 0.6 + ctx_score * 0.4
            if combined > best_score:
                best_score = combined
                best = recipe

        if best:
            logger.info(
                f"[Memory] Recalled recipe for '{command}' "
                f"(cmd_sim={best_score:.2f}): {best.steps}"
            )
        else:
            logger.debug(f"[Memory] No recall match for '{command}'")

        return best

    # ── Public: Save ─────────────────────────────
    def save(
        self,
        command: str,
        steps: list[str],
        snapshot: ContextSnapshot,
        category: str = "navigation",
    ) -> None:
        """
        Save a successfully learned recipe to the appropriate .md file.
        If a recipe with the same command + precondition already exists,
        increment its success counter instead of duplicating.
        """
        target_file = MEMORY_FILES.get(category, MEMORY_FILES["navigation"])

        # Load existing recipes to check for duplicates
        existing = self._load_recipes_from_file(target_file)
        for r in existing:
            if (r.command.lower() == command.lower()
                    and r.precondition_app == (snapshot.active_app or "any")
                    and r.precondition_location == (snapshot.current_location or "any")):
                # Increment success count by rewriting the file
                r.success_count += 1
                self._rewrite_file(target_file, existing)
                logger.info(f"[Memory] Updated success count for '{command}' → {r.success_count}")
                return

        # New recipe
        recipe = MemoryRecipe(
            command=command,
            steps=steps,
            precondition_app=snapshot.active_app or "any",
            precondition_location=snapshot.current_location or "any",
            precondition_window=snapshot.active_window_title or "any",
            learned_date=date.today().isoformat(),
            success_count=1,
            category=category,
        )
        self._append_recipe(target_file, recipe)
        logger.info(f"[Memory] Saved new recipe: '{command}' → {steps}")

    # ── Public: Relevant memory as LLM context ───
    def get_relevant_context(
        self,
        command: str,
        snapshot: ContextSnapshot,
        top_n: int = 4,
    ) -> str:
        """
        Retrieval-Augmented Generation (RAG) approach:
        Extracts only the top N most relevant recipes from memory to keep the
        LLM context fast and laser-focused.

        Scores recipes based on:
        1. Text similarity (how close is the command to the recipe's title)
        2. Context similarity (is the user in the same app/location as the recipe)
        """
        all_recipes = self._load_all_recipes()
        if not all_recipes:
            return "(no memory yet)"

        scored_recipes = []
        cmd_lower = command.lower().strip()

        for recipe in all_recipes:
            # 1. Text Similarity
            # We want to catch semantic keywords. Simple SequenceMatcher ratio works nicely here,
            # but we can also use word intersection for robustness.
            recipe_cmd = recipe.command.lower()
            words_a = set(cmd_lower.split())
            words_b = set(recipe_cmd.split())
            
            # Use longer of the two: exact string match ratio OR word overlap ratio
            seq_sim = SequenceMatcher(None, cmd_lower, recipe_cmd).ratio()
            word_sim = len(words_a.intersection(words_b)) / max(len(words_a), 1)
            
            text_score = max(seq_sim, word_sim)

            # --- CRITICAL RULE ---
            # As requested by the user: "Matches that are contextually similar but not actually the same entity"
            # We must absolutely drop recipes that share NO semantic text similarity, 
            # even if the user is in the exact same app. This prevents confusing the LLM with completely
            # unrelated actions just because they both happen to be in 'Settings'.
            if text_score < 0.15:
                continue

            # 2. Context Similarity
            context_score = recipe.matches_context(snapshot)

            # Combined Score (Text is king, Context validates)
            final_score = (text_score * 0.6) + (context_score * 0.4)
            scored_recipes.append((final_score, recipe))

        # Sort highest score first
        scored_recipes.sort(key=lambda x: x[0], reverse=True)

        # Build output string of only the top N
        parts = []
        for score, recipe in scored_recipes[:top_n]:
            parts.append(self._recipe_to_md(recipe).strip())

        if not parts:
            return "(no highly relevant memories found for this context)"

        logger.info(f"[Memory] Fetched {len(parts)} highly relevant recipes for '{command}'.")
        return "\n\n".join(parts)

    # ── Internal: Load ───────────────────────────
    def _load_all_recipes(self) -> list[MemoryRecipe]:
        recipes = []
        for category, path in MEMORY_FILES.items():
            recipes.extend(self._load_recipes_from_file(path, category=category))
        return recipes

    def _load_recipes_from_file(self, path: str, category: str = "navigation") -> list[MemoryRecipe]:
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return self._parse_md(content, category)

    def _parse_md(self, content: str, category: str) -> list[MemoryRecipe]:
        """Parse memory .md file content into MemoryRecipe objects."""
        recipes = []
        # Split on level-2 headers (## command name)
        blocks = re.split(r"^## ", content, flags=re.MULTILINE)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            command = lines[0].strip()
            if not command:
                continue

            recipe = MemoryRecipe(command=command, steps=[], category=category)
            in_steps = False
            for line in lines[1:]:
                line = line.strip()
                if line.startswith("- Preconditions:"):
                    preconds = line.replace("- Preconditions:", "").strip()
                    # Parse: app=settings | location=display | window=...
                    for part in preconds.split("|"):
                        part = part.strip()
                        if part.startswith("app="):
                            recipe.precondition_app = part[4:].strip()
                        elif part.startswith("location="):
                            recipe.precondition_location = part[9:].strip()
                        elif part.startswith("window="):
                            recipe.precondition_window = part[7:].strip()
                elif line.startswith("- Learned:"):
                    recipe.learned_date = line.replace("- Learned:", "").strip()
                elif line.startswith("- Success:"):
                    try:
                        recipe.success_count = int(line.replace("- Success:", "").strip())
                    except ValueError:
                        pass
                elif line == "### Steps":
                    in_steps = True
                elif in_steps and re.match(r"^\d+\.", line):
                    step_text = re.sub(r"^\d+\.\s*", "", line).strip()
                    if step_text:
                        recipe.steps.append(step_text)

            if recipe.steps:
                recipes.append(recipe)

        return recipes

    # ── Internal: Write ──────────────────────────
    def _append_recipe(self, path: str, recipe: MemoryRecipe):
        with open(path, "a", encoding="utf-8") as f:
            f.write(self._recipe_to_md(recipe))

    def _rewrite_file(self, path: str, recipes: list[MemoryRecipe]):
        header = self._file_header(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
            for r in recipes:
                f.write(self._recipe_to_md(r))

    def _recipe_to_md(self, r: MemoryRecipe) -> str:
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(r.steps))
        return (
            f"\n## {r.command}\n"
            f"- Preconditions: app={r.precondition_app} | "
            f"location={r.precondition_location} | "
            f"window={r.precondition_window}\n"
            f"- Learned: {r.learned_date}\n"
            f"- Success: {r.success_count}\n"
            f"### Steps\n"
            f"{steps_text}\n"
        )

    def _file_header(self, path: str) -> str:
        name = os.path.splitext(os.path.basename(path))[0]
        return f"# Jarvis Memory — {name.title()}\n\n"

    def _ensure_memory_files(self):
        """Create empty memory files with headers if they don't exist."""
        headers = {
            MEMORY_FILES["navigation"]: (
                "# Jarvis Memory — Navigation\n\n"
                "<!-- Auto-generated. Each entry records how Jarvis navigated to something.\n"
                "     Preconditions capture the exact state Jarvis was in when it learned this. -->\n"
            ),
            MEMORY_FILES["apps"]: (
                "# Jarvis Memory — Apps\n\n"
                "<!-- Auto-generated. Records how Jarvis opens unusual apps. -->\n"
            ),
            MEMORY_FILES["folders"]: (
                "# Jarvis Memory — Folders\n\n"
                "<!-- Auto-generated. Maps spoken folder names to real paths. -->\n"
            ),
        }
        for path, header in headers.items():
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(header)
                logger.info(f"[Memory] Created {path}")
