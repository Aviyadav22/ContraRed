"""Drafting Orchestrator — state machine driving the full multi-agent pipeline."""

import asyncio
import logging

from app.services.drafting.models import FinalDraft, Annotation
from app.services.drafting.style_rules import apply_all_style_rules
from app.services.drafting.consistency_engine import ConsistencyEngine
from app.services.drafting.jurisdiction_rules import JurisdictionRuleEngine
from app.services.drafting.agents.intake_agent import IntakeAgent
from app.services.drafting.agents.draft_agent import DraftAgent
from app.services.drafting.agents.risk_agent import RiskAgent
from app.services.drafting.agents.compliance_agent import ComplianceAgent
from app.services.drafting.agents.qa_agent import QAAgent
from app.services.drafting.assembler import Assembler

logger = logging.getLogger(__name__)

_STAGE_TIMEOUT = 120  # seconds per stage


class DraftingOrchestrator:
    """Drives intake -> draft -> parallel review -> assembly pipeline."""

    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.draft_agent = DraftAgent()
        self.risk_agent = RiskAgent()
        self.compliance_agent = ComplianceAgent()
        self.qa_agent = QAAgent()
        self.assembler = Assembler()
        self._consistency = ConsistencyEngine()
        self._jurisdiction = JurisdictionRuleEngine()

    async def run(self, raw_input: dict) -> FinalDraft:
        """Execute the full drafting pipeline and return the final draft."""

        # Stage 1: Intake — validate and enrich the request
        logger.info("Stage 1: Intake processing")
        try:
            draft_request = await asyncio.wait_for(
                self.intake_agent.process(raw_input),
                timeout=_STAGE_TIMEOUT,
            )
            playbook = self.intake_agent.select_playbook(
                draft_request.contract_type, draft_request.jurisdiction
            )
        except asyncio.TimeoutError:
            logger.error("Stage 1 timed out after %ds", _STAGE_TIMEOUT)
            raise RuntimeError("Intake processing timed out")
        except Exception as exc:
            logger.error("Stage 1 failed: %s", exc, exc_info=True)
            raise

        # Stage 2: Draft generation
        logger.info("Stage 2: Draft generation")
        try:
            raw_draft = await asyncio.wait_for(
                self.draft_agent.generate(draft_request, playbook),
                timeout=_STAGE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Stage 2 timed out after %ds", _STAGE_TIMEOUT)
            raise RuntimeError("Draft generation timed out")
        except Exception as exc:
            logger.error("Stage 2 failed: %s", exc, exc_info=True)
            raise

        # Stage 3: Parallel review by risk, compliance, and QA agents
        logger.info("Stage 3: Parallel review (risk, compliance, QA)")
        risk_anns: list = []
        compliance_anns: list = []
        qa_anns: list = []
        try:
            risk_anns, compliance_anns, qa_anns = await asyncio.wait_for(
                asyncio.gather(
                    self.risk_agent.review(
                        raw_draft, risk_appetite=draft_request.risk_appetite
                    ),
                    self.compliance_agent.review(
                        raw_draft, jurisdiction=draft_request.jurisdiction
                    ),
                    self.qa_agent.review(raw_draft),
                ),
                timeout=_STAGE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Stage 3 timed out after %ds — using partial results", _STAGE_TIMEOUT)
        except Exception as exc:
            logger.error("Stage 3 failed: %s — continuing with empty annotations", exc, exc_info=True)

        all_annotations = risk_anns + compliance_anns + qa_anns

        # Stage 3b: Deterministic jurisdiction rule checks
        logger.info("Stage 3b: Jurisdiction rule checks (%s)", draft_request.jurisdiction)
        jurisdiction_findings = self._jurisdiction.check(
            raw_draft,
            jurisdiction=draft_request.jurisdiction,
            contract_type=draft_request.contract_type,
        )
        all_annotations.extend(self._jurisdiction.to_annotations(jurisdiction_findings))

        logger.info("Reviews complete: %d annotations total", len(all_annotations))

        # Stage 4: Assemble final draft with annotations applied
        logger.info("Stage 4: Assembly")
        try:
            result = await asyncio.wait_for(
                self.assembler.assemble(raw_draft, all_annotations),
                timeout=_STAGE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Stage 4 timed out after %ds", _STAGE_TIMEOUT)
            raise RuntimeError("Assembly timed out")
        except Exception as exc:
            logger.error("Stage 4 failed: %s", exc, exc_info=True)
            raise

        # ── Stage 5: Style enforcement + consistency checks ──
        logger.info("Stage 5: Style enforcement + consistency checks")
        try:
            defined_set = set(result.draft.defined_terms.keys())
            for section in result.draft.sections:
                section.content = apply_all_style_rules(
                    section.content, defined_terms=defined_set
                )
            consistency_annotations = self._consistency.check(result.draft)
            result.quality_report.open_annotations.extend(consistency_annotations)
            # Recompute QA score with consistency findings
            penalty = sum(
                15 if a.severity == "critical" else 5 if a.severity == "warning" else 1
                for a in result.quality_report.open_annotations
            )
            result.quality_report.qa_score = max(0.0, 100.0 - penalty)
        except Exception as exc:
            logger.warning("Style/consistency stage failed: %s", exc)

        return result


drafting_orchestrator = DraftingOrchestrator()
