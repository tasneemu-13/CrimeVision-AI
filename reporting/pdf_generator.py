"""
Court-ready forensic PDF export generator using ReportLab.
"""
from __future__ import annotations

import hashlib
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
)

from ai_services.vision import annotate_image
from database.connection import REPORTS_DIR


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def generate_forensic_pdf(
    case: Any,
    investigator_name: str,
    badge_number: str,
    department: Optional[str],
    analyses: Dict[str, Dict[str, Any]],
    evidence_items: List[Any],
    ledger: List[Dict[str, Any]],
    custody_log: List[Dict[str, Any]],
    image_bytes: Optional[bytes] = None,
) -> Tuple[bytes, str, str]:
    """
    Generates a complete forensic PDF report.
    Returns: (pdf_bytes, file_path, sha256_digest)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Forensic Report - {case.id}",
        author=investigator_name,
    )

    ss = getSampleStyleSheet()
    primary_color = colors.HexColor("#0f2942")
    accent_color = colors.HexColor("#008a65")

    h1_style = ParagraphStyle(
        "H1_Style",
        parent=ss["Heading1"],
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "H2_Style",
        parent=ss["Heading2"],
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4,
    )
    normal_style = ParagraphStyle("Norm_Style", parent=ss["Normal"], fontSize=9, leading=12)
    small_style = ParagraphStyle("Small_Style", parent=ss["Normal"], fontSize=7.5, leading=10)
    meta_style = ParagraphStyle(
        "Meta_Style",
        parent=ss["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    def make_table(rows, widths=None):
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return t

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    story = [
        Paragraph("<b>CRIMEVISION AI — MULTIMODAL FORENSIC INTELLIGENCE REPORT</b>", h1_style),
        Paragraph(
            f"<b>Case Reference:</b> {case.id} &nbsp;|&nbsp; <b>Status:</b> {case.status} &nbsp;|&nbsp; "
            f"<b>Incident Category:</b> {case.incident_type}",
            normal_style,
        ),
        Paragraph(
            f"<b>Case Title:</b> {case.title} &nbsp;|&nbsp; <b>Incident Location:</b> {case.location or 'N/A'}",
            normal_style,
        ),
        Paragraph(
            f"<b>Lead Investigator:</b> {investigator_name} &nbsp;|&nbsp; <b>Badge:</b> {badge_number or 'N/A'} "
            f"&nbsp;|&nbsp; <b>Agency:</b> {department or 'N/A'}",
            normal_style,
        ),
        Paragraph(f"<b>Report Generated:</b> {now_utc}", meta_style),
        Spacer(1, 4 * mm),
        Paragraph(
            "<b>STATUTORY FORENSIC ADVISORY:</b> This document contains automated and multimodal AI-assisted forensic "
            "findings compiled for investigative triage. All extracted leads, transcriptions, and biometric/object "
            "detections must be corroborated by a certified forensic practitioner prior to formal judicial submission.",
            small_style,
        ),
        Spacer(1, 4 * mm),
    ]

    # Section 1: Visual Evidence
    img_ev = next((e for e in evidence_items if e.evidence_type == "IMAGE"), None)
    if img_ev and img_ev.id in analyses:
        ir = analyses[img_ev.id]
        story.append(Paragraph("1. Crime Scene Visual Evidence", h2_style))
        story.append(
            Paragraph(
                f"<b>Evidence ID:</b> {img_ev.id} &nbsp;|&nbsp; <b>Threat Level:</b> {ir.get('threat', 'N/A')} "
                f"&nbsp;|&nbsp; <b>Scene Classification:</b> {ir.get('scene', 'N/A')} &nbsp;|&nbsp; "
                f"<b>Engine:</b> {ir.get('engine', 'RT-DETR')}",
                normal_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        # Annotated image if available
        if image_bytes:
            try:
                base_img = Image.open(io.BytesIO(image_bytes))
                ann_img = annotate_image(base_img, ir.get("detections", []))
                img_io = io.BytesIO()
                ann_img.save(img_io, format="PNG")
                img_io.seek(0)
                aspect = ann_img.height / max(1, ann_img.width)
                target_w = 110 * mm
                target_h = min(80 * mm, target_w * aspect)
                story.append(RLImage(img_io, width=target_w, height=target_h))
                story.append(Spacer(1, 2 * mm))
            except Exception:
                pass

        # Detection Table
        dets = ir.get("detections", [])
        if dets:
            table_rows = [["Evidence Class", "Confidence", "Bounding Box [x1,y1,x2,y2]"]]
            for d in dets:
                table_rows.append([d.get("label", ""), f"{d.get('confidence', 0):.2f}", str(d.get("bbox", []))])
            story.append(make_table(table_rows, [45 * mm, 30 * mm, 95 * mm]))
            story.append(Spacer(1, 2 * mm))

        # Investigative leads
        leads = ir.get("leads", [])
        if leads:
            story.append(Paragraph("<b>Prioritized Investigative Leads:</b>", normal_style))
            for l in leads:
                story.append(Paragraph(f"• {l}", small_style))
            story.append(Spacer(1, 4 * mm))

    # Section 2: Witness Audio
    aud_ev = next((e for e in evidence_items if e.evidence_type == "AUDIO"), None)
    if aud_ev and aud_ev.id in analyses:
        ar = analyses[aud_ev.id]
        story.append(Paragraph("2. Witness Audio & Emergency Dispatch Timeline", h2_style))
        story.append(
            Paragraph(
                f"<b>Evidence ID:</b> {aud_ev.id} &nbsp;|&nbsp; <b>Original File:</b> {aud_ev.filename} &nbsp;|&nbsp; "
                f"<b>ASR Engine:</b> {ar.get('engine', 'Whisper ASR')}",
                normal_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        segs = ar.get("segments", [])
        if segs:
            aud_rows = [["t (s)", "Speaker", "Verbatim Statement", "Forensic Tag"]]
            for s in segs:
                aud_rows.append(
                    [
                        f"{s.get('start', 0):.1f}s",
                        s.get("speaker", "Unknown"),
                        Paragraph(s.get("text", ""), small_style),
                        s.get("event", "") or "-",
                    ]
                )
            story.append(make_table(aud_rows, [18 * mm, 26 * mm, 96 * mm, 30 * mm]))
            story.append(Spacer(1, 4 * mm))

    # Section 3: CCTV Video Analysis
    vid_ev = next((e for e in evidence_items if e.evidence_type == "VIDEO"), None)
    if vid_ev and vid_ev.id in analyses:
        vr = analyses[vid_ev.id]
        story.append(Paragraph("3. CCTV Video & Temporal Progression Analysis", h2_style))
        story.append(
            Paragraph(
                f"<b>Evidence ID:</b> {vid_ev.id} &nbsp;|&nbsp; <b>Duration:</b> {vr.get('duration', 0)}s &nbsp;|&nbsp; "
                f"<b>Frames Sampled:</b> {vr.get('frames_sampled', 0)} &nbsp;|&nbsp; <b>Engine:</b> {vr.get('engine', 'OpenCV')}",
                normal_style,
            )
        )
        story.append(Spacer(1, 2 * mm))

        events = vr.get("events", [])
        if events:
            vid_rows = [["Timestamp", "Observed Event", "Legal / Penal Classification", "Conf."]]
            for e in events:
                vid_rows.append(
                    [
                        f"t={e.get('t', 0):.1f}s",
                        Paragraph(e.get("event", ""), small_style),
                        Paragraph(e.get("penal", ""), small_style),
                        f"{e.get('confidence', 0):.2f}",
                    ]
                )
            story.append(make_table(vid_rows, [20 * mm, 65 * mm, 70 * mm, 15 * mm]))
            story.append(Spacer(1, 4 * mm))

    # Section 4: Master Cross-Modal Ledger
    if ledger:
        story.append(PageBreak())
        story.append(Paragraph("4. Master Forensic Event Ledger (Unified Cross-Modal)", h2_style))
        ledger_rows = [["Evidence ID", "Source", "t (s)", "Corroborated Event Description"]]
        for e in ledger:
            ledger_rows.append(
                [
                    e.get("evidence_id", ""),
                    e.get("source", ""),
                    f"{e.get('t_offset', 0):.1f}s",
                    Paragraph(e.get("description", ""), small_style),
                ]
            )
        story.append(make_table(ledger_rows, [30 * mm, 20 * mm, 18 * mm, 102 * mm]))
        story.append(Spacer(1, 4 * mm))

    # Section 5: Chain of Custody
    story.append(Paragraph("5. Chain of Custody & Cryptographic Audit Trail", h2_style))
    if custody_log:
        cust_rows = [["Evidence ID", "Timestamp (UTC)", "Action", "Authorized Personnel", "SHA-256 Digest"]]
        for c in custody_log:
            cust_rows.append(
                [
                    c.get("Evidence ID", ""),
                    c.get("Timestamp (UTC)", ""),
                    c.get("Action", ""),
                    c.get("Investigator", ""),
                    c.get("SHA-256", ""),
                ]
            )
        story.append(make_table(cust_rows, [28 * mm, 36 * mm, 46 * mm, 38 * mm, 22 * mm]))
    else:
        story.append(Paragraph("No chain-of-custody transactions recorded.", normal_style))

    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "<b>INVESTIGATOR CERTIFICATION:</b> I hereby certify under statutory forensic standards that the evidence "
            "documented herein has been preserved, analyzed, and audited without unauthorized alteration.",
            small_style,
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            f"Signature: _____________________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
            f"Date: {now_utc[:10]}",
            normal_style,
        )
    )

    doc.build(story)
    pdf_bytes = buf.getvalue()

    # Save to persistent reports storage
    case_report_dir = REPORTS_DIR / case.id
    case_report_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{case.id}_Forensic_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = case_report_dir / filename

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    digest = sha256_bytes(pdf_bytes)
    return pdf_bytes, str(file_path), digest
