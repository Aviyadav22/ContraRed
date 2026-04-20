"""
Hallucination Guard - Post-generation verification of AI output against source document.

Verifies that AI-generated "original_text" quotes actually exist in the contract.
Uses exact matching, normalized matching, and fuzzy matching (rapidfuzz) with
configurable thresholds.  Rejects or corrects quotes that don't match.

Zero Data Retention: all processing is in RAM only.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of verifying a single AI-generated quote against the source document."""
    original_quote: str
    verified_quote: str        # Corrected quote (may differ from original if fuzzy-matched)
    confidence: float          # 0.0-1.0 verification confidence
    status: str                # "exact", "normalized", "fuzzy_corrected", "rejected"
    matched_segment: str       # The actual text segment from the document that matched
    similarity_score: float    # Raw similarity score (1.0 for exact, Levenshtein ratio for fuzzy)
    correction_applied: bool   # Whether the quote was corrected

    @property
    def passed(self) -> bool:
        return self.status != "rejected"


@dataclass
class HallucinationStats:
    """Aggregate statistics for a batch of verifications."""
    total_checked: int = 0
    exact_matches: int = 0
    normalized_matches: int = 0
    fuzzy_corrected: int = 0
    rejected: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total_checked == 0:
            return 1.0
        return (self.total_checked - self.rejected) / self.total_checked

    @property
    def hallucination_rate(self) -> float:
        if self.total_checked == 0:
            return 0.0
        return self.rejected / self.total_checked

    def to_dict(self) -> dict:
        return {
            "total_checked": self.total_checked,
            "exact_matches": self.exact_matches,
            "normalized_matches": self.normalized_matches,
            "fuzzy_corrected": self.fuzzy_corrected,
            "rejected": self.rejected,
            "pass_rate": round(self.pass_rate, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
        }


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace (including newlines) to single spaces and strip."""
    return " ".join(text.split())


def _normalize_for_comparison(text: str) -> str:
    """Aggressive normalization: lowercase, collapse whitespace, strip punctuation edges."""
    t = text.lower()
    t = _normalize_whitespace(t)
    # Remove leading/trailing punctuation that AI might add/remove
    t = t.strip('"\' .,;:')
    return t


def _sliding_window_segments(text: str, window_size: int, step: int) -> List[str]:
    """Generate overlapping text segments of approximately `window_size` characters.

    Splits on word boundaries so segments don't cut words in half.
    """
    words = text.split()
    if not words:
        return []

    segments: List[str] = []
    # Estimate words per window
    avg_word_len = max(1, len(text) / max(1, len(words)))
    words_per_window = max(5, int(window_size / avg_word_len))
    words_per_step = max(1, int(step / avg_word_len))

    i = 0
    while i < len(words):
        segment = " ".join(words[i: i + words_per_window])
        segments.append(segment)
        i += words_per_step
        if i + words_per_window >= len(words) and i < len(words):
            # Ensure we capture the tail
            segments.append(" ".join(words[i:]))
            break

    return segments


class HallucinationGuard:
    """
    Post-generation verification of AI output against the source contract.

    Verification cascade:
      1. Exact substring match -> confidence 1.0
      2. Normalized match (case/whitespace) -> confidence 0.99
      3. Short quotes (<40 chars) that reach here -> REJECTED (no fuzzy allowed)
      4. Two-step fuzzy:
           - partial_ratio to locate best window
           - fuzz.ratio on that window for pass/fail (>=0.90 non-deal-breaker,
             >=0.95 deal-breaker) -> corrected quote, reduced confidence
      5. No match -> REJECTED (logged as hallucination)

    For DEAL-BREAKER rules that fail fuzzy match, the caller can request
    a re-query with explicit "copy verbatim" instruction via `needs_requery`.
    """

    # Thresholds
    # Tightened (Phase 2 investor polish): the AI is the load-bearing system here,
    # so verification must be strict. We require 0.90 sequence similarity for
    # non-deal-breaker quotes and 0.95 for deal-breakers. Short quotes (<40 chars)
    # bypass fuzzy entirely — they must match exactly or via normalization.
    FUZZY_PASS_THRESHOLD: float = 0.90            # Minimum ratio to accept (non-deal-breaker)
    FUZZY_DEAL_BREAKER_THRESHOLD: float = 0.95    # Stricter bar for deal-breakers
    FUZZY_REJECT_THRESHOLD: float = 0.70          # Below this -> hard reject
    DEGRADED_LOWER_BOUND: float = 0.80            # 0.80-0.90 logged as "degraded" for observability
    SHORT_QUOTE_MAX_CHARS: int = 40               # Below this length, no fuzzy — exact/normalized only

    def __init__(
        self,
        contract_text: str,
        fuzzy_pass_threshold: float = 0.90,
        fuzzy_reject_threshold: float = 0.70,
        fuzzy_deal_breaker_threshold: float = 0.95,
    ):
        """
        Args:
            contract_text: The full source contract text to verify against.
            fuzzy_pass_threshold: Minimum rapidfuzz ratio to accept (with correction).
            fuzzy_reject_threshold: Below this ratio -> hard reject.
            fuzzy_deal_breaker_threshold: Stricter threshold applied when the quote
                relates to a deal-breaker rule.
        """
        self.contract_text = contract_text
        self.FUZZY_PASS_THRESHOLD = fuzzy_pass_threshold
        self.FUZZY_DEAL_BREAKER_THRESHOLD = fuzzy_deal_breaker_threshold
        self.FUZZY_REJECT_THRESHOLD = fuzzy_reject_threshold

        # Pre-compute normalized version for stage 2
        self._normalized_text = _normalize_for_comparison(contract_text)

        # Pre-compute sliding window segments for fuzzy matching (stage 3)
        # Use segments of ~300 chars with 100-char overlap
        self._segments = _sliding_window_segments(contract_text, window_size=300, step=100)
        self._normalized_segments = [_normalize_for_comparison(s) for s in self._segments]

        # Statistics tracker
        self.stats = HallucinationStats()

    def verify_quote(self, quote: str, is_deal_breaker: bool = False) -> VerificationResult:
        """
        Verify a single AI-generated quote against the source contract.

        Args:
            quote: The "original_text" field from AI output.
            is_deal_breaker: If True, flag for re-query on fuzzy failure.

        Returns:
            VerificationResult with status, confidence, and corrected quote.
        """
        self.stats.total_checked += 1

        if not quote or not quote.strip():
            self.stats.rejected += 1
            return VerificationResult(
                original_quote=quote,
                verified_quote="",
                confidence=0.0,
                status="rejected",
                matched_segment="",
                similarity_score=0.0,
                correction_applied=False,
            )

        clean_quote = quote.strip()

        # --- Stage 1: Exact substring match ---
        if clean_quote in self.contract_text:
            self.stats.exact_matches += 1
            return VerificationResult(
                original_quote=quote,
                verified_quote=clean_quote,
                confidence=1.0,
                status="exact",
                matched_segment=clean_quote,
                similarity_score=1.0,
                correction_applied=False,
            )

        # --- Stage 2: Normalized match (case + whitespace) ---
        normalized_quote = _normalize_for_comparison(clean_quote)
        if normalized_quote and normalized_quote in self._normalized_text:
            # Find the actual text in the original document
            actual_segment = self._find_actual_text(normalized_quote)
            self.stats.normalized_matches += 1
            return VerificationResult(
                original_quote=quote,
                verified_quote=actual_segment or clean_quote,
                confidence=0.99,
                status="normalized",
                matched_segment=actual_segment or clean_quote,
                similarity_score=0.99,
                correction_applied=bool(actual_segment and actual_segment != clean_quote),
            )

        # --- Short-quote guard: no fuzzy matching for quotes <40 chars ---
        # Short phrases (e.g., "indemnify and hold harmless") can share enough
        # tokens with unrelated contract text to fuzzy-match. Require exact or
        # normalized-exact only. If we reach this point, neither matched.
        if len(normalized_quote) < self.SHORT_QUOTE_MAX_CHARS:
            self.stats.rejected += 1
            logger.warning(
                "Short-quote hallucination rejected (len=%d, threshold=%d). "
                "Quote: '%.80s'",
                len(normalized_quote),
                self.SHORT_QUOTE_MAX_CHARS,
                clean_quote,
            )
            return VerificationResult(
                original_quote=quote,
                verified_quote="",
                confidence=0.0,
                status="rejected",
                matched_segment="",
                similarity_score=0.0,
                correction_applied=False,
            )

        # --- Stage 3: Two-step fuzzy match (rapidfuzz) ---
        # Step 3a: Use fuzz.partial_ratio to LOCATE the best-matching window.
        # Step 3b: Re-score that anchored window with fuzz.ratio (full sequence
        # similarity) for the actual pass/fail decision. partial_ratio alone is
        # too permissive — it rewards any substring overlap, which the AI can
        # exploit by paraphrasing while keeping a few key words.
        best_match, best_score, best_segment = self._fuzzy_search(normalized_quote)

        # Re-score with full sequence ratio on the anchored segment.
        if best_segment:
            anchored_score = fuzz.ratio(normalized_quote, _normalize_for_comparison(best_segment))
        else:
            anchored_score = 0.0

        # Pick the relevant pass threshold based on deal-breaker status.
        pass_threshold = (
            self.FUZZY_DEAL_BREAKER_THRESHOLD if is_deal_breaker else self.FUZZY_PASS_THRESHOLD
        )

        # Observability: log "degraded" range (would-pass at old threshold but
        # below current threshold). Useful for tuning in production.
        if self.DEGRADED_LOWER_BOUND * 100 <= anchored_score < pass_threshold * 100:
            logger.debug(
                "Fuzzy match downgraded to 'degraded' (anchored_score=%.1f, "
                "threshold=%.2f, deal_breaker=%s). Quote: '%.80s'",
                anchored_score,
                pass_threshold,
                is_deal_breaker,
                clean_quote,
            )

        if anchored_score >= pass_threshold * 100:
            # Fuzzy match passed - correct the quote to the actual document text
            corrected = best_segment
            confidence = round(anchored_score / 100.0 * 0.95, 3)  # Scale down slightly
            self.stats.fuzzy_corrected += 1
            return VerificationResult(
                original_quote=quote,
                verified_quote=corrected,
                confidence=confidence,
                status="fuzzy_corrected",
                matched_segment=corrected,
                similarity_score=round(anchored_score / 100.0, 3),
                correction_applied=True,
            )

        # --- Stage 4: Rejection ---
        self.stats.rejected += 1
        logger.warning(
            "Hallucination detected: quote not found in contract "
            "(partial_locate=%.1f, anchored_ratio=%.1f, threshold=%.2f). "
            "Quote: '%.80s...'",
            best_score,
            anchored_score,
            pass_threshold,
            clean_quote,
        )

        return VerificationResult(
            original_quote=quote,
            verified_quote="",
            confidence=0.0,
            status="rejected",
            matched_segment="",
            # Report the stricter anchored ratio (not partial_ratio) — it better
            # reflects actual similarity and is what gated the pass/fail decision.
            similarity_score=round(anchored_score / 100.0, 3) if anchored_score > 0 else 0.0,
            correction_applied=False,
        )

    def verify_batch(
        self,
        quotes: List[str],
        deal_breaker_flags: Optional[List[bool]] = None,
    ) -> List[VerificationResult]:
        """
        Verify a batch of quotes.

        Args:
            quotes: List of "original_text" strings from AI output.
            deal_breaker_flags: Parallel list indicating deal-breaker status.

        Returns:
            List of VerificationResult in same order as input.
        """
        if deal_breaker_flags is None:
            deal_breaker_flags = [False] * len(quotes)

        results: List[VerificationResult] = []
        for quote, is_db in zip(quotes, deal_breaker_flags):
            results.append(self.verify_quote(quote, is_deal_breaker=is_db))
        return results

    def needs_requery(self, result: VerificationResult, is_deal_breaker: bool) -> bool:
        """
        Determine if a failed verification should trigger a re-query.

        Only for DEAL-BREAKER rules whose quotes were rejected or had
        low fuzzy scores (between reject and pass thresholds).
        """
        if not is_deal_breaker:
            return False
        if result.status == "rejected":
            return True
        if result.status == "fuzzy_corrected" and result.similarity_score < 0.85:
            return True
        return False

    def get_requery_instruction(self, rule_name: str, original_quote: str) -> str:
        """
        Generate an explicit instruction for the AI to re-extract the quote verbatim.

        Used when a DEAL-BREAKER rule fails initial verification.
        """
        return (
            f"CRITICAL RE-EXTRACTION REQUEST for rule '{rule_name}':\n"
            f"Your previous extraction was: \"{original_quote}\"\n"
            f"This text was NOT found in the contract. You MUST copy the EXACT text "
            f"from the contract - character for character, including all punctuation "
            f"and spacing. Do NOT paraphrase or summarize. Find the specific sentence "
            f"or phrase in the contract that violates this rule and copy it VERBATIM.\n"
            f"If no such text exists, respond with 'NO_MATCH'."
        )

    def _fuzzy_search(
        self,
        normalized_quote: str,
        scorer=None,
        score_cutoff: float = 0,
    ) -> Tuple[Optional[str], float, str]:
        """
        Search for the closest matching segment in the contract using rapidfuzz.

        Args:
            normalized_quote: The normalized quote to search for.
            scorer: Optional rapidfuzz scorer override (e.g. fuzz.ratio for short quotes).
            score_cutoff: Optional score cutoff override.

        Returns:
            Tuple of (best_match_normalized, score, original_segment_text)
        """
        if not self._normalized_segments:
            return None, 0.0, ""

        effective_scorer = scorer or fuzz.partial_ratio
        effective_cutoff = score_cutoff or (self.FUZZY_REJECT_THRESHOLD * 100)

        # Use rapidfuzz process.extractOne for efficiency
        result = process.extractOne(
            normalized_quote,
            self._normalized_segments,
            scorer=effective_scorer,
            score_cutoff=effective_cutoff,
        )

        if result is None:
            # Try token_sort_ratio as fallback (handles word reordering)
            result = process.extractOne(
                normalized_quote,
                self._normalized_segments,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=effective_cutoff,
            )

        if result is None:
            return None, 0.0, ""

        matched_text, score, idx = result
        # Return the original (non-normalized) segment for the corrected quote
        original_segment = self._segments[idx] if idx < len(self._segments) else matched_text
        return matched_text, score, original_segment

    def _find_actual_text(self, normalized_quote: str) -> Optional[str]:
        """
        Given a normalized quote that matched in the normalized text,
        find the corresponding original (un-normalized) text in the contract.

        Uses character position mapping to extract the original substring.
        """
        # Build a mapping from normalized positions back to original
        # This is approximate but works for case/whitespace differences
        norm_text = self._normalized_text
        idx = norm_text.find(normalized_quote)
        if idx == -1:
            return None

        # Approximate: count how many real characters correspond to this position
        # Walk through original text tracking normalized position
        orig_chars = list(self.contract_text)
        norm_pos = 0
        orig_start = None
        orig_end = None

        i = 0
        while i < len(orig_chars) and norm_pos <= idx + len(normalized_quote):
            # Simulate normalization for this character
            char = orig_chars[i]
            char_lower = char.lower()

            # Skip characters that normalization removes
            if char in '"\' ' and norm_pos < idx:
                pass  # These might be stripped at edges

            if norm_pos == idx and orig_start is None:
                orig_start = i

            if norm_pos == idx + len(normalized_quote):
                orig_end = i
                break

            # Advance norm_pos for non-whitespace or single space
            if char in ' \t\n\r':
                # Whitespace collapses to single space in normalization
                if norm_pos > 0 and norm_text[norm_pos - 1] != ' ':
                    norm_pos += 1
                # Skip consecutive whitespace in original
                while i + 1 < len(orig_chars) and orig_chars[i + 1] in ' \t\n\r':
                    i += 1
            else:
                norm_pos += 1

            i += 1

        if orig_start is not None:
            if orig_end is None:
                orig_end = min(orig_start + len(normalized_quote) + 50, len(self.contract_text))
            return self.contract_text[orig_start:orig_end].strip()

        return None

    def get_stats(self) -> HallucinationStats:
        """Return current verification statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset statistics for a new batch."""
        self.stats = HallucinationStats()
