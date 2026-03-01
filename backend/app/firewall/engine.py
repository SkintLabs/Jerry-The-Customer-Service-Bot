"""
Jerry The Customer Service Bot — AI Agent Firewall Engine
Orchestrates all firewall layers for inbound and outbound scanning.

INBOUND (user → AI):
    1. SemanticRouter: Is the message on-topic? (fast, deterministic)
    2. SentinelScan: Is it a prompt injection? (LLM-based, slower)

OUTBOUND (AI → user):
    1. EgressFilter: Leaked secrets, PII, canary tokens?
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.firewall.file_sanitizer import FileSanitizer
from app.firewall.egress_filter import EgressFilter
from app.firewall.semantic_router import SemanticRouter
from app.firewall.sentinel_scan import SentinelScan

logger = logging.getLogger("jerry.firewall.engine")


@dataclass
class FirewallVerdict:
    """Result of a firewall evaluation."""
    allowed: bool
    blocked_by: Optional[str] = None
    message: str = ""
    violations: List[str] = field(default_factory=list)
    semantic_score: float = 0.0
    sentinel_result: str = ""


class FirewallEngine:
    """
    Coordinates all firewall layers.
    Designed to be fail-open: if any layer errors, the message is allowed through.
    """

    def __init__(self, embedding_model=None):
        """
        Args:
            embedding_model: Shared SentenceTransformer from ProductIntelligence.
        """
        self.file_sanitizer = FileSanitizer()
        self.egress_filter = EgressFilter()
        self.semantic_router = SemanticRouter(embedding_model=embedding_model)
        self.sentinel_scan = SentinelScan()

        logger.info(
            f"FirewallEngine initialized | "
            f"semantic_router={'active' if embedding_model else 'disabled'} | "
            f"sentinel={'active' if self.sentinel_scan.enabled else 'disabled'}"
        )

    async def scan_inbound(self, message: str) -> FirewallVerdict:
        """
        Scan an inbound user message BEFORE it reaches ConversationEngine.
        Runs: SemanticRouter → SentinelScan (only if router passes).
        """
        # Layer 3: Semantic Router (fast, no API call)
        try:
            is_on_topic, sim_score, closest = await self.semantic_router.is_on_topic(message)
        except Exception as e:
            logger.error(f"SemanticRouter error (allowing): {e}")
            is_on_topic, sim_score, closest = True, 1.0, "error_fallback"

        if not is_on_topic:
            return FirewallVerdict(
                allowed=False,
                blocked_by="semantic_router",
                message=(
                    "I'm Jerry, your shopping assistant! I can help with products, "
                    "orders, shipping, and returns. What can I help you with?"
                ),
                violations=[f"off_topic:sim={sim_score:.3f}:closest={closest[:40]}"],
                semantic_score=sim_score,
            )

        # Layer 4: Sentinel Scan (LLM-based, ~100ms)
        try:
            is_safe, sentinel_result = await self.sentinel_scan.classify(message)
        except Exception as e:
            logger.error(f"SentinelScan error (allowing): {e}")
            is_safe, sentinel_result = True, f"error:{e}"

        if not is_safe:
            return FirewallVerdict(
                allowed=False,
                blocked_by="sentinel_scan",
                message=(
                    "I'm here to help with shopping! Could you rephrase your "
                    "question about our products or orders?"
                ),
                violations=[f"injection_detected:{sentinel_result}"],
                semantic_score=sim_score,
                sentinel_result=sentinel_result,
            )

        return FirewallVerdict(
            allowed=True,
            message=message,
            semantic_score=sim_score,
            sentinel_result=sentinel_result,
        )

    async def scan_outbound(self, text: str, canary_token: str) -> FirewallVerdict:
        """
        Scan an outbound LLM response BEFORE it reaches the user.
        Runs: EgressFilter (canary tokens, API key leaks, PII).
        """
        try:
            is_safe, cleaned_text, violations = self.egress_filter.scan(text, canary_token)
        except Exception as e:
            logger.error(f"EgressFilter error (allowing): {e}")
            return FirewallVerdict(allowed=True, message=text)

        if violations:
            logger.warning(f"Egress violations: {violations}")

        return FirewallVerdict(
            allowed=is_safe,
            blocked_by="egress_filter" if not is_safe else None,
            message=cleaned_text,
            violations=violations,
        )

    def generate_canary_token(self, session_id: str) -> str:
        """Generate a canary token for a session. Inject into system prompt."""
        return self.egress_filter.generate_canary_token(session_id)
