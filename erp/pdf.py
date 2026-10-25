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

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "InvoiceSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )
    badge_style = ParagraphStyle(
        "InvoiceBadge",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563eb"),
        fontName="Helvetica-Bold",
        alignment=2,  # Right-aligned
    )
    header_right_style = ParagraphStyle(
        "HeaderRight",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        alignment=2,  # Right-aligned
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "InvoiceBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        alignment=2,
    )

    elements = []

    # --- Header Section (Company Info on Left, Invoice Details on Right) ---
    company_info = [
        Paragraph("<b>ENTERPRISE SYSTEM</b>", title_style),
        Paragraph("Enterprise Resource Planning (ERP) Suite", subtitle_style),
        Paragraph("Web & Cloud Operations", subtitle_style),
        Paragraph("support@enterprise.local", subtitle_style),
    ]

    status_color = "#16a34a" if invoice.status == "PAID" else "#2563eb"
    if invoice.status == "OVERDUE":
        status_color = "#dc2626"

    badge_html = f"<font color='{status_color}'><b>STATUS: {invoice.get_status_display().upper()}</b></font>"

    invoice_info = [
        Paragraph(badge_html, badge_style),
        Spacer(1, 4),
        Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}", header_right_style),
        Paragraph(f"<b>Issue Date:</b> {invoice.issue_date.strftime('%B %d, %Y')}", header_right_style),
        Paragraph(f"<b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y')}", header_right_style),
    ]

    header_table = Table(
        [[company_info, invoice_info]],
        colWidths=[4.0 * inch, 3.5 * inch],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

    # --- Bill To Section ---
    bill_to_content = [
        Paragraph("<b>BILL TO:</b>", section_title),
        Spacer(1, 4),
        Paragraph(f"<b>{invoice.customer_name}</b>", body_style),
        Paragraph(f"Email: {invoice.customer_email}", body_style),
    ]
    if invoice.customer_address:
        bill_to_content.append(Paragraph(invoice.customer_address.replace("\n", "<br/>"), body_style))

    bill_table = Table([[bill_to_content]], colWidths=[7.5 * inch])
    bill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(bill_table)
    elements.append(Spacer(1, 16))

    # --- Line Items Table ---
    items_data = [
        [
            Paragraph("<b>Description</b>", table_header_style),
            Paragraph("<b>Qty</b>", table_header_style),
            Paragraph("<b>Unit Price</b>", table_header_style),
            Paragraph("<b>Line Total</b>", table_header_style),
        ]
    ]

    items = list(invoice.items.all())
    if not items:
        items_data.append([
            Paragraph("No items recorded.", table_cell_style),
            Paragraph("1.00", table_cell_style),
            Paragraph(f"${invoice.subtotal:.2f}", table_cell_right),
            Paragraph(f"${invoice.total_amount:.2f}", table_cell_right),
        ])
    else:
        for item in items:
            desc_text = item.description
            if item.product:
                desc_text = f"<b>{item.product.name}</b> ({item.product.sku})<br/>{desc_text}"
            items_data.append([
                Paragraph(desc_text, table_cell_style),
                Paragraph(f"{item.quantity:g}", table_cell_style),
                Paragraph(f"${item.unit_price:.2f}", table_cell_right),
                Paragraph(f"${item.total_price:.2f}", table_cell_right),
            ])

    items_table = Table(
        items_data,
        colWidths=[4.2 * inch, 0.9 * inch, 1.2 * inch, 1.2 * inch],
    )
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
    elements.append(items_table)
    elements.append(Spacer(1, 14))

    # --- Totals Section (Right-aligned table) ---
    totals_data = [
        [Paragraph("<b>Subtotal:</b>", table_cell_right), Paragraph(f"${invoice.subtotal:.2f}", table_cell_right)],
    ]
    if invoice.tax_rate > 0 or invoice.tax_amount > 0:
        totals_data.append([
            Paragraph(f"<b>Tax ({invoice.tax_rate}%):</b>", table_cell_right),
            Paragraph(f"${invoice.tax_amount:.2f}", table_cell_right),
        ])
    if invoice.discount_amount > 0:
        totals_data.append([
            Paragraph("<b>Discount:</b>", table_cell_right),
            Paragraph(f"-${invoice.discount_amount:.2f}", table_cell_right),
        ])
    totals_data.append([
        Paragraph("<b>Total Amount:</b>", table_cell_right),
        Paragraph(f"<b>${invoice.total_amount:.2f}</b>", table_cell_right),
    ])

    totals_table = Table(
        totals_data,
        colWidths=[1.8 * inch, 1.4 * inch],
        hAlign="RIGHT",
    )
    totals_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -2), (-1, -2), 1, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, -1), (-1, -1), 1, colors.HexColor("#94a3b8")),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 20))

    # --- Notes / Terms Section ---
    if invoice.notes:
        elements.append(Paragraph("<b>Terms & Payment Instructions:</b>", section_title))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(invoice.notes.replace("\n", "<br/>"), body_style))
        elements.append(Spacer(1, 14))

    # --- Thank You Footer ---
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8))
    elements.append(Paragraph(
        "Thank you for your business! Please remit payment before or on the due date.",
        subtitle_style,
    ))

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
