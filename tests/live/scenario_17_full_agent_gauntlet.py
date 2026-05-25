"""
Scenario 17 — The Full Agent Gauntlet
=======================================
The most demanding end-to-end integration scenario for the Jarvis autonomous agent.

PHILOSOPHY
----------
Every step is expressed as a *user goal* only — no step-by-step instructions.
The agent must fully plan, navigate, type, scroll, switch apps, and verify
entirely on its own using the NLU + LLM Planner + SkillBus OODA loop.

DOMAINS EXERCISED
-----------------
  Phase A — System Intelligence
    A1 · Desktop environment reconnaissance
    A2 · Multi-app concurrent launch
    A3 · App-specific deep settings navigation with scrolling

  Phase B — Research & Web Foraging
    B1 · Browser search with autonomous query construction
    B2 · Multi-page scroll + DOM foraging
    B3 · Cross-tab research + link redirection
    B4 · Extract structured info from a live web page

  Phase C — File System & Notes
    C1 · File Explorer deep navigation + search
    C2 · Notepad multi-section document creation + save

  Phase D — System Tuning
    D1 · Network / Wi-Fi settings deep navigation
    D2 · Display personalization settings walk-through
    D3 · Sound output device enumeration

  Phase E — Cross-Domain Orchestration
    E1 · Copy info from browser → paste into Notepad
    E2 · Save notes to a specific user-named file
    E3 · Verify file exists via File Explorer

  Phase F — Cleanup & Memory Audit
    F1 · Close all open programs gracefully
    F2 · Ask for an activity summary from agent memory
    F3 · /new_session to wipe memory and confirm clean state

Run:
    python -m tests.live.scenario_17_full_agent_gauntlet
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus
from jarvis.input.adapters import MockTelegramAdapter
from jarvis.brain.message_formatter import MessageFormatter


_CHAT_ID = 777001
_USERNAME = "GauntletTester"
_NOTE_FILENAME = "gauntlet_research.txt"


class Scenario17(LiveScenario):
    scenario_name = "17 — The Full Agent Gauntlet"

    # ─────────────────────────────────────────────────────────────
    # Setup
    # ─────────────────────────────────────────────────────────────

    def setup(self):
        mem = MemoryManager()
        self.orch = Orchestrator(
            memory=mem, router=LLMRouter.from_config(), bus=SkillBus()
        )
        self.orch.boot()

        self.adapter = MockTelegramAdapter(log_path="logs/telegram_test.log")
        self.chat_id = _CHAT_ID
        self._stream_gen = self.adapter.stream()

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _simulate(self, text: str):
        """Send one user goal-message and collect the agent reply."""
        print(f"\n[GAUNTLET] 👤 USER >> {text}")
        self.adapter.simulate_message(text, chat_id=self.chat_id, username=_USERNAME)
        utterance = next(self._stream_gen)
        results = self.orch.process(utterance.text, source="telegram")
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        print(f"[GAUNTLET] 🤖 JARVIS <<\n{reply_text}")
        return results

    def _assert_replied(self, label: str):
        replies = self.adapter.get_replies()
        assert len(replies) > 0, f"No reply received for: {label}"

    # ─────────────────────────────────────────────────────────────
    # Phase A — System Intelligence
    # ─────────────────────────────────────────────────────────────

    def test_A1_recon(self):
        """Desktop recon: what apps are running, CPU/RAM state."""
        self._simulate(
            "Jarvis, scan my desktop and tell me what applications are currently open "
            "and give me a snapshot of my system resources right now."
        )
        self._assert_replied("A1 system recon")

    def test_A2_multi_launch(self):
        """Launch browser + Notepad + File Explorer in one shot."""
        self._simulate(
            "I need to start a research session. Open my web browser, a text editor "
            "for notes, and the file manager — all at once."
        )
        self._assert_replied("A2 multi-app launch")
        time.sleep(3)

    def test_A3_settings_deep_scroll(self):
        """Navigate deeply into Settings — Personalization → Background → Colors tab, scroll to find accent colour."""
        self._simulate(
            "I want to customise the look of my computer. Go into system personalisation, "
            "find the section that controls colours and accent settings, scroll through the "
            "options, and tell me what accent colour modes are available."
        )
        self._assert_replied("A3 deep settings scroll")

    # ─────────────────────────────────────────────────────────────
    # Phase B — Research & Web Foraging
    # ─────────────────────────────────────────────────────────────

    def test_B1_browser_research(self):
        """Open browser, search for Python asyncio best practices — no URL given."""
        self._simulate(
            "I want to learn about best practices for writing async Python code. "
            "Use my web browser to find good resources on this topic."
        )
        self._assert_replied("B1 browser research")
        time.sleep(2)

    def test_B2_scroll_and_forage(self):
        """Scroll results page to inspect listings, identify top 3 result titles."""
        self._simulate(
            "Scroll through the results page you just opened and list me the titles "
            "of the top 3 search results you can see."
        )
        self._assert_replied("B2 scroll + forage")

    def test_B3_click_redirect_new_tab(self):
        """Click the first promising link, then open GitHub trending in a new tab."""
        self._simulate(
            "Click the most relevant link from those results to open the article. "
            "Then, without closing it, open a second tab and navigate to GitHub's trending page."
        )
        self._assert_replied("B3 click + new tab")
        time.sleep(2)

    def test_B4_extract_page_info(self):
        """Extract the top trending repo name, stars, and language from GitHub trending."""
        self._simulate(
            "On the GitHub trending tab, find the number-one trending repository. "
            "Tell me its name, description, programming language, and star count."
        )
        self._assert_replied("B4 extract page info")

    # ─────────────────────────────────────────────────────────────
    # Phase C — File System & Notes
    # ─────────────────────────────────────────────────────────────

    def test_C1_file_explorer_deep(self):
        """Navigate File Explorer: This PC / C:/Users / <user> / Documents — list 5 files."""
        self._simulate(
            "In the file manager, navigate all the way into my personal Documents folder "
            "and tell me the names of the first 5 files or folders you can see there."
        )
        self._assert_replied("C1 file explorer deep nav")

    def test_C2_notepad_multiline_doc(self):
        """Write a structured research note with sections into Notepad."""
        self._simulate(
            f"Switch to my text editor and write a structured research note with three sections: "
            f"'Web Research Findings', 'GitHub Trend Insights', and 'Action Items'. "
            f"Fill each section with a brief placeholder summary of what we found. "
            f"Then save this document as '{_NOTE_FILENAME}' on my Desktop."
        )
        self._assert_replied("C2 notepad document + save")
        time.sleep(2)

    # ─────────────────────────────────────────────────────────────
    # Phase D — System Tuning
    # ─────────────────────────────────────────────────────────────

    def test_D1_wifi_settings(self):
        """Navigate to Network settings, find advanced Wi-Fi options."""
        self._simulate(
            "I want to understand my current network configuration. Open the network settings "
            "and find the advanced options for my Wi-Fi connection — tell me what properties "
            "are visible there."
        )
        self._assert_replied("D1 wi-fi deep nav")

    def test_D2_display_settings(self):
        """Navigate to Display settings, check resolution and scale."""
        self._simulate(
            "Navigate to my display settings and tell me what resolution and display scale "
            "percentage my main screen is set to."
        )
        self._assert_replied("D2 display settings")

    def test_D3_sound_devices(self):
        """Navigate to Sound settings, list available output devices."""
        self._simulate(
            "Check my sound settings and list all the output audio devices that my system "
            "currently has available."
        )
        self._assert_replied("D3 sound devices")

    # ─────────────────────────────────────────────────────────────
    # Phase E — Cross-Domain Orchestration
    # ─────────────────────────────────────────────────────────────

    def test_E1_browser_to_notepad(self):
        """Copy the URL of the current browser tab and paste it into Notepad."""
        self._simulate(
            "I want to save the URL of whatever web page I'm currently looking at into my "
            "research notes. Get the address from the browser and append it to the document "
            "already open in my text editor."
        )
        self._assert_replied("E1 browser→notepad cross-app")

    def test_E2_save_and_verify(self):
        """Save the Notepad file and verify it exists in File Explorer on the Desktop."""
        self._simulate(
            f"Make sure my notes document '{_NOTE_FILENAME}' is properly saved, then switch "
            f"to my file manager and navigate to my Desktop to confirm the file is there."
        )
        self._assert_replied("E2 save + verify in explorer")
        time.sleep(2)

    def test_E3_search_file_in_explorer(self):
        """Use File Explorer's search box to search for the file by name."""
        self._simulate(
            f"In the file manager, use the search feature to find the file '{_NOTE_FILENAME}' "
            f"anywhere on my computer and report back the full path where it's stored."
        )
        self._assert_replied("E3 file search in explorer")

    # ─────────────────────────────────────────────────────────────
    # Phase F — Cleanup & Memory Audit
    # ─────────────────────────────────────────────────────────────

    def test_F1_graceful_cleanup(self):
        """Close browser, Notepad, File Explorer, Settings — all in one pass."""
        self._simulate(
            "Our research session is complete. Please close the web browser, the text editor, "
            "the file manager, and any settings windows we had open to clean up the desktop."
        )
        self._assert_replied("F1 graceful cleanup")
        time.sleep(3)

    def test_F2_memory_audit(self):
        """Ask agent for a summary of the full session from its memory."""
        self._simulate(
            "Give me a full summary of everything we did in this session. "
            "Include which apps we opened, what we researched, and what files were created."
        )
        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for F2 memory audit"
        # Expect the summary to mention at least one of the key topics
        last_reply = replies[-1]["text"].lower()
        found_keywords = any(
            kw in last_reply
            for kw in ["browser", "notepad", "file", "research", "github", "settings", "network"]
        )
        assert found_keywords, (
            f"Memory audit did not reference any expected session topics. Got:\n{last_reply}"
        )

    def test_F3_new_session_slash(self):
        """Trigger /new_session via the slash handler and confirm clean response."""
        print("\n[GAUNTLET] 👤 USER >> /new_session")
        self.adapter.simulate_message(
            "/new_session", chat_id=self.chat_id, username=_USERNAME
        )
        utterance = next(self._stream_gen)

        # /new_session is handled by the slash handler — pass it through the orchestrator
        results = self.orch.process(utterance.text, source="telegram")
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        print(f"[GAUNTLET] 🤖 JARVIS <<\n{reply_text}")

        replies = self.adapter.get_replies()
        assert len(replies) > 0, "No reply received for /new_session"
        last = replies[-1]["text"].lower()
        assert (
            "wipe" in last or "clean" in last or "session" in last or "archive" in last or "memory" in last
        ), f"/new_session did not return expected confirmation. Got:\n{last}"

    # ─────────────────────────────────────────────────────────────
    # Step Registration
    # ─────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.steps = [
            # Phase A
            StepDef("A1_recon",               self.test_A1_recon,               timeout_s=30),
            StepDef("A2_multi_launch",         self.test_A2_multi_launch,         timeout_s=45),
            StepDef("A3_settings_deep_scroll", self.test_A3_settings_deep_scroll, timeout_s=60),
            # Phase B
            StepDef("B1_browser_research",     self.test_B1_browser_research,     timeout_s=60),
            StepDef("B2_scroll_forage",        self.test_B2_scroll_and_forage,    timeout_s=35),
            StepDef("B3_click_new_tab",        self.test_B3_click_redirect_new_tab, timeout_s=55),
            StepDef("B4_extract_info",         self.test_B4_extract_page_info,    timeout_s=40),
            # Phase C
            StepDef("C1_file_explorer_deep",   self.test_C1_file_explorer_deep,   timeout_s=45),
            StepDef("C2_notepad_doc",          self.test_C2_notepad_multiline_doc, timeout_s=75),
            # Phase D
            StepDef("D1_wifi_settings",        self.test_D1_wifi_settings,        timeout_s=50),
            StepDef("D2_display_settings",     self.test_D2_display_settings,     timeout_s=40),
            StepDef("D3_sound_devices",        self.test_D3_sound_devices,        timeout_s=40),
            # Phase E
            StepDef("E1_browser_to_notepad",   self.test_E1_browser_to_notepad,   timeout_s=55),
            StepDef("E2_save_verify",          self.test_E2_save_and_verify,      timeout_s=55),
            StepDef("E3_search_file",          self.test_E3_search_file_in_explorer, timeout_s=45),
            # Phase F
            StepDef("F1_cleanup",              self.test_F1_graceful_cleanup,     timeout_s=40),
            StepDef("F2_memory_audit",         self.test_F2_memory_audit,         timeout_s=35),
            StepDef("F3_new_session",          self.test_F3_new_session_slash,    timeout_s=30),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario17().run().passed else 1)
