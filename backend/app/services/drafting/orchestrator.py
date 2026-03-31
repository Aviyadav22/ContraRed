"""Drafting Orchestrator — state machine driving the full multi-agent pipeline."""

import asyncio
import logging

from app.services.drafting.models import FinalDraft, Annotation
from app.services.drafting.agents.intake_agent import IntakeAgent
from app.services.drafting.agents.draft_agent import DraftAgent
from app.services.drafting.agents.risk_agent import RiskAgent
from app.services.drafting.agents.compliance_agent import ComplianceAgent
from app.services.drafting.agents.qa_agent import QAAgent
from app.services.drafting.assembler import Assembler

logger = logging.getLogger(__name__)


class DraftingOrchestrator:
    """Drives intake -> draft -> parallel review -> assembly pipeline."""

    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.draft_agent = DraftAgent()
        self.risk_agent = RiskAgent()
        self.compliance_agent = ComplianceAgent()
        self.qa_agent = QAAgent()
        self.assembler = Assembler()

    async def run(self, raw_input: dict) -> FinalDraft:
        """Execute the full drafting pipeline and return the final draft."""

        # Stage 1: Intake — validate and enrich the request
        logger.info("Stage 1: Intake processing")
        draft_request = await self.intake_agent.process(raw_input)
        playbook = self.intake_agent.select_playbook(
            draft_request.contract_type, draft_request.jurisdiction
        )

        # Stage 2: Draft generation
        logger.info("Stage 2: Draft generation")
        raw_draft = await self.draft_agent.generate(draft_request, playbook)

        # Stage 3: Parallel review by risk, compliance, and QA agents
        logger.info("Stage 3: Parallel review (risk, compliance, QA)")
        risk_anns, compliance_anns, qa_anns = await asyncio.gather(
            self.risk_agent.review(
                raw_draft, risk_appetite=draft_request.risk_appetite
            ),
            self.compliance_agent.review(
                raw_draft, jurisdiction=draft_request.jurisdiction
            ),
            self.qa_agent.review(raw_draft),
        )
        all_annotations = risk_anns + compliance_anns + qa_anns
        logger.info("Reviews complete: %d annotations total", len(all_annotations))

        # Stage 4: Assemble final draft with annotations applied
        logger.info("Stage 4: Assembly")
        return await self.assembler.assemble(raw_draft, all_annotations)


drafting_orchestrator = DraftingOrchestrator()
