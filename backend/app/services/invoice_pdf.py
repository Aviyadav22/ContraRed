"""
Invoice PDF generator for billing compliance.

Generates a single-page PDF invoice using fpdf2.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_invoice_pdf(invoice, user) -> bytes:
    """Generate a PDF invoice document.

    Args:
        invoice: Invoice model instance.
        user: User model instance (for name/email).

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
    pdf.add_page()

    # --- Header ---
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(220, 38, 38)  # ContraRed brand red
    pdf.cell(0, 12, "ContraRed", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "AI-Powered Contract Redlining", ln=True)
    pdf.ln(8)

    # --- Invoice Title ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "INVOICE", ln=True)
    pdf.set_draw_color(220, 38, 38)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # --- Invoice Details ---
    pdf.set_font("Helvetica", "", 10)
    inv_id = str(invoice.id)
    created = invoice.created_at.strftime("%B %d, %Y") if invoice.created_at else "N/A"
    paid = invoice.paid_at.strftime("%B %d, %Y") if invoice.paid_at else "Unpaid"

    details = [
        ("Invoice Number", inv_id[:8].upper()),
        ("Date Issued", created),
        ("Date Paid", paid),
        ("Status", invoice.status.upper()),
        ("Gateway", (invoice.gateway or "razorpay").title()),
    ]

    if invoice.gateway_payment_id:
        details.append(("Payment ID", invoice.gateway_payment_id))
    if invoice.gateway_invoice_id:
        details.append(("Gateway Invoice", invoice.gateway_invoice_id))

    for label, value in details:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, f"{label}:", align="L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(value), ln=True)

    pdf.ln(8)

    # --- Billed To ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Billed To", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, user.name, ln=True)
    pdf.cell(0, 6, user.email, ln=True)
    pdf.ln(8)

    # --- Line Items Table ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(100, 8, "Description", border=1, fill=True)
    pdf.cell(30, 8, "Currency", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Amount", border=1, align="R", fill=True, ln=True)

    pdf.set_font("Helvetica", "", 10)
    plan_name = (invoice.plan or "").title()
    description = invoice.description or f"{plan_name} Plan - Monthly Subscription"

    # Format amount from smallest unit
    currency = invoice.currency or "INR"
    if currency == "INR":
        formatted_amount = f"Rs. {invoice.amount / 100:,.2f}"
    else:
        formatted_amount = f"${invoice.amount / 100:,.2f}"

    pdf.cell(100, 8, description, border=1)
    pdf.cell(30, 8, currency, border=1, align="C")
    pdf.cell(30, 8, formatted_amount, border=1, align="R", ln=True)

    # Total row
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 9, "", border=0)
    pdf.cell(30, 9, "Total:", border=1, align="C", fill=True)
    pdf.cell(30, 9, formatted_amount, border=1, align="R", fill=True, ln=True)

    pdf.ln(12)

    # --- Footer ---
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.cell(0, 6, "This is a computer-generated invoice and does not require a signature.", ln=True)

    return pdf.output()
