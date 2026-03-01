"""
Layer 2: Egress Filter — Output Scanning
Scans LLM responses for leaked secrets, PII, and canary tokens
before they reach the end user.
"""

import hashlib
import logging
import re
from typing import List, Tuple

logger = logging.getLogger("jerry.firewall.egress_filter")

# Canary token prefix (injected into system prompt per session)
CANARY_PREFIX = "JERRY-CANARY-"

# API key patterns (never should appear in outbound responses)
API_KEY_PATTERNS = [
    re.compile(r'shpat_[a-fA-F0-9]{32,}'),          # Shopify access tokens
    re.compile(r'shpss_[a-fA-F0-9]{32,}'),           # Shopify API secrets
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),              # OpenAI API keys
    re.compile(r'gsk_[a-zA-Z0-9]{20,}'),             # Groq API keys
    re.compile(r'pcsk_[a-zA-Z0-9]{20,}'),            # Pinecone API keys
    re.compile(r'sk_live_[a-zA-Z0-9]{20,}'),         # Stripe live keys
    re.compile(r'sk_test_[a-zA-Z0-9]{20,}'),         # Stripe test keys
    re.compile(r'whsec_[a-zA-Z0-9]{20,}'),           # Stripe webhook secrets
]

# PII patterns for sanitisation
PII_PATTERNS = {
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{1,4}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
}


class EgressFilter:
    """Scans outbound LLM responses for leaked secrets, PII, and canary tokens."""

    def generate_canary_token(self, session_id: str) -> str:
        """Generate a unique canary token for this session."""
        h = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return f"{CANARY_PREFIX}{h}"

    def scan(self, text: str, canary_token: str) -> Tuple[bool, str, List[str]]:
        """
        Scan outbound text for security violations.

        Returns:
            (is_safe, cleaned_text, list_of_violations)

        Protocol A (Hard Stop): Canary token leak → block entire response.
        Protocol B (Sanitise): API keys and PII → redact and pass through.
        """
        violations: List[str] = []
        cleaned = text

        # Protocol A: Canary token detection (CRITICAL — prompt injection confirmed)
        if canary_token and canary_token in text:
            violations.append("CANARY_TOKEN_LEAK")
            logger.critical(
                f"CANARY TOKEN DETECTED in outbound response — "
                f"prompt injection attack succeeded. Blocking response."
            )
            return (
                False,
                "I apologize, but I'm unable to process that request. How can I help you with our products or orders?",
                violations,
            )

        # Protocol B: API key leak detection
        for pattern in API_KEY_PATTERNS:
            if pattern.search(cleaned):
                violations.append(f"API_KEY_LEAK:{pattern.pattern[:30]}")
                cleaned = pattern.sub("[REDACTED]", cleaned)
                logger.critical(f"API key leak detected and redacted in outbound response")

        # Protocol B: PII sanitisation
        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(cleaned):
                violations.append(f"PII:{pii_type}")
                cleaned = pattern.sub(f"[{pii_type.upper()}_REDACTED]", cleaned)
                logger.warning(f"PII ({pii_type}) redacted from outbound response")

        is_safe = len(violations) == 0
        return (is_safe, cleaned, violations)
