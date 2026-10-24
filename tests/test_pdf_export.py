"""
Unit tests for court-ready forensic PDF generation and checksum verification.
"""
import os
import uuid
import pytest

from database.connection import init_db
from database.db_service import create_user, create_case
from auth.security import hash_password
from reporting.pdf_generator import generate_forensic_pdf


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_pdf_generation_and_checksum():
    h, s = hash_password("Password!1234")
    user = create_user(
        email=f"reporter_{uuid.uuid4().hex[:6]}@lab.org",
        full_name="Lead Examiner Abby Sciuto",
        badge_number="NCIS-042",
        department="Forensic Services Division",
        password_hash=h,
        salt=s,
    )
    case = create_case(
        user_id=user.id,
        title="Armed Burglary Forensic Examination",
        incident_type="Burglary",
        status="In Progress",
    )

    analyses = {
        "IMG-001": {
            "threat": "High",
            "scene": "Burglary",
            "engine": "RT-DETR (Local Forensic Baseline)",
            "detections": [
                {"label": "forced_entry", "confidence": 0.94, "bbox": [10, 10, 80, 90]},
                {"label": "edged_weapon", "confidence": 0.88, "bbox": [100, 120, 160, 200]},
            ],
            "leads": ["P1 - Recover edged weapon; preserve for latent fingerprints."],
        }
    }

    custody_log = [
        {
            "Evidence ID": "IMG-001",
            "Timestamp (UTC)": "2026-10-23T21:00:00Z",
            "Action": "Evidence ingested",
            "Investigator": "Examiner Abby (NCIS-042)",
            "SHA-256": "abcdef1234567890…",
        }
    ]

    pdf_bytes, file_path, digest = generate_forensic_pdf(
        case=case,
        investigator_name=user.full_name,
        badge_number=user.badge_number,
        department=user.department,
        analyses=analyses,
        evidence_items=[],
        ledger=[],
        custody_log=custody_log,
    )

    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
    assert os.path.exists(file_path)
    assert len(digest) == 64
