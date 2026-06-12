import logging
import yaml
import sys
from pathlib import Path
from typing import Optional

from jarvis.gateway.session_manager import SessionManager
from jarvis.gateway.channel_manager import ChannelManager
from jarvis.memory.memory_manager import MemoryManager
from jarvis.llm.llm_router import LLMRouter
from jarvis.skills.skill_bus import SkillBus

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class GatewayDaemon:
    """
    The heart of the Jarvis Ecosystem.
    Manages shared resources, parallel channels, and user sessions.
    """
    def __init__(self, config_path: str = "", profile: str = "default"):
        if config_path:
            self._config_path = config_path
        elif profile and profile != "default":
            self._config_path = str(_PROJECT_ROOT / "jarvis" / "config" / "profiles" / f"{profile}.yaml")
        else:
            self._config_path = str(_PROJECT_ROOT / "jarvis" / "config" / "config.yaml")
        
        self._cfg = {}
        
        # Core Shared Components
        self.memory: Optional[MemoryManager] = None
        self.router: Optional[LLMRouter] = None
        self.bus: Optional[SkillBus] = None
        self.agent_bus = None
        self.mcp_bus = None
        
        # Managers
        self.session_mgr: Optional[SessionManager] = None
        self.channel_mgr: Optional[ChannelManager] = None
        
        self._running = False

    def bootstrap(self):
        """Initialize all shared components from config."""
        if self.memory is not None:
            logger.debug("[Gateway] Already bootstrapped. Skipping.")
            return
        logger.info(f"[Gateway] Bootstrapping from {self._config_path}")
        
        from jarvis.config.config_manager import ConfigManager
        self._cm = ConfigManager(self._config_path)
        self._cfg = self._cm.show(mask_secrets=False)

        # 0. Ensure Ollama is running
        from jarvis.utils.ollama_utils import enable_auto_start, ensure_ollama_running
        enable_auto_start(True)
        ensure_ollama_running()

        # 1. Memory
        db_cfg = self._cfg.get("memory", {}).get("graph_db", {})
        db_path = db_cfg.get("path", "memory/jarvis.db")
        self.memory = MemoryManager(db_path=str(_PROJECT_ROOT / db_path))
        
        # 2. LLM Router
        self.router = LLMRouter.from_config(config_path=self._config_path)
        
        # 3. Skill Bus
        self.bus = SkillBus()
        self.bus.discover() # Discover skills on startup
        
        # 3b. Agent Bus & MCP Bus
        from jarvis.agents.agent_bus import AgentBus
        from jarvis.mcp.mcp_bus import MCPBus
        self.agent_bus = AgentBus(self.memory)
        self.agent_bus.discover()
        self.mcp_bus = MCPBus()
        self.mcp_bus.discover()
        
        # Phase 6: Verification Loop (Hardware/UI state tracking)
        from jarvis.memory.state_harvester import StateHarvester
        from jarvis.memory.state_comparator import StateComparator
        from jarvis.brain.recovery import RecoveryStrategies
        from jarvis.brain.verification_loop import VerificationLoop
        
        self.harvester = StateHarvester()
        self.vloop = VerificationLoop(
            harvester=self.harvester,
            comparator=StateComparator(),
            recovery=RecoveryStrategies(bus=self.bus)
        )
        
        # 4. Session Manager
        self.session_mgr = SessionManager(
            memory=self.memory, 
            router=self.router, 
            bus=self.bus,
            gateway=self,
            vloop=self.vloop
        )
        
        # 5. Channel Manager
        self.channel_mgr = ChannelManager(session_mgr=self.session_mgr)
        self._setup_channels()
        
        # 6. Seed procedural memory
        from jarvis.memory.layers.procedural import ProceduralMemory
        proc = ProceduralMemory(self.memory.get_db())
        proc.seed_settings_graph()
        
        logger.info("[Gateway] Bootstrap complete")

    def _setup_channels(self):
        """Initialize channels based on config."""
        from jarvis.input.adapters import CLIAdapter, TelegramAdapter, MockTelegramAdapter
        
        chan_cfg = self._cfg.get("channels", {})
        
        # CLI Channel
        if chan_cfg.get("cli", {}).get("enabled", True):
            self.channel_mgr.add_channel(CLIAdapter())
            
        # Telegram Channel
        tel_cfg = chan_cfg.get("telegram", {})
        if tel_cfg.get("enabled", False):
            # Resolve token (expand ${ENV_VAR})
            token = tel_cfg.get("token", "")
            if token.startswith("${") and token.endswith("}"):
                import os
                token = os.environ.get(token[2:-1], "")
            
            adapter = TelegramAdapter(
                token=token,
                allowed_chat_ids=tel_cfg.get("allowed_chat_ids", [])
            )
            self.channel_mgr.add_channel(adapter)
            
        # Mock Telegram
        if chan_cfg.get("telegram_test", {}).get("enabled", False):
            self.channel_mgr.add_channel(MockTelegramAdapter())

    def start(self):
        """Start the gateway and all channels."""
        if not self.memory:
            self.bootstrap()
            
        self._running = True
        logger.info("[Gateway] Starting all channels...")
        self.channel_mgr.start_all()

    def stop(self):
        """Shut down the gateway and all channels."""
        self._running = False
        if self.channel_mgr:
            self.channel_mgr.stop_all()
        logger.info("[Gateway] Stopped.")

    def status(self) -> dict:
        """Return system health and status summary."""
        return {
            "running": self._running,
            "channels": self.channel_mgr.list_channels() if self.channel_mgr else [],
            "sessions": len(self.session_mgr.list_sessions()) if self.session_mgr else 0,
            "memory": self.memory.get_db_path() if self.memory else "unknown"
        }

    def reload(self):
        """Reload configuration and refresh components."""
        logger.info("[Gateway] Reloading configuration...")
        self._cm.load()
        self._cfg = self._cm.show(mask_secrets=False)
        # In a real scenario, we'd selectively update components
        # For now, just re-bootstrap (some components might not like double init)
        self.bootstrap()
