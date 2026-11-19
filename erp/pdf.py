import io
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


def _build_pdf_styles() -> dict[str, ParagraphStyle]:
    """Build custom ReportLab paragraph styles for invoice PDF rendering."""
    base = getSampleStyleSheet()
    specs = {
        "title": ("Heading1", 24, 28, "#0f172a", "Helvetica-Bold", 0),
        "subtitle": ("Normal", 10, 14, "#475569", None, 0),
        "badge": ("Normal", 11, 15, "#2563eb", "Helvetica-Bold", 2),
        "header_right": ("Normal", 9, 13, "#334155", None, 2),
        "section_title": ("Heading2", 12, 16, "#1e293b", "Helvetica-Bold", 0),
        "body": ("Normal", 9, 13, "#334155", None, 0),
        "table_header": ("Normal", 9, 12, "#ffffff", "Helvetica-Bold", 0),
        "table_cell": ("Normal", 9, 12, "#1e293b", None, 0),
        "table_cell_right": ("Normal", 9, 12, "#1e293b", None, 2),
    }
    styles: dict[str, ParagraphStyle] = {}
    for key, (parent, size, leading, hex_color, font_name, align) in specs.items():
        kwargs = {
            "parent": base[parent],
            "fontSize": size,
            "leading": leading,
            "textColor": colors.HexColor(hex_color),
            "alignment": align,
        }
        if font_name:
            kwargs["fontName"] = font_name
        styles[key] = ParagraphStyle(f"Invoice_{key}", **kwargs)
    return styles


def _build_header_flowable(invoice, pdf_styles: dict[str, ParagraphStyle]) -> list:
    """Build company branding, invoice metadata header table, and divider."""
    company_info = [
        Paragraph("<b>ENTERPRISE SYSTEM</b>", pdf_styles["title"]),
        Paragraph("Enterprise Resource Planning (ERP) Suite", pdf_styles["subtitle"]),
        Paragraph("Web & Cloud Operations", pdf_styles["subtitle"]),
        Paragraph("support@enterprise.local", pdf_styles["subtitle"]),
    ]
    status_color = "#16a34a" if invoice.status == "PAID" else "#2563eb"
    if invoice.status == "OVERDUE":
        status_color = "#dc2626"
    badge_html = f"<font color='{status_color}'><b>STATUS: {invoice.get_status_display().upper()}</b></font>"
    invoice_info = [
        Paragraph(badge_html, pdf_styles["badge"]),
        Spacer(1, 4),
        Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}", pdf_styles["header_right"]),
        Paragraph(f"<b>Issue Date:</b> {invoice.issue_date.strftime('%B %d, %Y')}", pdf_styles["header_right"]),
        Paragraph(f"<b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y')}", pdf_styles["header_right"]),
    ]
    header_table = Table([[company_info, invoice_info]], colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        header_table,
        Spacer(1, 16),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=14),
    ]


def _build_bill_to_flowable(invoice, pdf_styles: dict[str, ParagraphStyle]) -> list:
    """Build the customer billing address box."""
    bill_to_content = [
        Paragraph("<b>BILL TO:</b>", pdf_styles["section_title"]),
        Spacer(1, 4),
        Paragraph(f"<b>{invoice.customer_name}</b>", pdf_styles["body"]),
        Paragraph(f"Email: {invoice.customer_email}", pdf_styles["body"]),
    ]
    if invoice.customer_address:
        bill_to_content.append(Paragraph(invoice.customer_address.replace("\n", "<br/>"), pdf_styles["body"]))
    bill_table = Table([[bill_to_content]], colWidths=[7.5 * inch])
    bill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    return [bill_table, Spacer(1, 16)]


def _build_items_flowable(invoice, pdf_styles: dict[str, ParagraphStyle]) -> list:
    """Build the invoice line items table."""
    hdr = pdf_styles["table_header"]
    cell = pdf_styles["table_cell"]
    cell_r = pdf_styles["table_cell_right"]
    items_data = [[
        Paragraph("<b>Description</b>", hdr),
        Paragraph("<b>Qty</b>", hdr),
        Paragraph("<b>Unit Price</b>", hdr),
        Paragraph("<b>Line Total</b>", hdr),
    ]]
    items = list(invoice.items.all())
    if not items:
        items_data.append([
            Paragraph("No items recorded.", cell),
            Paragraph("1.00", cell),
            Paragraph(f"${invoice.subtotal:.2f}", cell_r),
            Paragraph(f"${invoice.total_amount:.2f}", cell_r),
        ])
    else:
        for item in items:
            desc_text = f"<b>{item.product.name}</b> ({item.product.sku})<br/>{item.description}" if item.product else item.description
            items_data.append([
                Paragraph(desc_text, cell),
                Paragraph(f"{item.quantity:g}", cell),
                Paragraph(f"${item.unit_price:.2f}", cell_r),
                Paragraph(f"${item.total_price:.2f}", cell_r),
            ])
    items_table = Table(items_data, colWidths=[4.2 * inch, 0.9 * inch, 1.2 * inch, 1.2 * inch])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    return [items_table, Spacer(1, 14)]


def _build_totals_flowable(invoice, pdf_styles: dict[str, ParagraphStyle]) -> list:
    """Build the right-aligned subtotal, tax, discount, and total summary table."""
    cell_r = pdf_styles["table_cell_right"]
    totals_data = [[Paragraph("<b>Subtotal:</b>", cell_r), Paragraph(f"${invoice.subtotal:.2f}", cell_r)]]
    if invoice.tax_rate > 0 or invoice.tax_amount > 0:
        totals_data.append([Paragraph(f"<b>Tax ({invoice.tax_rate}%):</b>", cell_r), Paragraph(f"${invoice.tax_amount:.2f}", cell_r)])
    if invoice.discount_amount > 0:
        totals_data.append([Paragraph("<b>Discount:</b>", cell_r), Paragraph(f"-${invoice.discount_amount:.2f}", cell_r)])
    totals_data.append([Paragraph("<b>Total Amount:</b>", cell_r), Paragraph(f"<b>${invoice.total_amount:.2f}</b>", cell_r)])
    totals_table = Table(totals_data, colWidths=[1.8 * inch, 1.4 * inch], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, -1), (-1, -1), 1, colors.HexColor("#94a3b8")),
    ]))
    return [totals_table, Spacer(1, 20)]


def _build_notes_and_footer_flowable(invoice, pdf_styles: dict[str, ParagraphStyle]) -> list:
    """Build optional terms/notes block and closing thank-you footer."""
    elements = []
    if invoice.notes:
        elements.extend([
            Paragraph("<b>Terms & Payment Instructions:</b>", pdf_styles["section_title"]),
            Spacer(1, 4),
            Paragraph(invoice.notes.replace("\n", "<br/>"), pdf_styles["body"]),
            Spacer(1, 14),
        ])
    elements.extend([
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8),
        Paragraph("Thank you for your business! Please remit payment before or on the due date.", pdf_styles["subtitle"]),
    ])
    return elements


def generate_invoice_pdf(invoice) -> bytes:
    """
    Generates a clean, professional PDF invoice for the given Invoice model instance.
    Returns the binary PDF content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    pdf_styles = _build_pdf_styles()
    elements = [
        *_build_header_flowable(invoice, pdf_styles),
        *_build_bill_to_flowable(invoice, pdf_styles),
        *_build_items_flowable(invoice, pdf_styles),
        *_build_totals_flowable(invoice, pdf_styles),
        *_build_notes_and_footer_flowable(invoice, pdf_styles),
    ]
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
