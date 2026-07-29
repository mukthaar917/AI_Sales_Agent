from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.quotation import Quotation


PAGE_WIDTH, PAGE_HEIGHT = A4


def _safe_text(value: Any, default: str = "") -> str:
    """Convert a value to safe display text."""
    if value is None:
        return default

    return str(value)


def _format_money(
    value: Any,
    currency: str = "USD",
) -> str:
    """Format a monetary amount for the PDF."""
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0

    return f"{currency} {amount:,.2f}"


def _format_number(
    value: Any,
    decimal_places: int = 2,
) -> str:
    """Format a numeric value for display."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0

    return f"{number:,.{decimal_places}f}"


def _format_date(value: Any) -> str:
    """Format a date-like value."""
    if value is None:
        return "-"

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    return str(value)


def _get_customer(quotation: Quotation) -> Any:
    """Return the quotation customer when available."""
    return getattr(quotation, "customer", None)


def _get_organization(quotation: Quotation) -> Any:
    """Return the quotation organization when available."""
    return getattr(quotation, "organization", None)


def _build_customer_address(customer: Any) -> str:
    """Build a multiline customer address."""
    if customer is None:
        return "-"

    lines: list[str] = []

    address = getattr(customer, "address", None)
    city = getattr(customer, "city", None)
    state = getattr(customer, "state", None)
    postal_code = getattr(customer, "postal_code", None)
    country = getattr(customer, "country", None)

    if address:
        lines.append(str(address))

    city_line_parts = [
        str(value)
        for value in (city, state, postal_code)
        if value
    ]

    if city_line_parts:
        lines.append(", ".join(city_line_parts))

    if country:
        lines.append(str(country))

    return "<br/>".join(lines) if lines else "-"


def _build_company_details(organization: Any) -> list[str]:
    """Build organization header details."""
    if organization is None:
        return ["AI Sales Agent"]

    organization_name = (
        getattr(organization, "name", None)
        or getattr(organization, "company_name", None)
        or "AI Sales Agent"
    )

    details = [str(organization_name)]

    email = getattr(organization, "email", None)
    phone = getattr(organization, "phone", None)
    website = getattr(organization, "website", None)

    if email:
        details.append(str(email))

    if phone:
        details.append(str(phone))

    if website:
        details.append(str(website))

    return details


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create reusable PDF paragraph styles."""
    sample_styles = getSampleStyleSheet()

    return {
        "company_name": ParagraphStyle(
            name="CompanyName",
            parent=sample_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "company_detail": ParagraphStyle(
            name="CompanyDetail",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
        ),
        "document_title": ParagraphStyle(
            name="DocumentTitle",
            parent=sample_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_RIGHT,
            spaceAfter=4,
        ),
        "quotation_number": ParagraphStyle(
            name="QuotationNumber",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_RIGHT,
        ),
        "section_title": ParagraphStyle(
            name="SectionTitle",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=5,
        ),
        "normal": ParagraphStyle(
            name="PDFNormal",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            name="PDFSmall",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
        "small_right": ParagraphStyle(
            name="PDFSmallRight",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
        ),
        "table_header": ParagraphStyle(
            name="TableHeader",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            name="TableCell",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
        "table_cell_right": ParagraphStyle(
            name="TableCellRight",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
        ),
        "total_label": ParagraphStyle(
            name="TotalLabel",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            name="TotalValue",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT,
        ),
        "grand_total_label": ParagraphStyle(
            name="GrandTotalLabel",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.white,
            alignment=TA_RIGHT,
        ),
        "grand_total_value": ParagraphStyle(
            name="GrandTotalValue",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.white,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            name="Footer",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#6B7280"),
            alignment=TA_CENTER,
        ),
    }


def _draw_page_footer(
    canvas,
    document,
) -> None:
    """Draw a footer and page number on every page."""
    canvas.saveState()

    canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
    canvas.setLineWidth(0.5)
    canvas.line(
        document.leftMargin,
        14 * mm,
        PAGE_WIDTH - document.rightMargin,
        14 * mm,
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6B7280"))

    canvas.drawString(
        document.leftMargin,
        9 * mm,
        "Generated by AI Sales Agent",
    )

    canvas.drawRightString(
        PAGE_WIDTH - document.rightMargin,
        9 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


def generate_quotation_pdf(
    quotation: Quotation,
) -> bytes:
    """Generate and return a complete quotation PDF."""
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title=_safe_text(
            getattr(quotation, "quotation_number", None),
            "Quotation",
        ),
        author="AI Sales Agent",
        subject="Sales quotation",
    )

    styles = _build_styles()
    story: list[Any] = []

    currency = _safe_text(
        getattr(quotation, "currency", None),
        "USD",
    )

    customer = _get_customer(quotation)
    organization = _get_organization(quotation)

    company_details = _build_company_details(organization)

    company_story = [
        Paragraph(
            company_details[0],
            styles["company_name"],
        )
    ]

    for detail in company_details[1:]:
        company_story.append(
            Paragraph(
                detail,
                styles["company_detail"],
            )
        )

    quotation_number = _safe_text(
        getattr(quotation, "quotation_number", None),
        "-",
    )

    title_story = [
        Paragraph(
            "QUOTATION",
            styles["document_title"],
        ),
        Paragraph(
            quotation_number,
            styles["quotation_number"],
        ),
    ]

    header_table = Table(
        [[company_story, title_story]],
        colWidths=[110 * mm, 68 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 9 * mm))

    customer_name = (
        getattr(customer, "company_name", None)
        or getattr(customer, "name", None)
        or "-"
    )

    contact_name = getattr(customer, "contact_name", None)
    customer_email = getattr(customer, "email", None)
    customer_phone = getattr(customer, "phone", None)
    customer_tax_number = getattr(customer, "tax_number", None)

    customer_lines = [
        Paragraph(
            f"<b>{_safe_text(customer_name, '-')}</b>",
            styles["normal"],
        )
    ]

    if contact_name:
        customer_lines.append(
            Paragraph(
                _safe_text(contact_name),
                styles["normal"],
            )
        )

    customer_lines.append(
        Paragraph(
            _build_customer_address(customer),
            styles["normal"],
        )
    )

    if customer_email:
        customer_lines.append(
            Paragraph(
                _safe_text(customer_email),
                styles["normal"],
            )
        )

    if customer_phone:
        customer_lines.append(
            Paragraph(
                _safe_text(customer_phone),
                styles["normal"],
            )
        )

    if customer_tax_number:
        customer_lines.append(
            Paragraph(
                f"Tax number: {_safe_text(customer_tax_number)}",
                styles["normal"],
            )
        )

    details_data = [
        [
            Paragraph(
                "BILL TO",
                styles["section_title"],
            ),
            Paragraph(
                "QUOTATION DETAILS",
                styles["section_title"],
            ),
        ],
        [
            customer_lines,
            Table(
                [
                    [
                        Paragraph(
                            "<b>Issue date</b>",
                            styles["small"],
                        ),
                        Paragraph(
                            _format_date(
                                getattr(
                                    quotation,
                                    "issue_date",
                                    None,
                                )
                            ),
                            styles["small_right"],
                        ),
                    ],
                    [
                        Paragraph(
                            "<b>Expiry date</b>",
                            styles["small"],
                        ),
                        Paragraph(
                            _format_date(
                                getattr(
                                    quotation,
                                    "expiry_date",
                                    None,
                                )
                            ),
                            styles["small_right"],
                        ),
                    ],
                    [
                        Paragraph(
                            "<b>Status</b>",
                            styles["small"],
                        ),
                        Paragraph(
                            _safe_text(
                                getattr(
                                    quotation,
                                    "status",
                                    None,
                                ),
                                "draft",
                            ).replace("_", " ").title(),
                            styles["small_right"],
                        ),
                    ],
                    [
                        Paragraph(
                            "<b>Currency</b>",
                            styles["small"],
                        ),
                        Paragraph(
                            currency,
                            styles["small_right"],
                        ),
                    ],
                ],
                colWidths=[30 * mm, 35 * mm],
                style=TableStyle(
                    [
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            0,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            0,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            2,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            3,
                        ),
                    ]
                ),
            ),
        ],
    ]

    details_table = Table(
        details_data,
        colWidths=[105 * mm, 73 * mm],
    )

    details_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#F3F4F6"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.75,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#E5E7EB"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(details_table)
    story.append(Spacer(1, 8 * mm))

    items = list(getattr(quotation, "items", None) or [])

    item_rows: list[list[Any]] = [
        [
            Paragraph("#", styles["table_header"]),
            Paragraph("Description", styles["table_header"]),
            Paragraph("Qty", styles["table_header"]),
            Paragraph("Unit", styles["table_header"]),
            Paragraph("Unit price", styles["table_header"]),
            Paragraph("Discount", styles["table_header"]),
            Paragraph("Tax", styles["table_header"]),
            Paragraph("Total", styles["table_header"]),
        ]
    ]

    sorted_items = sorted(
        items,
        key=lambda item: (
            getattr(item, "sort_order", None) or 0
        ),
    )

    for index, item in enumerate(sorted_items, start=1):
        description = _safe_text(
            getattr(item, "description", None),
            "-",
        )

        quantity = getattr(item, "quantity", 0)
        unit = _safe_text(
            getattr(item, "unit", None),
            "-",
        )
        unit_price = getattr(item, "unit_price", 0)
        discount_rate = getattr(item, "discount_rate", 0)
        tax_rate = getattr(item, "tax_rate", 0)
        line_total = getattr(item, "line_total", 0)

        item_rows.append(
            [
                Paragraph(
                    str(index),
                    styles["table_cell"],
                ),
                Paragraph(
                    description,
                    styles["table_cell"],
                ),
                Paragraph(
                    _format_number(quantity),
                    styles["table_cell_right"],
                ),
                Paragraph(
                    unit,
                    styles["table_cell"],
                ),
                Paragraph(
                    _format_money(unit_price, currency),
                    styles["table_cell_right"],
                ),
                Paragraph(
                    f"{_format_number(discount_rate)}%",
                    styles["table_cell_right"],
                ),
                Paragraph(
                    f"{_format_number(tax_rate)}%",
                    styles["table_cell_right"],
                ),
                Paragraph(
                    _format_money(line_total, currency),
                    styles["table_cell_right"],
                ),
            ]
        )

    item_table = Table(
        item_rows,
        repeatRows=1,
        colWidths=[
            8 * mm,
            48 * mm,
            15 * mm,
            17 * mm,
            25 * mm,
            19 * mm,
            17 * mm,
            29 * mm,
        ],
    )

    item_style_commands = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#1F2937"),
        ),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor("#D1D5DB"),
        ),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for row_number in range(1, len(item_rows)):
        if row_number % 2 == 0:
            item_style_commands.append(
                (
                    "BACKGROUND",
                    (0, row_number),
                    (-1, row_number),
                    colors.HexColor("#F9FAFB"),
                )
            )

    item_table.setStyle(
        TableStyle(item_style_commands)
    )

    story.append(item_table)
    story.append(Spacer(1, 7 * mm))

    subtotal = getattr(quotation, "subtotal", 0)
    discount_amount = getattr(
        quotation,
        "discount_amount",
        0,
    )
    tax_amount = getattr(quotation, "tax_amount", 0)
    total_amount = getattr(quotation, "total_amount", 0)

    totals_table = Table(
        [
            [
                "",
                Paragraph(
                    "Subtotal",
                    styles["total_label"],
                ),
                Paragraph(
                    _format_money(subtotal, currency),
                    styles["total_value"],
                ),
            ],
            [
                "",
                Paragraph(
                    "Discount",
                    styles["total_label"],
                ),
                Paragraph(
                    f"- {_format_money(discount_amount, currency)}",
                    styles["total_value"],
                ),
            ],
            [
                "",
                Paragraph(
                    "Tax",
                    styles["total_label"],
                ),
                Paragraph(
                    _format_money(tax_amount, currency),
                    styles["total_value"],
                ),
            ],
            [
                "",
                Paragraph(
                    "TOTAL",
                    styles["grand_total_label"],
                ),
                Paragraph(
                    _format_money(total_amount, currency),
                    styles["grand_total_value"],
                ),
            ],
        ],
        colWidths=[100 * mm, 38 * mm, 40 * mm],
    )

    totals_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                (
                    "LINEABOVE",
                    (1, 0),
                    (-1, 0),
                    0.75,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "LINEBELOW",
                    (1, 0),
                    (-1, 2),
                    0.5,
                    colors.HexColor("#E5E7EB"),
                ),
                (
                    "BACKGROUND",
                    (1, 3),
                    (-1, 3),
                    colors.HexColor("#1F2937"),
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(totals_table)

    notes = getattr(quotation, "notes", None)
    terms = getattr(quotation, "terms", None)

    supplementary_content: list[Any] = []

    if notes:
        supplementary_content.extend(
            [
                Spacer(1, 8 * mm),
                Paragraph(
                    "Notes",
                    styles["section_title"],
                ),
                Paragraph(
                    _safe_text(notes),
                    styles["normal"],
                ),
            ]
        )

    if terms:
        supplementary_content.extend(
            [
                Spacer(1, 6 * mm),
                Paragraph(
                    "Terms and Conditions",
                    styles["section_title"],
                ),
                Paragraph(
                    _safe_text(terms),
                    styles["normal"],
                ),
            ]
        )

    if supplementary_content:
        story.append(
            KeepTogether(supplementary_content)
        )

    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "Thank you for your business.",
            styles["footer"],
        )
    )

    document.build(
        story,
        onFirstPage=_draw_page_footer,
        onLaterPages=_draw_page_footer,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes