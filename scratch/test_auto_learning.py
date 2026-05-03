import os
import sys

# Add project root to sys.path so we can import jarvis
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jarvis.memory.memory_manager import MemoryManager
from jarvis.skills.skill_bus import SkillBus, SkillCall, SkillResult
from jarvis.llm.llm_router import LLMRouter
from jarvis.brain.orchestrator import Orchestrator

class MockRouter(LLMRouter):
    def __init__(self, plan_to_return):
        self.plan_to_return = plan_to_return
        
    def route(self, prompt: str, memory_context: str = "") -> list[SkillCall]:
        return self.plan_to_return

def test_auto_learning():
    mem = MemoryManager(":memory:")
    bus = SkillBus()
    from jarvis.skills.skill_decorator import skill
    
    @skill(triggers=["set brightness"])
    def set_brightness(params, **kwargs):
        return SkillResult(success=True)

    @skill(triggers=["type text"], is_cognitive=True)
    def type_text(params, **kwargs):
        return SkillResult(success=True)

    bus.register(set_brightness)
    bus.register(type_text)
    
    # 1. Test learning a safe macro
    router = MockRouter([SkillCall(skill="set_brightness", params={"direction": "down"}, source="llm")])
    orch = Orchestrator(mem, router, bus)
    orch.boot()
    
    print("\n--- Test 1: Learn Safe Macro ---")
    utterance_1 = "dim the visual output by a lot"
    orch.process(utterance_1, source="text")
    
    # Verify the memory has it
    path = mem.recall(utterance_1)
    if path and getattr(path.edges[0], "action_type", "") == "macro":
        print(f"Success! Macro learned for '{utterance_1}'")
        import json
        print(f"Stored calls: {path.edges[0].action_params.get('calls')}")
    else:
        print("Failed to learn macro.")

    # 2. Test semantic match on learned macro
    print("\n--- Test 2: Semantic Match on Reflex ---")
    utterance_2 = "lower the visual output"
    path2 = mem.recall(utterance_2)
    if path2 and path2.edges[0].id == path.edges[0].id:
        print(f"Success! Semantic match found for '{utterance_2}' hitting the reflex.")
    else:
        print("Failed semantic match.")

    # 3. Test unsafe skill rejection
    print("\n--- Test 3: Reject Unsafe Cognitive Macro ---")
    router.plan_to_return = [SkillCall(skill="type_text", params={"text": "hello"}, source="llm")]
    utterance_3 = "draft an email saying hello"
    orch.process(utterance_3, source="text")
    
    path3 = mem.recall(utterance_3)
    if path3 is None:
        print(f"Success! Unsafe macro was correctly skipped.")
    else:
        print("Failed. Unsafe macro was learned!")

if __name__ == "__main__":
    test_auto_learning()
