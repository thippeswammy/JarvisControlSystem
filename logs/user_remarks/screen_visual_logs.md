F:\RunningProjects\JarvisControlSystem>python -m tests.live.scenario_99_new_test_cases --telegram --steps 01
2026-05-27 18:09:08,837 [INFO] tests.live.base_scenario:
============================================================
2026-05-27 18:09:08,837 [INFO] tests.live.base_scenario: ▶ SCENARIO: 99 — New Test Cases Suite
2026-05-27 18:09:08,838 [INFO] tests.live.base_scenario: ============================================================
2026-05-27 18:09:08,845 [INFO] jarvis.memory.graph_db: [GraphDB] Opened: F:\RunningProjects\JarvisControlSystem\memory\jarvis.db
2026-05-27 18:09:09,103 [INFO] jarvis.memory.semantic_encoder: [SemanticEncoder] Initialized with nomic-embed-text at http://localhost:11434/api/embeddings
2026-05-27 18:09:09,103 [INFO] jarvis.memory.memory_manager: [MemoryManager] DB: F:\RunningProjects\JarvisControlSystem\memory\jarvis.db
2026-05-27 18:09:09,104 [INFO] jarvis.memory.memory_manager: [MemoryManager] Warming semantic embedding cache...
2026-05-27 18:09:11,262 [INFO] jarvis.memory.layers.temporal: [TemporalMemory] Initialized with DB: F:\RunningProjects\JarvisControlSystem\memory\jarvis.db
2026-05-27 18:09:11,321 [INFO] jarvis.skills.skill_bus: [SkillBus] Discovered 35 skills: ['activate_window', 'ask_user', 'call_mcp_tool', 'chat_reply', 'click_browser_node', 'click_element', 'click_web_element', 'close_app', 'extract_browser_dom_tree', 'fill_browser_node', 'get_active_window_title', 'greet_user', 'log_analysis', 'maximize_window', 'minimize_window', 'navigate_location', 'open_app', 'open_brave_profile', 'power_action', 'press_key', 'run_agent', 'run_agent_pipeline', 'scroll_page', 'search_web', 'search_windows', 'session_activate', 'session_deactivate', 'set_brightness', 'set_volume', 'snap_window', 'switch_browser_tab', 'switch_window', 'system_status', 'type_text', 'verify_element_exists']
2026-05-27 18:09:11,321 [INFO] jarvis.brain.orchestrator: [Orchestrator] Skills: ['activate_window', 'ask_user', 'call_mcp_tool', 'chat_reply', 'click_browser_node', 'click_element', 'click_web_element', 'close_app', 'extract_browser_dom_tree', 'fill_browser_node', 'get_active_window_title', 'greet_user', 'log_analysis', 'maximize_window', 'minimize_window', 'navigate_location', 'open_app', 'open_brave_profile', 'power_action', 'press_key', 'run_agent', 'run_agent_pipeline', 'scroll_page', 'search_web', 'search_windows', 'session_activate', 'session_deactivate', 'set_brightness', 'set_volume', 'snap_window', 'switch_browser_tab', 'switch_window', 'system_status', 'type_text', 'verify_element_exists']
2026-05-27 18:09:11,327 [INFO] jarvis.agents.agent_bus: [AgentBus] Discovered 4 total agents: ['aggregator_agent', 'brave_agent', 'example_agent', 'planner_agent']
2026-05-27 18:09:11,328 [INFO] jarvis.mcp.mcp_bus: [MCPBus] Discovered 0 MCP servers: []
2026-05-27 18:09:11,329 [INFO] jarvis.brain.orchestrator: [Orchestrator] Boot complete
[Scenario 99] 📱 Live Telegram enabled! Chat ID: 5469322696
2026-05-27 18:09:12,125 [INFO] tests.live.base_scenario:   ▶ STEP  [01_context_persistence]

