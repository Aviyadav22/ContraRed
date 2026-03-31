from app.services.drafting.models import FinalDraft


def render_addin_payload(final_draft: FinalDraft, draft_id: str) -> dict:
    sections = [
        {
            "number": ds.number,
            "heading": ds.heading,
            "content": ds.content,
            "clause_type": ds.clause_type,
            "style": "Heading2" if ds.clause_type != "signature_blocks" else "Normal",
        }
        for ds in final_draft.draft.sections
    ]
    qr = final_draft.quality_report
    return {
        "draft_id": draft_id,
        "title": final_draft.draft.title,
        "contract_type": final_draft.draft.contract_type,
        "sections": sections,
        "quality_report_summary": {
            "overall_score": qr.overall_score,
            "risk_alignment": qr.risk_alignment,
            "compliance_score": qr.compliance_score,
            "qa_score": qr.qa_score,
            "open_items": len(qr.open_annotations),
            "conflicts": qr.conflicts_flagged,
        },
    }
