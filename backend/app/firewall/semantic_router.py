"""
Layer 3: Semantic Router — Topic Boundary Enforcement
Uses vector embeddings to ensure user queries stay within allowed
e-commerce topics. Off-topic queries are blocked before reaching the LLM.
"""

import asyncio
import logging
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger("jerry.firewall.semantic_router")

# Topics Jerry IS allowed to discuss
ALLOWED_TOPICS = [
    "I want to buy a product from this store",
    "What products do you have available",
    "I need help with my order tracking and shipping",
    "What is your return and refund policy",
    "I need to return or exchange an item",
    "What sizes do you carry and what size should I get",
    "Tell me about the materials and quality of your products",
    "Do you ship internationally and how much does shipping cost",
    "I want to check my order status where is my order",
    "What payment methods do you accept",
    "Do you have any sales or discounts or coupon codes",
    "Can I speak to a human customer service agent",
    "I have a complaint about my order or a damaged item",
    "Help me find a gift recommendation for someone",
    "Hello hi hey good morning good afternoon greetings",
    "Thank you goodbye have a nice day",
    "I received the wrong item or my order is missing something",
    "How do I use or care for this product",
]

COSINE_SIMILARITY_THRESHOLD = 0.35


class SemanticRouter:
    """
    Enforces topic boundaries using cosine similarity of sentence embeddings.
    Shares the SentenceTransformer model from ProductIntelligence (zero extra memory).
    """

    def __init__(self, embedding_model=None):
        """
        Args:
            embedding_model: Shared SentenceTransformer instance from ProductIntelligence.
        """
        self.embedding_model = embedding_model
        self._allowed_embeddings: Optional[np.ndarray] = None

        if self.embedding_model is not None:
            self._precompute_allowed_embeddings()
        else:
            logger.warning("SemanticRouter: no embedding model — routing disabled")

    def _precompute_allowed_embeddings(self):
        """Encode all allowed topics at init time (one-time cost, sub-second)."""
        embeddings = self.embedding_model.encode(
            ALLOWED_TOPICS, normalize_embeddings=True
        )
        self._allowed_embeddings = np.array(embeddings)
        logger.info(f"SemanticRouter: pre-computed {len(ALLOWED_TOPICS)} topic embeddings")

    async def is_on_topic(self, query: str) -> Tuple[bool, float, str]:
        """
        Check if query is semantically within allowed topics.

        Returns:
            (is_allowed, max_similarity_score, closest_topic)
        """
        if self._allowed_embeddings is None:
            return (True, 1.0, "router_disabled")

        loop = asyncio.get_running_loop()
        query_embedding = await loop.run_in_executor(
            None,
            lambda: self.embedding_model.encode([query], normalize_embeddings=True),
        )

        # Cosine similarity (embeddings are already L2-normalized)
        similarities = np.dot(self._allowed_embeddings, query_embedding[0])
        max_idx = int(np.argmax(similarities))
        max_sim = float(similarities[max_idx])
        closest_topic = ALLOWED_TOPICS[max_idx]

        is_allowed = max_sim >= COSINE_SIMILARITY_THRESHOLD

        if not is_allowed:
            logger.warning(
                f"SemanticRouter BLOCKED | sim={max_sim:.3f} | "
                f"closest='{closest_topic[:50]}' | query='{query[:60]}'"
            )

        return (is_allowed, max_sim, closest_topic)
