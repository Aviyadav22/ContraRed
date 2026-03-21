"""
Contract Differ — Paragraph-level comparison of two contract versions.

Identifies added, removed, and modified paragraphs using difflib and
optionally calls Gemini for AI commentary on changes.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class DiffChange:
    """A single change between two contract versions."""
    change_type: str  # "added", "removed", "modified"
    text_a: str  # Text from version A (empty if added)
    text_b: str  # Text from version B (empty if removed)
    position: int  # Paragraph index in version A (or insertion point)
    similarity: float = 0.0  # 0-1, how similar modified paragraphs are
    ai_assessment: Optional[str] = None  # AI commentary


@dataclass
class DiffResult:
    """Complete diff result between two versions."""
    changes: List[DiffChange]
    total_changes: int
    paragraphs_a: int
    paragraphs_b: int
    summary: str


def _split_paragraphs(text: str) -> List[str]:
    """Split contract text into meaningful paragraphs."""
    # Split on double newlines or single newlines that start a new section
    paragraphs = re.split(r'\n\s*\n', text.strip())
    # Filter out empty paragraphs and normalize whitespace
    result = []
    for p in paragraphs:
        cleaned = p.strip()
        if cleaned and len(cleaned) > 5:  # Skip very short fragments
            result.append(cleaned)
    return result


def _hash_paragraph(text: str) -> str:
    """SHA-256 hash of normalized text."""
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _extract_section_number(text: str) -> Optional[str]:
    """Extract leading section/clause number from a paragraph.

    Matches patterns like "5.", "5.1", "CLAUSE 5", "Section 5", "(a)", etc.
    Returns the number/letter as a string for matching, or None.
    """
    text = text.strip()
    # "5." or "5.1" or "5.1.2" at start
    m = re.match(r'^(\d+(?:\.\d+)*)\s*[.)\s]', text)
    if m:
        return m.group(1)
    # "Section 5" or "Clause 5" or "Article 5"
    m = re.match(r'^(?:section|clause|article)\s+(\d+(?:\.\d+)*)', text, re.IGNORECASE)
    if m:
        return m.group(1)
    # "(a)" or "(i)" style
    m = re.match(r'^\(([a-z]|[ivxlc]+)\)', text, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None


def compute_diff(text_a: str, text_b: str) -> DiffResult:
    """
    Compare two contract versions at paragraph level.

    Returns list of changes (added, removed, modified).
    """
    paras_a = _split_paragraphs(text_a)
    paras_b = _split_paragraphs(text_b)

    # Build hash sets for quick comparison
    hashes_a = {_hash_paragraph(p): (i, p) for i, p in enumerate(paras_a)}
    hashes_b = {_hash_paragraph(p): (i, p) for i, p in enumerate(paras_b)}

    changes: List[DiffChange] = []

    # Use SequenceMatcher for paragraph-level alignment
    matcher = SequenceMatcher(None, paras_a, paras_b)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        elif tag == 'delete':
            for i in range(i1, i2):
                changes.append(DiffChange(
                    change_type="removed",
                    text_a=paras_a[i],
                    text_b="",
                    position=i,
                ))
        elif tag == 'insert':
            for j in range(j1, j2):
                changes.append(DiffChange(
                    change_type="added",
                    text_a="",
                    text_b=paras_b[j],
                    position=i1,
                ))
        elif tag == 'replace':
            # Try to pair modified paragraphs
            a_slice = paras_a[i1:i2]
            b_slice = paras_b[j1:j2]

            # Phase 1: Match by section number (most reliable for contracts)
            used_a = set()
            used_b = set()
            section_matches: List[tuple] = []

            a_sections = {ai: _extract_section_number(p) for ai, p in enumerate(a_slice)}
            b_sections = {bj: _extract_section_number(p) for bj, p in enumerate(b_slice)}

            for ai, a_sec in a_sections.items():
                if a_sec is None or ai in used_a:
                    continue
                for bj, b_sec in b_sections.items():
                    if b_sec is None or bj in used_b:
                        continue
                    if a_sec == b_sec:
                        sim = SequenceMatcher(None, a_slice[ai], b_slice[bj]).ratio()
                        section_matches.append((ai, bj, sim))
                        used_a.add(ai)
                        used_b.add(bj)
                        break

            # Phase 2: Match remaining paragraphs by similarity (threshold 0.5)
            for ai, a_para in enumerate(a_slice):
                if ai in used_a:
                    continue
                best_sim = 0.0
                best_bj = -1
                for bj, b_para in enumerate(b_slice):
                    if bj in used_b:
                        continue
                    sim = SequenceMatcher(None, a_para, b_para).ratio()
                    if sim > best_sim:
                        best_sim = sim
                        best_bj = bj

                if best_bj >= 0 and best_sim > 0.5:
                    used_a.add(ai)
                    used_b.add(best_bj)
                    section_matches.append((ai, best_bj, best_sim))

            # Emit matched pairs as "modified"
            for ai, bj, sim in section_matches:
                changes.append(DiffChange(
                    change_type="modified",
                    text_a=a_slice[ai],
                    text_b=b_slice[bj],
                    position=i1 + ai,
                    similarity=sim,
                ))

            # Unmatched A paragraphs are removals
            for ai, a_para in enumerate(a_slice):
                if ai not in used_a:
                    changes.append(DiffChange(
                        change_type="removed",
                        text_a=a_para,
                        text_b="",
                        position=i1 + ai,
                    ))

            # Unmatched B paragraphs are additions
            for bj, b_para in enumerate(b_slice):
                if bj not in used_b:
                    changes.append(DiffChange(
                        change_type="added",
                        text_a="",
                        text_b=b_para,
                        position=i1,
                    ))

    added = sum(1 for c in changes if c.change_type == "added")
    removed = sum(1 for c in changes if c.change_type == "removed")
    modified = sum(1 for c in changes if c.change_type == "modified")

    summary = f"{len(changes)} changes: {added} added, {removed} removed, {modified} modified"

    return DiffResult(
        changes=changes,
        total_changes=len(changes),
        paragraphs_a=len(paras_a),
        paragraphs_b=len(paras_b),
        summary=summary,
    )


async def compute_diff_with_ai(
    text_a: str,
    text_b: str,
    playbook_rules: Optional[List[Dict]] = None,
) -> DiffResult:
    """
    Compare two versions and add AI assessment for each change.

    AI assessment indicates whether changes favor the user, the counterparty,
    or are neutral.
    """
    diff = compute_diff(text_a, text_b)

    # Add AI commentary for all meaningful changes
    assessable_changes = [c for c in diff.changes if c.change_type in ("modified", "added", "removed")]
    if not assessable_changes:
        return diff

    try:
        from app.services.analysis_pipeline import analysis_pipeline, _sanitize_for_prompt

        if not analysis_pipeline.is_enabled:
            return diff

        # Build a batch prompt for all changes
        changes_text = ""
        for i, change in enumerate(assessable_changes):
            changes_text += f"\nChange {i+1} ({change.change_type.upper()}):\n"
            if change.text_a:
                changes_text += f"  BEFORE: {_sanitize_for_prompt(change.text_a, 500)}\n"
            else:
                changes_text += f"  BEFORE: (not present in original)\n"
            if change.text_b:
                changes_text += f"  AFTER: {_sanitize_for_prompt(change.text_b, 500)}\n"
            else:
                changes_text += f"  AFTER: (removed in new version)\n"

        rules_context = ""
        if playbook_rules:
            rules_context = "Playbook positions:\n" + "\n".join(
                f"- {_sanitize_for_prompt(r.get('name', ''), 200)}: {_sanitize_for_prompt(r.get('primary_position', ''), 500)}"
                for r in playbook_rules[:10]
            )

        assessments = await analysis_pipeline.assess_diff_changes(
            changes_text=changes_text,
            rules_context=rules_context,
        )

        if assessments:
            for item in assessments:
                idx = item.get("change_number", 0) - 1
                if 0 <= idx < len(assessable_changes):
                    assessment = item.get("assessment", "neutral")
                    explanation = item.get("explanation", "")
                    assessable_changes[idx].ai_assessment = f"{assessment}: {explanation}"

    except Exception as e:
        logger.warning("AI diff assessment failed: %s", e)

    return diff
