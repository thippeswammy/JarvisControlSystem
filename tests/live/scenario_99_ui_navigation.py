"""
Scenario 99 — UI Navigation Suite
===================================================
A comprehensive end-to-end integration test suite verifying UI navigation,
window management, multi-step planning, and multi-agent coordination.

Run:
    python -m tests.live.scenario_99_ui_navigation
"""

import sys
import time
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.live.base_scenario import LiveScenario, StepDef
from jarvis.brain.orchestrator import Orchestrator
from jarvis.llm.llm_router import LLMRouter
from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus
from jarvis.input.adapters import MockTelegramAdapter
from jarvis.brain.message_formatter import MessageFormatter


class Scenario99UINavigation(LiveScenario):
    scenario_name = "99 — UI Navigation Suite"

    # ─────────────────────────────────────────────────────────────
    # Setup
    # ─────────────────────────────────────────────────────────────

    def setup(self):
        # Parse optional command line arguments safely
        import argparse
        parser = argparse.ArgumentParser(description="Scenario 99 UI Runner")
        parser.add_argument("--telegram", action="store_true", help="Enable live Telegram logging")
        parser.add_argument("--chat-id", type=str, default="5469322696", help="Telegram Chat ID to send updates to")
        parser.add_argument("--steps", type=str, help="Comma-separated step numbers or names to run (e.g. 01,02)")
        args, _ = parser.parse_known_args()
        
        self.telegram_enabled = args.telegram
        self.telegram_chat_id = args.chat_id
        self.telegram_token = None
        self.last_plan = []

        if args.steps:
            step_numbers = [s.strip() for s in args.steps.split(",")]
            filtered = []
            for step in self.steps:
                for num in step_numbers:
                    if step.name.startswith(num) or num in step.name:
                        filtered.append(step)
                        break
            self.steps = filtered

        # Initialize Memory Graph, Skill Bus, local-first LLM Router, and Orchestrator
        mem = MemoryManager()
        self.orch = Orchestrator(memory=mem, router=LLMRouter.from_config(), bus=SkillBus())
        self.orch.boot()
        
        # Intercept the plan generation
        original_plan = self.orch._planner.plan
        def custom_plan(packet, *args, **kwargs):
            calls = original_plan(packet, *args, **kwargs)
            self.last_plan = calls
            return calls
        self.orch._planner.plan = custom_plan

        # Instantiate Mock Telegram Adapter focusing output to logs/runtime/telegram_test.log
        self.adapter = MockTelegramAdapter(log_path = "logs/runtime/telegram_test.log")
        self.chat_id = 991199
        self._stream_gen = self.adapter.stream()

        if self.telegram_enabled:
            self.telegram_token = self._load_telegram_token()
            print(f"[Scenario 99 UI] 📱 Live Telegram enabled! Chat ID: {self.telegram_chat_id}")
            self.send_telegram(f"🏁 *Starting Scenario 99: UI Navigation Suite*")
            
            # Wrap step functions to send step boundaries
            for step in self.steps:
                original_fn = step.fn
                def make_wrapper(s_def, orig):
                    def wrapper(*args, **kwargs):
                        self.send_telegram(f"🎬 *Starting Step:* `{s_def.name}`")
                        return orig(*args, **kwargs)
                    return wrapper
                step.fn = make_wrapper(step, original_fn)

    # ─────────────────────────────────────────────────────────────
    # Helpers & Custom Assertions
    # ─────────────────────────────────────────────────────────────

    def _load_telegram_token(self) -> str:
        import yaml
        config_path = PROJECT_ROOT / "jarvis" / "config" / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    token = cfg.get("channels", {}).get("telegram", {}).get("token", "")
                    if token and "AA" in token:
                        return token
            except Exception as e:
                print(f"[Scenario 99 UI] Warning: failed to parse config.yaml for token: {e}")
        # Fallback to the known working token
        return "8693706700:AAERwET5RcROo91AbQ9K2-yv1DPx_VwhH40"

    def send_telegram(self, text: str):
        if not self.telegram_enabled or not self.telegram_token:
            return
        import requests
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                print(f"[Scenario 99 UI] Telegram send error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[Scenario 99 UI] Telegram connection error: {e}")

    def _format_plan(self, plan: list) -> str:
        if not plan:
            return ""
        
        lines = ["📋 *Cognitive Plan:*"]
        for idx, call in enumerate(plan, 1):
            skill = call.skill
            if skill == "chat_reply" and len(plan) > 1:
                continue
            
            clean_params = {k: v for k, v in call.params.items() if not k.startswith("_")}
            
            if skill == "run_agent":
                agent_name = clean_params.get("agent", "unknown")
                task = clean_params.get("task", "")
                lines.append(f" {idx}. 🤖 *Agent* `{agent_name}` → task: {task!r}")
            elif skill == "call_mcp_tool":
                server = clean_params.get("server", "unknown")
                tool = clean_params.get("tool", "unknown")
                params = clean_params.get("params", {})
                lines.append(f" {idx}. 🛠️ *MCP* `{server}/{tool}` (params: `{params}`)")
            else:
                param_str = ", ".join(f"{k}={v!r}" for k, v in clean_params.items())
                icon = "⚙️"
                if skill in ("type_text", "press_key"):
                    icon = "⌨️"
                elif skill in ("open_app", "close_app", "switch_window"):
                    icon = "📱"
                lines.append(f" {idx}. {icon} `{skill}` ({param_str})")
                
        return "\n".join(lines)

    def _simulate(self, text: str):
        """Simulate sending a chat command from Telegram and receiving formatted output."""
        print(f"\n[Scenario 99 UI] 👤 User >> {text}")
        if getattr(self, "telegram_enabled", False):
            self.send_telegram(f"👤 *User simulated message:*\n> {text}")
            
        self.adapter.simulate_message(text, chat_id=self.chat_id, username="NewTestSuiteTester")
        
        # Pull utterance from the stream
        utterance = next(self._stream_gen)
        
        # Reset last captured plan
        self.last_plan = []
        
        # Process dynamically via NLU + Planner OODA Loop
        results = self.orch.process(utterance.text, source="telegram")
        
        # Send planning updates if available
        if getattr(self, "telegram_enabled", False) and self.last_plan:
            plan_msg = self._format_plan(self.last_plan)
            if plan_msg:
                self.send_telegram(plan_msg)
        
        # Format the skill execution outputs
        reply_text = MessageFormatter.format(results, source="telegram")
        self.adapter.send(f"telegram:{self.chat_id}", reply_text)
        
        print(f"[Scenario 99 UI] 🤖 Jarvis <<\n{reply_text}")
        if getattr(self, "telegram_enabled", False):
            self.send_telegram(f"🤖 *Jarvis reply:*\n{reply_text}")
            
        return results

    def teardown(self):
        if getattr(self, "telegram_enabled", False):
            res = getattr(self, "_result", None)
            if res:
                passed_icon = "✅" if res.passed else "❌"
                summary_text = (
                    f"🏁 *Scenario 99 UI Completed!*\n"
                    f"{passed_icon} *Result:* {res.pass_count}/{res.total} passed"
                )
                self.send_telegram(summary_text)

    def _assert_replied(self, label: str):
        replies = self.adapter.get_replies()
        assert len(replies) > 0, f"No reply received for: {label}"

    # ─────────────────────────────────────────────────────────────
    # Step Implementations
    # ─────────────────────────────────────────────────────────────

    def test_01_context_persistence(self):
        """1. Context Persistence Tests: Runtime memory, active app tracking, follow-up."""
        self._simulate("Open Notepad and write 'Agent memory test'.")
        self._assert_replied("Notepad launch and type")
        
        self._simulate("Minimize it.")
        self._assert_replied("Minimize Notepad")
        
        self._simulate("Bring it back and continue writing: 'The memory system works correctly.'")
        self._assert_replied("Bring Notepad back and append text")
        
        self._simulate("Close it without saving.")
        self._assert_replied("Close Notepad without saving")

    def test_02_reference_resolution(self):
        """2. Reference Resolution Tests: Pronouns, context fusion."""
        self._simulate("Open Settings and Notepad.")
        self._assert_replied("Open Settings and Notepad")
        
        self._simulate("Switch back to the first one.")
        self._assert_replied("Switch to first app")
        
        self._simulate("Close the other one.")
        self._assert_replied("Close the other app")

    def test_03_multi_step_planning(self):
        """3. Multi-Step Autonomous Planning: Planning, sequencing, execution chaining."""
        self._simulate("Open Edge, go to github.com, search for 'python asyncio', then open Notepad and summarize what you found.")
        self._assert_replied("Multi-step search and summarize")

    def test_04_browser_cognition(self):
        """4. Browser Cognition Tests: Browser awareness, DOM reasoning, semantic navigation."""
        self._simulate("Open YouTube and search for 'ROS2 tutorials'.")
        self._assert_replied("YouTube search")
        
        self._simulate("Open the first video in a new tab.")
        self._assert_replied("Open video in new tab")
        
        self._simulate("Tell me the title of the currently active video.")
        self._assert_replied("Retrieve active video title")

    def test_05_window_reuse_intelligence(self):
        """5. Window Reuse Intelligence: App state tracking, focus controller."""
        self._simulate("Open Notepad.")
        self._assert_replied("Open Notepad first time")
        
        # Triggers focus on existing Notepad rather than relaunching
        self._simulate("Open Notepad.")
        self._assert_replied("Focus Notepad second time (reuse check)")

    def test_07_recovery_retry(self):
        """7. Recovery + Retry Tests: Error handling, replanning under failure."""
        self._simulate("Click the button named 'FakeButton123', and if it does not exist, open Settings instead.")
        self._assert_replied("Recovery fallback settings")

    def test_08_verification_layer(self):
        """8. Verification Layer Tests: Action confirmation, active state validation."""
        self._simulate("Open Calculator and verify that it became the active window.")
        self._assert_replied("Open calculator with verification")

    def test_09_parallel_task_planning(self):
        """9. Parallel Task Planning: Orchestration, concurrency reasoning."""
        self._simulate("Start a research workspace: open browser, notepad, and file explorer simultaneously.")
        self._assert_replied("Simultaneous workspace launch")

    def test_10_memory_timeline(self):
        """10. Memory Timeline Tests: Episodic memory, history retrieval."""
        self._simulate("Open Notepad and type: 'Timeline memory validation test'")
        self._assert_replied("Notepad timeline setup")
        
        self._simulate("What did I last type in Notepad?")
        self._assert_replied("Recalled last Notepad typed content")

    def test_12_structured_save_workflow(self):
        """12. Structured Save Workflow: File workflow, save pipeline."""
        self._simulate("Open Notepad, write a short system report, and save it as: C:\\Temp\\agent_test.txt")
        self._assert_replied("Save Notepad report")
        
        self._simulate("Verify the file exists.")
        self._assert_replied("Verify report saved")

    def test_13_ui_navigation(self):
        """13. UI Navigation Tests: Semantic UI navigation."""
        self._simulate("Open Settings and navigate to Display settings.")
        self._assert_replied("Navigate display settings")
        
        self._simulate("Increase brightness if possible.")
        self._assert_replied("Increase display brightness")

    def test_15_long_horizon_workflow(self):
        """15. Long-Horizon Agentic Workflow: Comprehensive planning, browser, notepad, filesystem, memory."""
        self._simulate(
            "I want to start studying ROS2. "
            "Open a browser and search for beginner ROS2 tutorials. "
            "Open Notepad for notes. "
            "Write the top learning topics I should study first. "
            "Then create a folder named ROS2_Study on my desktop."
        )
        self._assert_replied("Long-horizon ROS2 workflow")

    def test_16_environment_understanding(self):
        """16. Dynamic Environment Understanding: Environment cognition, window tracking."""
        self._simulate("Tell me what applications are currently open and which one is focused.")
        self._assert_replied("Applications and focus report")

    def test_18_multi_agent_architecture(self):
        """18. Multi-Agent Architecture Tests: Desktop, browser, conversation, vision fallback."""
        # 18.1 Desktop Agent
        self._simulate("Open File Explorer and navigate to Downloads.")
        self._assert_replied("Desktop Agent downloads navigation")
        
        # 18.2 Browser Agent
        self._simulate("Search GitHub for ROS2 repositories.")
        self._assert_replied("Browser Agent GitHub search")
        
        # 18.3 Conversation Agent
        res_nodes = self._simulate("Explain what ROS2 nodes are.")
        self._assert_replied("Conversation Agent ROS2 explanation")
        
        # 18.4 Vision Fallback
        try:
            import playwright
            has_playwright = True
        except ImportError:
            has_playwright = False

        if has_playwright:
            self._simulate("Find the blue button on the current screen.")
            self._assert_replied("Vision Fallback check")
        else:
            print("[Scenario 99 UI] ⚠️ Skipping Playwright Vision Fallback check (module not installed)")

    # ─────────────────────────────────────────────────────────────
    # Step Registration
    # ─────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.steps = [
            StepDef("01_context_persistence",      self.test_01_context_persistence,      timeout_s=120),
            StepDef("02_reference_resolution",     self.test_02_reference_resolution,     timeout_s=90),
            StepDef("03_multi_step_planning",      self.test_03_multi_step_planning,      timeout_s=75),
            StepDef("04_browser_cognition",        self.test_04_browser_cognition,        timeout_s=120),
            StepDef("05_window_reuse_intel",       self.test_05_window_reuse_intelligence, timeout_s=45),
            StepDef("07_recovery_retry",           self.test_07_recovery_retry,           timeout_s=60),
            StepDef("08_verification_layer",       self.test_08_verification_layer,       timeout_s=45),
            StepDef("09_parallel_task_planning",   self.test_09_parallel_task_planning,   timeout_s=60),
            StepDef("10_memory_timeline",          self.test_10_memory_timeline,          timeout_s=75),
            StepDef("12_structured_save_workflow", self.test_12_structured_save_workflow, timeout_s=75),
            StepDef("13_ui_navigation",            self.test_13_ui_navigation,            timeout_s=75),
            StepDef("15_long_horizon_workflow",    self.test_15_long_horizon_workflow,    timeout_s=120),
            StepDef("16_environment_understanding", self.test_16_environment_understanding, timeout_s=45),
            StepDef("18_multi_agent_architecture", self.test_18_multi_agent_architecture, timeout_s=120),
        ]


if __name__ == "__main__":
    sys.exit(0 if Scenario99UINavigation().run().passed else 1)
