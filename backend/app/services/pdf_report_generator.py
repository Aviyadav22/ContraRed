"""
PDF Report Generator — Generate contract analysis reports as PDF.

Phase 7: Output format support for PDF export.
Uses fpdf2 for lightweight PDF generation without system dependencies.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_pdf_report(
    issues: List[Dict[str, Any]],
    document_name: str = "contract",
    summary: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate a PDF report of contract analysis results.

    Args:
        issues: List of issue dicts from the analysis.
        document_name: Name of the analyzed document.
        summary: Optional summary dict with keys like total_issues,
                 risk_breakdown, overall_risk, etc.

    Returns:
        PDF file content as bytes.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        logger.error("fpdf2 not installed — PDF export unavailable")
        raise RuntimeError("PDF export requires fpdf2. Install with: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- Title Page ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 40, "", ln=True)  # Spacer
    pdf.cell(0, 15, "Contract Analysis Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, f"Document: {document_name}", ln=True, align="C")
    pdf.cell(0, 8, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")
    pdf.cell(0, 8, "Powered by ContraRed AI", ln=True, align="C")

    # --- Summary Section ---
    if summary:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, "Executive Summary", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 11)
        total = summary.get("total_issues", len(issues))
        overall_risk = summary.get("overall_risk", "N/A")
        pdf.cell(0, 8, f"Total Issues Found: {total}", ln=True)
        pdf.cell(0, 8, f"Overall Risk Level: {overall_risk}", ln=True)

        risk_breakdown = summary.get("risk_breakdown", {})
        if risk_breakdown:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Risk Breakdown:", ln=True)
            pdf.set_font("Helvetica", "", 11)
            for level, count in risk_breakdown.items():
                pdf.cell(0, 7, f"  {level.capitalize()}: {count}", ln=True)

    # --- Issues Table ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Detailed Findings", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    risk_colors = {
        "critical": (255, 68, 68),
        "high": (255, 140, 0),
        "medium": (255, 215, 0),
        "low": (144, 238, 144),
    }

    for idx, issue in enumerate(issues, 1):
        # Check if we need a new page (leave 60mm margin for content)
        if pdf.get_y() > 240:
            pdf.add_page()

        risk_level = issue.get("risk_level", "medium").lower()
        color = risk_colors.get(risk_level, (200, 200, 200))

        # Issue header with risk badge
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(*color)
        pdf.cell(8, 8, "", fill=True)  # Color indicator
        pdf.cell(0, 8, f"  Issue #{idx}: {issue.get('category', 'General')} [{risk_level.upper()}]", ln=True)

        # Clause text
        clause_text = issue.get("clause_text", "")
        if clause_text:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            # Truncate very long clauses
            display_text = clause_text[:500] + "..." if len(clause_text) > 500 else clause_text
            pdf.multi_cell(0, 6, f'"{display_text}"')
            pdf.set_text_color(0, 0, 0)

        # Recommendation
        recommendation = issue.get("recommendation", "")
        if recommendation:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, "Recommendation:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, recommendation)

        # Suggested revision
        revision = issue.get("suggested_revision", "")
        if revision:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, "Suggested Revision:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 100, 0)
            pdf.multi_cell(0, 6, revision)
            pdf.set_text_color(0, 0, 0)

        # Confidence
        conf = issue.get("confidence")
        if conf is not None:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(120, 120, 120)
            conf_str = f"{conf:.0%}" if isinstance(conf, (int, float)) else str(conf)
            pdf.cell(0, 6, f"Confidence: {conf_str}", ln=True)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

    # --- Footer on each page ---
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)

    return pdf.output()
