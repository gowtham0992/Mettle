from __future__ import annotations

from datetime import date
from enum import StrEnum
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image as PillowImage
from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from mettle.communication import RecordedDelivery
from mettle.domain import CampaignPlan, InspectionNotice
from mettle.evidence import EvidenceAssessment


class PacketStatus(StrEnum):
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class PacketRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    packet_id: str
    status: PacketStatus
    prepared_on: date
    citations_total: int = Field(ge=1)
    citations_ready: int = Field(ge=0)
    approval_id: str
    approval_decision: str | None = None


_SAMPLE_FILES = {
    "panel_closeup_insufficient": "panel-closeup-insufficient.png",
    "panel_wide_measured": "panel-wide-measured.png",
    "framing_plates_complete": "framing-plates-visible-v2.png",
    "mechanical_access_wide": "mechanical-access-wide.png",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MettleTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=27,
            textColor=colors.HexColor("#191d20"),
            spaceAfter=12,
        ),
        "eyebrow": ParagraphStyle(
            "MettleEyebrow",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#b54418"),
            tracking=1.2,
            spaceAfter=5,
        ),
        "heading": ParagraphStyle(
            "MettleHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#23262a"),
            spaceBefore=8,
            spaceAfter=9,
        ),
        "body": ParagraphStyle(
            "MettleBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.5,
            textColor=colors.HexColor("#3a3d36"),
            spaceAfter=7,
        ),
        "quote": ParagraphStyle(
            "MettleQuote",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=8.2,
            leading=12,
            leftIndent=10,
            borderColor=colors.HexColor("#23262a"),
            borderWidth=0,
            borderPadding=8,
            backColor=colors.HexColor("#f3efe3"),
            spaceAfter=10,
        ),
        "stamp": ParagraphStyle(
            "MettleStamp",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#3d6b4f"),
        ),
        "small": ParagraphStyle(
            "MettleSmall",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=7.4,
            leading=10,
            textColor=colors.HexColor("#5e635f"),
        ),
        "detail_label": ParagraphStyle(
            "MettleDetailLabel",
            parent=base["Normal"],
            fontName="Courier-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#6e6a5e"),
        ),
        "detail_value": ParagraphStyle(
            "MettleDetailValue",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#23262a"),
            splitLongWords=True,
        ),
    }


