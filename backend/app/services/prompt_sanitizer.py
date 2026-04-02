"""
Prompt Sanitizer - Defense-in-depth against prompt injection attacks.

Provides sanitization for user-supplied text (contract text, clause text,
playbook names) before interpolation into AI prompts. Works alongside
structured prompt templates and output validation.

This module does NOT guarantee prevention of all prompt injection — it is
one layer in a defense-in-depth strategy:
  1. Input sanitization (this module)
  2. Structured prompt separation (system vs user roles)
  3. Output validation (JSON schema + confidence scoring)
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt injection patterns — matches common injection techniques
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<\s*SYS\s*>>",
    r"human\s*:\s*",
    r"assistant\s*:\s*",
    r"IMPORTANT\s*:\s*override",
    r"forget\s+(everything|all)",
    r"do\s+not\s+follow\s+(the\s+)?(above|previous|system)",
    r"repeat\s+after\s+me",
    r"translate\s+the\s+above",
    r"output\s+(the\s+)?(system|initial)\s+prompt",
    r"reveal\s+(your|the)\s+(system|initial)\s+(prompt|instructions)",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_for_prompt(text: str, max_length: int = 50000) -> str:
    """Sanitize user-supplied text before interpolating into AI prompts.

    Steps:
        1. Strip ASCII control characters (except newline/tab)
        2. Detect and neutralise known prompt injection patterns
        3. Truncate to max_length

    Args:
        text: Raw user/contract text.
        max_length: Maximum allowed character count.

    Returns:
        Sanitized text safe(r) for prompt interpolation.
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Strip control characters (keep \n \t \r)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 2. Detect and replace injection patterns
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(cleaned):
            logger.warning("Prompt injection pattern detected and neutralised")
            cleaned = pattern.sub("[FILTERED]", cleaned)

    # 3. Truncate
    return cleaned[:max_length]


def validate_contract_length(
    text: str,
    max_chars: int = 1_000_000,
    min_chars: int = 10,
) -> Tuple[bool, str]:
    """Validate that contract text length is within acceptable bounds.

    Args:
        text: Contract text to validate.
        max_chars: Upper bound on character count.
        min_chars: Lower bound on character count.

    Returns:
        (is_valid, message) tuple.
    """
    if not text or not isinstance(text, str):
        return False, "Contract text is empty or not a string"
    if len(text) < min_chars:
        return False, f"Contract text too short to analyse ({len(text)} chars, min {min_chars})"
    if len(text) > max_chars:
        return False, f"Contract text exceeds maximum length ({len(text):,} > {max_chars:,} chars)"
    return True, "OK"
