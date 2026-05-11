import logging
import threading
from typing import Dict, List, Optional

from jarvis.gateway.session_manager import SessionManager
from jarvis.input.adapters import ChannelAdapter
from jarvis.brain.message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

class ChannelManager:
    """
    Manages parallel input/output channels.
    Each channel runs in its own thread.
    """
    def __init__(self, session_mgr: SessionManager):
        self._session_mgr = session_mgr
        self._channels: Dict[str, ChannelAdapter] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._running = False

    def add_channel(self, adapter: ChannelAdapter):
        self._channels[adapter.name] = adapter
        logger.info(f"[ChannelManager] Added channel: {adapter.name}")

    def start_all(self):
        self._running = True
        for name, adapter in self._channels.items():
            if not adapter.is_available():
                logger.warning(f"[ChannelManager] Skipping channel {name}: Not available/configured")
                continue
            
            thread = threading.Thread(
                target=self._run_channel_loop,
                args=(name, adapter),
                name=f"Channel-{name}",
                daemon=True
            )
            self._threads[name] = thread
            thread.start()
            logger.info(f"[ChannelManager] Started thread for channel: {name}")

    def stop_all(self):
        self._running = False
        for name, adapter in self._channels.items():
            logger.info(f"[ChannelManager] Stopping channel: {name}")
            # Note: Many adapters use blocking stream() (e.g. input() or long polling).
            # Some might need explicit stop() call.
            if hasattr(adapter, 'stop'):
                adapter.stop()
            adapter.on_stop()

    def _run_channel_loop(self, name: str, adapter: ChannelAdapter):
        """Per-thread loop for a single channel."""
        logger.info(f"[ChannelManager] Loop started for {name}")
        adapter.on_ready()
        
        try:
            for utterance in adapter.stream():
                if not self._running:
                    break
                
                logger.info(f"[ChannelManager] Received utterance from {name}: {utterance.text}")
                
                # Identify user and get session
                user_id = utterance.metadata.get("user_id", "default")
                session = self._session_mgr.get_or_create(name, user_id)
                
                # Handle slash commands (bypass orchestrator)
                slash_reply = session.slash_handler.handle(utterance.text)
                if slash_reply:
                    logger.info(f"[ChannelManager] Slash command handled for {session.id}: {utterance.text}")
                    adapter.send(session.id, slash_reply)
                    continue

                # Process via session-isolated orchestrator
                logger.info(f"[ChannelManager] Processing utterance via session {session.id}")
                results = session.orchestrator.process(
                    utterance.text,
                    source=name,
                    typing_callback=lambda: adapter.start_typing(session.id)
                )
                
                logger.info(f"[ChannelManager] Processed. Results count: {len(results)}")
                
                # Format and send reply
                reply_text = MessageFormatter.format(results, source=name)
                logger.info(f"[ChannelManager] Sending reply to {session.id}: {reply_text[:50]}...")
                adapter.send(session.id, reply_text)
                
        except Exception as e:
            logger.error(f"[ChannelManager] Error in channel {name}: {e}", exc_info=True)
        finally:
            logger.info(f"[ChannelManager] Loop exited for {name}")

    def list_channels(self) -> List[dict]:
        res = []
        for name, adapter in self._channels.items():
            res.append({
                "name": name,
                "status": "running" if name in self._threads and self._threads[name].is_alive() else "stopped",
                "available": adapter.is_available()
            })
        return res