def _draw_page_frame(canvas: Canvas, page_number: int) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.HexColor("#191d20"))
    canvas.rect(0, height - 34, width, 34, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#f2672f"))
    canvas.rect(0, height - 37, width, 3, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#f4f1e9"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(42, height - 22, "METTLE  /  REINSPECTION PACKET")
    canvas.setFillColor(colors.HexColor("#5e635f"))
    canvas.setFont("Courier", 7)
    canvas.drawString(42, 24, "CONTRACTOR-CONTROLLED RECORD  /  NOT A CODE-COMPLIANCE CERTIFICATION")
    canvas.drawRightString(width - 42, 24, f"PAGE {page_number}")
    canvas.restoreState()


class _PacketCanvas(Canvas):
    def showPage(self) -> None:
        _draw_page_frame(self, self.getPageNumber())
        super().showPage()


def _scaled_image(source: Path | BytesIO) -> Image:
    # Lambda's synchronous response limit applies after Mangum base64-encodes
    # the PDF. Re-encoding evidence for the packet keeps a detailed visual
    # record while preventing a few lossless phone photos from overflowing the
    # public response boundary.
    compressed = BytesIO()
    pillow_source: Path | BytesIO
    if isinstance(source, Path):
        pillow_source = source
    else:
        pillow_source = BytesIO(source.getvalue())
    with PillowImage.open(pillow_source) as photo:
        photo.convert("RGB").save(
            compressed,
            format="JPEG",
            quality=82,
            optimize=True,
            progressive=True,
        )
    compressed.seek(0)
    image = Image(compressed)
    max_width = 6.35 * inch
    max_height = 4.25 * inch
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return image


def render_packet_pdf(
    *,
    notice: InspectionNotice,
    plan: CampaignPlan,
    evidence: list[EvidenceAssessment],
    deliveries: list[RecordedDelivery],
    packet: PacketRecord,
    evidence_dir: Path,
    uploaded_photos: dict[str, bytes] | None = None,
) -> bytes:
    """Render an approved packet from validated, server-owned workflow state."""
    if packet.status is not PacketStatus.APPROVED:
        raise ValueError("packet must be approved before rendering")
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=42,
        leftMargin=42,
        topMargin=58,
        bottomMargin=42,
        title=f"Mettle reinspection packet - {notice.notice_id}",
        author="Mettle",
    )
    latest = {item.citation_id: item for item in evidence}
    story = [
        Spacer(1, 0.28 * inch),
        Paragraph("FAILED INSPECTION RECOVERY", styles["eyebrow"]),
        Paragraph("Reinspection evidence packet", styles["title"]),
        Paragraph(
            "A notice-anchored record of corrections, evidence, and contractor decisions.",
            styles["body"],
        ),
        Spacer(1, 0.08 * inch),
    ]
    def detail_row(label_a: str, value_a: str, label_b: str, value_b: str) -> list[Paragraph]:
        return [
            Paragraph(escape(label_a), styles["detail_label"]),
            Paragraph(escape(value_a), styles["detail_value"]),
            Paragraph(escape(label_b), styles["detail_label"]),
            Paragraph(escape(value_b), styles["detail_value"]),
        ]

    details = [
        detail_row("NOTICE", notice.notice_id, "PROPERTY", notice.property_label),
        detail_row(
            "ISSUED",
            notice.issued_on.isoformat(),
            "REINSPECTION",
            notice.reinspection_due_on.isoformat(),
        ),
        detail_row(
            "CITATIONS",
            str(packet.citations_total),
            "READY",
            str(packet.citations_ready),
        ),
    ]
    detail_table = Table(
        details,
        colWidths=[0.78 * inch, 2.17 * inch, 1.0 * inch, 2.4 * inch],
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fbf9f2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dad5c4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([detail_table, Spacer(1, 0.24 * inch)])
    stamp = Table(
        [[Paragraph("APPROVED BY CONTRACTOR", styles["stamp"])], [Paragraph(escape(packet.approval_decision or ""), styles["small"])]],
        colWidths=[6.35 * inch],
    )
    stamp.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.4, colors.HexColor("#3d6b4f")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e7efe4")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend(
        [
            stamp,
            Spacer(1, 0.25 * inch),
            Paragraph("Safety boundary", styles["heading"]),
            Paragraph(
                "Mettle checks whether submitted evidence shows the observable items requested by the notice. "
                "Mettle does not certify code compliance, impersonate the inspector, or submit this packet automatically.",
                styles["body"],
            ),
        ]
    )

    for citation in notice.citations:
        assessment = latest[citation.citation_id]
        uploaded = (uploaded_photos or {}).get(assessment.assessment_id)
        if assessment.contractor_record is not None:
            record = assessment.contractor_record
            evidence_record = [
                Paragraph("CONTRACTOR-REVIEWED SOURCE RECORD", styles["eyebrow"]),
                Paragraph(escape(record.route.replace("_", " ").title()), styles["heading"]),
                Paragraph(escape(f"Reference: {record.reference}"), styles["body"]),
                Paragraph(escape(f"Reviewed by {record.reviewer} on {record.reviewed_on.isoformat()}"), styles["body"]),
                Paragraph(escape(record.details), styles["body"]),
                Paragraph(escape(assessment.explanation), styles["body"]),
                Paragraph("Original source retained by the contractor; not attached or independently authenticated by Mettle.", styles["small"]),
            ]
        elif uploaded is not None:
            image_source: Path | BytesIO = BytesIO(uploaded)
        else:
            filename = _SAMPLE_FILES[assessment.sample_id]
            image_source = evidence_dir / filename
        if assessment.contractor_record is None:
            evidence_record = [
                _scaled_image(image_source),
                Spacer(1, 0.1 * inch),
                Paragraph("EVIDENCE ACCEPTED FOR SUFFICIENCY", styles["eyebrow"]),
                Paragraph(escape(assessment.explanation), styles["body"]),
            ]
        if assessment.contractor_decision:
            evidence_record.extend(
                [
                    Paragraph("CONTRACTOR EVIDENCE DECISION", styles["eyebrow"]),
                    Paragraph(escape(assessment.contractor_decision), styles["body"]),
                ]
            )
        story.extend(
            [
                PageBreak(),
                Paragraph(f"CITATION {escape(citation.citation_id)}  /  {escape(citation.code_reference)}", styles["eyebrow"]),
                Paragraph(escape(citation.trade.value.title()), styles["heading"]),
                Paragraph(f'"{escape(citation.notice_text)}"', styles["quote"]),
                Paragraph("Notice evidence requirements", styles["heading"]),
            ]
        )
        for requirement in assessment.matched_requirements or citation.evidence_requirements:
            story.append(Paragraph(f"- {escape(requirement)}", styles["body"]))
        story.extend(
            [
                Spacer(1, 0.08 * inch),
                KeepTogether(
                    evidence_record
                ),
            ]
        )

    # The communication trail is a first-class fifth page, not content that
    # happens to spill over when a workflow has enough delivery rows.
    story.extend([PageBreak(), Paragraph("RECOVERY RECORD", styles["eyebrow"])])
    story.append(Paragraph("Recovery communication record", styles["heading"]))
    delivery_rows = [["CITATION", "RECIPIENT", "STATUS", "SCHEDULED"]]
    for delivery in deliveries:
        delivery_rows.append(
            [
                escape(delivery.citation_id),
                escape(delivery.recipient.name),
                escape(delivery.status.upper()),
                delivery.scheduled_on.isoformat(),
            ]
        )
    delivery_table = Table(delivery_rows, colWidths=[0.8 * inch, 2.5 * inch, 1.25 * inch, 1.4 * inch], repeatRows=1)
    delivery_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#191d20")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#f4f1e9")),
                ("FONT", (0, 0), (-1, 0), "Courier-Bold", 7),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dad5c4")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(delivery_table)
    doc.build(story, canvasmaker=_PacketCanvas)
    return buffer.getvalue()
