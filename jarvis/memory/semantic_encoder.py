"""
Semantic Encoder
================
Provides vector embeddings for semantic search using a local Ollama instance.
Does not require heavy PyTorch dependencies.
"""

import json
import logging
import math
import urllib.request
import urllib.error
from typing import List, Optional

logger = logging.getLogger(__name__)

class SemanticEncoder:
    """
    Client for generating embeddings via local Ollama.
    Default model: nomic-embed-text
    """

    def __init__(
        self,
        api_url: str = "http://localhost:11434/api/embeddings",
        model: str = "nomic-embed-text",
        timeout: float = 30.0
    ):
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        logger.info(f"[SemanticEncoder] Initialized with {self.model} at {self.api_url}")

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Get the vector embedding for a single text string.
        Returns None if the request fails.
        """
        if not text:
            return None

        payload = {
            "model": self.model,
            "prompt": text
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("embedding")
        except urllib.error.URLError as e:
            logger.error(f"[SemanticEncoder] Failed to connect to Ollama: {e}")
            return None
        except Exception as e:
            logger.error(f"[SemanticEncoder] Error generating embedding: {e}")
            return None

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors. Returns -1.0 to 1.0."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot_product / (norm1 * norm2)
