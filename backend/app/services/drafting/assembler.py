"""Assembler – merges review annotations into the draft, resolves conflicts,
and computes quality scores."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from app.services.drafting.models import (
    Annotation,
    FinalDraft,
    QualityReport,
    RawDraft,
)


class Assembler:
    """Merge review-agent annotations into a *RawDraft* and produce a
    *FinalDraft* with a quality report."""

    async def assemble(
        self,
        draft: RawDraft,
        annotations: list[Annotation],
    ) -> FinalDraft:
        final_draft = deepcopy(draft)

        # Group annotations by section_number
        by_section: dict[str, list[Annotation]] = defaultdict(list)
        for a in annotations:
            by_section[a.section_number].append(a)

        applied = 0
        conflicts = 0
        open_annotations: list[Annotation] = []

        for section in final_draft.sections:
            section_anns = by_section.get(section.number, [])
            fixes = [a for a in section_anns if a.suggested_fix]

            if len(fixes) == 0:
                # No fixes — collect warnings/criticals as open
                open_annotations.extend(
                    a for a in section_anns if a.severity in ("warning", "critical")
                )
            elif len(fixes) == 1:
                # Single fix — apply it
                section.content = fixes[0].suggested_fix  # type: ignore[assignment]
                applied += 1
                open_annotations.extend(
                    a
                    for a in section_anns
                    if a not in fixes and a.severity in ("warning", "critical")
                )
            else:
                # Multiple fixes for the same section — conflict
                conflicts += 1
                open_annotations.extend(fixes)

        # Add global annotations (section_number="*") that are unresolved
        open_annotations.extend(
            a
            for a in by_section.get("*", [])
            if a.severity in ("warning", "critical") and not a.suggested_fix
        )

        quality = self._compute_scores(annotations, applied, conflicts)
        quality.annotations_applied = applied
        quality.conflicts_flagged = conflicts
        quality.open_annotations = open_annotations

        return FinalDraft(draft=final_draft, quality_report=quality)

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _compute_scores(
        self,
        annotations: list[Annotation],
        applied: int,
        conflicts: int,
    ) -> QualityReport:
        risk_anns = [a for a in annotations if a.agent == "risk"]
        compliance_anns = [a for a in annotations if a.agent == "compliance"]
        qa_anns = [a for a in annotations if a.agent == "qa"]

        risk_score = self._score(risk_anns)
        compliance_score = self._score(compliance_anns)
        qa_score = self._score(qa_anns)
        overall = (risk_score + compliance_score + qa_score) / 3

        return QualityReport(
            overall_score=round(overall, 1),
            risk_alignment=round(risk_score, 1),
            compliance_score=round(compliance_score, 1),
            qa_score=round(qa_score, 1),
        )

    @staticmethod
    def _score(annotations: list[Annotation]) -> float:
        """Higher is better. Each annotation penalises the score depending on
        severity."""
        if not annotations:
            return 100.0
        penalty = sum(
            15.0 if a.severity == "critical" else 5.0 if a.severity == "warning" else 1.0
            for a in annotations
        )
        return max(0.0, 100.0 - penalty)
