import unittest
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

if __name__ == "__main__":
    unittest.main()
