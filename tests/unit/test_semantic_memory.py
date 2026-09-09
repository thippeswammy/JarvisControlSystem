import unittest
from contextlib import contextmanager
from unittest.mock import patch
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.graph_db import GraphNode, GraphEdge
from jarvis.memory.semantic_encoder import SemanticEncoder

class TestSemanticMemory(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite DB
        self.mem = MemoryManager(":memory:")
        
        # We need an app and some nodes/edges
        self.mem.save_node(GraphNode(id="sys.volume", app_id="system", type="ACTION", label="Volume Control"))
        self.mem.save_node(GraphNode(id="sys.power", app_id="system", type="ACTION", label="Power Control"))

        # Edge for volume
        self.mem.save_edge(GraphEdge(
            id="edge.volume_up",
            from_id="sys.volume",
            to_id="sys.volume",
            triggers=["increase volume", "volume up", "make it louder"],
            action_type="command",
            confidence=0.9
        ))
        
        # Edge for power
        self.mem.save_edge(GraphEdge(
            id="edge.shutdown",
            from_id="sys.power",
            to_id="sys.power",
            triggers=["shut down", "turn off the computer", "power off"],
            action_type="command",
            confidence=0.9
        ))

        # Re-warm cache manually since we added edges after init
        self.mem._warm_embedding_cache()
        self.encoder = self.mem._encoder

    def test_exact_match_fast_lane(self):
        # "volume up" is an exact trigger
        path = self.mem.recall("volume up  ", "system", command_threshold=0.85)
        self.assertIsNotNone(path)
        self.assertEqual(path.edges[0].id, "edge.volume_up")

    def test_semantic_match(self):
        # "turn the music up" is not an exact match, but semantically similar
        cmd = "turn the music up"
        
        # Let's print the calibration score
        cmd_vec = self.encoder.embed(cmd)
        trigger_vec = self.mem._trigger_embeddings.get("increase volume")
        if cmd_vec and trigger_vec:
            score = self.encoder.cosine_similarity(cmd_vec, trigger_vec)
            print(f"\n[Calibration] '{cmd}' vs 'increase volume' = {score:.3f}")

        path = self.mem.recall(cmd, "system", command_threshold=0.55)
        self.assertIsNotNone(path, f"Semantic match failed for '{cmd}'")
        if path:
            self.assertEqual(path.edges[0].id, "edge.volume_up")

    def test_false_positive_rejection(self):
        cmd = "tell me a funny joke"
        
        # Let's print the calibration score against "shut down"
        cmd_vec = self.encoder.embed(cmd)
        trigger_vec = self.mem._trigger_embeddings.get("shut down")
        if cmd_vec and trigger_vec:
            score = self.encoder.cosine_similarity(cmd_vec, trigger_vec)
            print(f"[Calibration False Pos] '{cmd}' vs 'shut down' = {score:.3f}")

        # The threshold should aggressively reject this
        path = self.mem.recall(cmd, "system", command_threshold=0.55)
        self.assertIsNone(path)

    def test_empty_query_returns_none(self):
        """An empty (or whitespace-only) command embeds to None via
        SemanticEncoder.embed()'s `if not text: return None` short-circuit,
        and with no exact-trigger matches either, recall() must return None
        instead of raising or matching arbitrarily."""
        path = self.mem.recall("", "system", command_threshold=0.55)
        self.assertIsNone(path)

        # Whitespace collapses to "" after .strip(), same code path
        path_ws = self.mem.recall("    ", "system", command_threshold=0.55)
        self.assertIsNone(path_ws)

    @contextmanager
    def _force_local_fallback_embeddings(self):
        """Context manager that makes embedding computation fully deterministic
        and network-free for a test: forces MemoryManager._warm_embedding_cache()
        down its "Ollama unreachable" branch (local keyword-aware fallback
        vectors, order-independent bag-of-words) and makes the main encoder's
        embed() do the same for query text. This avoids depending on whatever
        real Ollama state happens to exist in the environment (running, not
        running, or slow to start up) and avoids ever tripping the encoder's
        real-network cooldown/auto-start side effects from these tests.
        """
        encoder = self.encoder

        def _fallback_embed(text, fallback=True, use_cooldown=True):
            return encoder._local_fallback_embed(text) if text else None

        with patch("jarvis.utils.ollama_utils.is_ollama_running", return_value=False), \
             patch.object(encoder, "embed", side_effect=_fallback_embed):
            yield

    def test_ambiguous_match_returns_one_of_tied_candidates(self):
        """Two triggers that share the exact same bag-of-words (just reordered)
        produce IDENTICAL local fallback embeddings, so a query similar to both
        creates a genuine tie. recall() must not crash and must deterministically
        return one of the tied candidates rather than dropping the match."""
        with self._force_local_fallback_embeddings():
            self.mem.save_node(GraphNode(id="sys.reboot", app_id="system", type="ACTION", label="Reboot"))
            self.mem.save_edge(GraphEdge(
                id="edge.reboot_a",
                from_id="sys.reboot", to_id="sys.reboot",
                triggers=["reboot machine"],
                action_type="command", confidence=0.9,
            ))
            self.mem.save_edge(GraphEdge(
                id="edge.reboot_b",
                from_id="sys.reboot", to_id="sys.reboot",
                triggers=["machine reboot"],
                action_type="command", confidence=0.9,
            ))
            self.mem._warm_embedding_cache()

            vec_a = self.mem._trigger_embeddings["reboot machine"]
            vec_b = self.mem._trigger_embeddings["machine reboot"]
            # Confirm this is a genuine tie (identical vectors) before trusting the recall assertion
            self.assertEqual(vec_a, vec_b)

            path = self.mem.recall("please reboot the machine now", "system", command_threshold=0.3)
            self.assertIsNotNone(path)
            self.assertIn(path.edges[0].id, {"edge.reboot_a", "edge.reboot_b"})

    def test_ambiguous_match_prefers_state_sig_on_tie(self):
        """Among tied candidates (equal similarity score), MemoryManager's
        tie-breaker logic must prefer the candidate whose starting_state_sig
        matches the caller-supplied state_sig, regardless of scan order."""
        with self._force_local_fallback_embeddings():
            self.mem.save_node(GraphNode(id="sys.reboot2", app_id="system", type="ACTION", label="Reboot2"))
            self.mem.save_edge(GraphEdge(
                id="edge.reboot_no_state",
                from_id="sys.reboot2", to_id="sys.reboot2",
                triggers=["restart device"],
                action_type="command", confidence=0.9,
                starting_state_sig="",
            ))
            self.mem.save_edge(GraphEdge(
                id="edge.reboot_with_state",
                from_id="sys.reboot2", to_id="sys.reboot2",
                triggers=["device restart"],
                action_type="command", confidence=0.9,
                starting_state_sig="state-xyz",
            ))
            self.mem._warm_embedding_cache()

            vec_a = self.mem._trigger_embeddings["restart device"]
            vec_b = self.mem._trigger_embeddings["device restart"]
            self.assertEqual(vec_a, vec_b)

            path = self.mem.recall(
                "please restart the device", "system",
                state_sig="state-xyz", command_threshold=0.3,
            )
            self.assertIsNotNone(path)
            self.assertEqual(path.edges[0].id, "edge.reboot_with_state")

    def test_encoder_exception_propagates_uncaught(self):
        """MemoryManager._hybrid_recall() has no try/except around the
        semantic-pass call to encoder.embed(). SemanticEncoder.embed() itself
        normally swallows network errors and returns a local fallback vector,
        but if the encoder raises directly (e.g. a bug, or a misbehaving
        subclass), MemoryManager does NOT catch it — the exception propagates
        straight out of recall() to the caller. This test documents that
        actual (unguarded) behavior."""
        with patch.object(self.encoder, "embed", side_effect=RuntimeError("encoder blew up")):
            with self.assertRaises(RuntimeError):
                self.mem.recall("turn the music up", "system", command_threshold=0.55)

if __name__ == "__main__":
    unittest.main()
