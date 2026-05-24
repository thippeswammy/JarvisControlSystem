"""
Iterative OODA (Observe-Orient-Decide-Act) Execution Loop
==========================================================
Enables state-driven execution. Rather than running static linear steps,
this runner continuously observes the current UI state, diagnoses errors
(e.g., minimized windows, wrong focus, fail-safes), decides on corrected
corrective actions, executes them, and loops until the target goal is verified.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from jarvis.perception.context_harvester import ContextHarvester
from jarvis.perception.perception_packet import PerceptionPacket, Utterance
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult

logger = logging.getLogger(__name__)

class OODARunner:
    """State-driven executor implementing a fully agentic OODA loop."""
    
    def __init__(self, orchestrator: Any, max_cycles: int = 5):
        self.orchestrator = orchestrator
        self.bus = orchestrator._bus
        self.harvester = ContextHarvester(episodic=orchestrator._episodic)
        self.max_cycles = max_cycles

    def run_goal(self, goal: str) -> List[SkillResult]:
        """Runs the agentic OODA loop to achieve the user's high-level goal."""
        logger.info(f"[OODARunner] Starting state-driven OODA loop for goal: {goal!r}")
        
        cycle = 0
        results = []
        
        while cycle < self.max_cycles:
            cycle += 1
            logger.info(f"[OODARunner] === Cycle {cycle}/{self.max_cycles} ===")
            
            # 1. OBSERVE: Capture current system and UI tree state
            snapshot = self.harvester.capture()
            logger.info(f"[OODARunner] OBSERVE: Active App={snapshot.active_app!r}, Window Title={snapshot.active_window_title!r}")
            
            # 2. ORIENT: Diagnose errors or unexpected states
            # E.g., check if a crucial app is minimized or UIA is lost
            error_diagnosed = False
            if snapshot.active_app == "unknown" and cycle > 1:
                logger.warning("[OODARunner] ORIENT: Lost active window context. Focus recovery triggered.")
                # Self-correction: try restoring last known focus
                from jarvis.brain.state_manager import WindowFocusController
                WindowFocusController.focus_window("notepad") # fallback attempt
                error_diagnosed = True
                time.sleep(0.5)
                continue

            # 3. DECIDE: Compute the next logical corrective actions
            packet = self.orchestrator._nlu.parse(Utterance(text=goal), app_context=snapshot.active_app)
            packet.context_snapshot = snapshot
            
            # Request plan from Planner based on enriched current state
            plan = self.orchestrator._planner.plan(packet)
            if not plan:
                logger.info("[OODARunner] DECIDE: Goal achieved or no further actions decided. Terminating loop.")
                break
                
            logger.info(f"[OODARunner] DECIDE: Planned {len(plan)} SkillCalls: {[c.skill for c in plan]}")

            # 4. ACT & VERIFY: Execute and run post-execution checks
            cycle_success = True
            for call in plan:
                logger.info(f"[OODARunner] ACT: Dispatching {call.skill} with params: {call.params}")
                
                # Wrap execution in VerificationLoop
                if self.orchestrator._verification_loop:
                    res = self.orchestrator._verification_loop.execute_and_verify(
                        call=call,
                        bus=self.bus,
                        packet=packet,
                        snapshot=snapshot,
                        learner=self.orchestrator._learner,
                    )
                else:
                    res = self.bus.dispatch(call)
                
                results.append(res)
                
                # Check for failure or fail-safe triggers
                if not res.success:
                    logger.warning(f"[OODARunner] Action failed: {call.skill}. Output: {res.message}")
                    cycle_success = False
                    
                    # Self-correction: if settings navigation failed, try re-launching settings
                    if call.skill == "navigate_location" and snapshot.active_app == "settings":
                        logger.info("[OODARunner] Self-Correction: Navigation failed in Settings. Re-focusing home...")
                        from jarvis.brain.state_manager import WindowFocusController
                        WindowFocusController.focus_window("settings")
                    break

            if cycle_success:
                logger.info("[OODARunner] VERIFY: All actions in current cycle verified successfully.")
                # If we've finished all actions and state is stable, we are done
                break
                
            # Wait for UI to settle before next cycle
            time.sleep(0.5)

        logger.info(f"[OODARunner] OODA execution loop complete after {cycle} cycles.")
        return results