[Scenario 99] 👤 User >> Open Notepad and write 'Agent memory test'.
2026-05-27 18:09:13,915 [INFO] jarvis.perception.nlu: [NLU] Compound: ['open_app', 'type_text']
2026-05-27 18:09:15,953 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 1/10
2026-05-27 18:09:18,354 [INFO] jarvis.brain.planner: [Planner] Compound → single LLM call: "Open Notepad and write 'Agent memory test'."
2026-05-27 18:09:18,354 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:09:18,801 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:09:18,801 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:09:29,905 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: MIXED
2026-05-27 18:09:29,905 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: MIXED
2026-05-27 18:09:29,905 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: chat_reply({'message': "Opening Notepad and writing 'Agent memory test'.", '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:09:29,905 [INFO] jarvis.skills.builtins.chat_skill: [chat_skill] Delivering reply: "Opening Notepad and writing 'Agent memory test'."
2026-05-27 18:09:29,906 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: open_app({'target': 'notepad', '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:09:29,978 [INFO] jarvis.brain.state_manager: [WindowFocusController] Attempting dynamic focus for target: notepad
2026-05-27 18:09:30,396 [INFO] jarvis.utils.app_finder: [AppFinder] Discovered notepad via Registry: C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.2604.5.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe
2026-05-27 18:09:30,477 [INFO] jarvis.skills.builtins.app_skill: [app_skill] Discovered and launched: C:\Program Files\WindowsApps\Microsoft.WindowsNotepad_11.2604.5.0_x64__8wekyb3d8bbwe\Notepad\Notepad.exe
2026-05-27 18:09:32,812 [INFO] jarvis.skills.builtins.app_skill: [app_skill] Focused window by title: notepad
2026-05-27 18:09:32,812 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: type_text({'text': 'Agent memory test', '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:09:34,401 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 2/10
2026-05-27 18:09:38,241 [INFO] jarvis.brain.planner: [Planner] Compound → single LLM call: "Open Notepad and write 'Agent memory test'."
2026-05-27 18:09:38,241 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:09:38,710 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:09:38,710 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:09:44,849 [WARNING] jarvis.llm.backends.local_llm: [LocalLLM] JSON parse failure on attempt 1: Extra data: line 1 column 213 (char 212). Retrying self-correction...
2026-05-27 18:09:49,646 [WARNING] jarvis.llm.backends.local_llm: [LocalLLM] JSON parse failure on attempt 2: Extra data: line 1 column 213 (char 212). Retrying self-correction...
2026-05-27 18:09:54,495 [ERROR] jarvis.llm.backends.local_llm: [LocalLLM] JSON self-correction exhausted all attempts.
2026-05-27 18:09:54,497 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: CHAT
2026-05-27 18:09:54,497 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: CHAT
2026-05-27 18:09:54,497 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: chat_reply({'message': '{"type": "mixed", "message": "Opening Notepad and writing \'Agent memory test\'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}', '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:09:54,498 [INFO] jarvis.skills.builtins.chat_skill: [chat_skill] Delivering reply: '{"type": "mixed", "message": "Opening Notepad and writing \'Agent memory test\'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}'
2026-05-27 18:09:54,498 [INFO] jarvis.brain.orchestrator: [Orchestrator] ReAct loop reached conversational terminal action: chat_reply
2026-05-27 18:09:55,180 [INFO] jarvis.input.adapters: [MockTelegram] REPLY to 991199: 🤖 {"type": "mixed", "message": "Opening Notepad and writing 'Agent memory test'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}

[OK] *Discovered and launched: notepad*
[OK] *Typed: 'Agent memory test'*
[Scenario 99] 🤖 Jarvis <<
🤖 {"type": "mixed", "message": "Opening Notepad and writing 'Agent memory test'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}

[OK] *Discovered and launched: notepad*
[OK] *Typed: 'Agent memory test'*

[Scenario 99] 👤 User >> Minimize it.
2026-05-27 18:09:58,386 [INFO] jarvis.perception.nlu: [NLU] 'Minimize it.' → intent=llm_route, entities={'raw': 'minimize it.'}, safe_mode=False
2026-05-27 18:10:02,463 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 1/10
2026-05-27 18:10:06,247 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:10:06,748 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:10:06,748 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:10:11,697 [WARNING] jarvis.llm.backends.local_llm: [LocalLLM] JSON parse failure on attempt 1: Extra data: line 1 column 93 (char 92). Retrying self-correction...
2026-05-27 18:10:16,500 [WARNING] jarvis.llm.backends.local_llm: [LocalLLM] JSON parse failure on attempt 2: Extra data: line 1 column 213 (char 212). Retrying self-correction...
2026-05-27 18:10:21,308 [ERROR] jarvis.llm.backends.local_llm: [LocalLLM] JSON self-correction exhausted all attempts.
2026-05-27 18:10:21,311 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: CHAT
2026-05-27 18:10:21,311 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: CHAT
2026-05-27 18:10:21,312 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: chat_reply({'message': '{"type": "mixed", "message": "Opening Notepad and writing \'Agent memory test\'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}', '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:10:21,312 [INFO] jarvis.skills.builtins.chat_skill: [chat_skill] Delivering reply: '{"type": "mixed", "message": "Opening Notepad and writing \'Agent memory test\'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}'
2026-05-27 18:10:21,313 [INFO] jarvis.brain.orchestrator: [Orchestrator] ReAct loop reached conversational terminal action: chat_reply
2026-05-27 18:10:22,048 [INFO] jarvis.input.adapters: [MockTelegram] REPLY to 991199: 🤖 {"type": "mixed", "message": "Opening Notepad and writing 'Agent memory test'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}
[Scenario 99] 🤖 Jarvis <<
🤖 {"type": "mixed", "message": "Opening Notepad and writing 'Agent memory test'.", "steps": [{"skill": "open_app", "params": {"target": "notepad"}}, {"skill": "type_text", "params": {"text": "Agent memory test"}}]}}

[Scenario 99] 👤 User >> Bring it back and continue writing: 'The memory system works correctly.'
2026-05-27 18:10:25,315 [INFO] jarvis.perception.nlu: [NLU] Compound: ['llm_route', 'llm_route']
2026-05-27 18:10:25,315 [INFO] jarvis.perception.context_fusion: [ContextFusion] Ambiguous reference detected in command: "Bring it back and continue writing: 'The memory system works correctly.'". Routing to LLM for cognitive resolution.
2026-05-27 18:10:27,374 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 1/10
2026-05-27 18:10:31,162 [INFO] jarvis.brain.planner: [Planner] Compound → single LLM call: "Bring it back and continue writing: 'The memory system works correctly.'"
2026-05-27 18:10:31,162 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:10:31,664 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:10:31,664 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:10:36,070 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: CHAT
2026-05-27 18:10:36,070 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: CHAT
2026-05-27 18:10:36,070 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: chat_reply({'message': 'The memory system works correctly.', '_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:10:36,070 [INFO] jarvis.skills.builtins.chat_skill: [chat_skill] Delivering reply: 'The memory system works correctly.'
2026-05-27 18:10:36,071 [INFO] jarvis.brain.orchestrator: [Orchestrator] ReAct loop reached conversational terminal action: chat_reply
2026-05-27 18:10:36,736 [INFO] jarvis.input.adapters: [MockTelegram] REPLY to 991199: 🤖 The memory system works correctly.
[Scenario 99] 🤖 Jarvis <<
🤖 The memory system works correctly.

[Scenario 99] 👤 User >> Close it without saving.
2026-05-27 18:10:39,987 [INFO] jarvis.perception.nlu: [NLU] 'Close it without saving.' → intent=close_app, entities={'target': 'it without saving'}, safe_mode=False
2026-05-27 18:10:39,987 [INFO] jarvis.perception.context_fusion: [ContextFusion] Ambiguous reference detected in command: 'Close it without saving.'. Routing to LLM for cognitive resolution.
2026-05-27 18:10:44,066 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 1/10
2026-05-27 18:10:47,854 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:10:48,345 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:10:48,345 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:10:53,089 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: PLAN
2026-05-27 18:10:53,089 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: PLAN
2026-05-27 18:10:53,089 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: minimize_window({'_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:10:53,193 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 2/10
2026-05-27 18:10:55,627 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:10:56,080 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:10:56,080 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:11:00,826 [INFO] jarvis.llm.llm_router: [Decision] Mode identified: PLAN
2026-05-27 18:11:00,826 [INFO] jarvis.brain.planner: [Decision] LLM response mode identified: PLAN
2026-05-27 18:11:00,826 [INFO] jarvis.skills.skill_bus: [SkillBus] Dispatching: minimize_window({'_interface': 'telegram', '_agent_bus': <jarvis.agents.agent_bus.AgentBus object at 0x000001FE1D9BC040>, '_mcp_bus': <jarvis.mcp.mcp_bus.MCPBus object at 0x000001FE1F108970>, '_router': <jarvis.llm.llm_router.LLMRouter object at 0x000001FE1D9BC730>})
2026-05-27 18:11:00,928 [INFO] jarvis.brain.orchestrator: [Orchestrator] Starting ReAct iteration 3/10
2026-05-27 18:11:06,451 [INFO] jarvis.brain.planner: [Brain] Routing to cognitive layer for intent: 'llm_route'
2026-05-27 18:11:06,926 [INFO] jarvis.brain.planner: [Cognitive] Requesting decision from LLM backend...
2026-05-27 18:11:06,927 [INFO] jarvis.llm.llm_router: [Cognitive] Requesting decision from local/ollama(gemma3:4b)...
2026-05-27 18:11:12,126 [ERROR] tests.regression.crash_detector: [CrashDetector] TIMEOUT: Step '01_context_persistence' timed out after 120s
2026-05-27 18:11:12,127 [INFO] tests.live.base_scenario:   ❌ FAIL [01_context_persistence] (120.00s)
2026-05-27 18:11:12,127 [ERROR] tests.live.base_scenario:        Error: Step '01_context_persistence' timed out after 120s
2026-05-27 18:11:12,885 [INFO] tests.live.base_scenario:
❌ FAIL [99 — New Test Cases Suite] 0/1 passed, 1 failed, 0 skipped

F:\RunningProjects\JarvisControlSystem>