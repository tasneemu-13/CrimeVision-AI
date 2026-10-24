"""
Unit tests for database multi-user case isolation and access authorization.
"""
import uuid
import pytest

from auth.security import hash_password
from database.connection import init_db
from database.db_service import (
    create_user,
    create_case,
    get_case_for_user,
    get_user_cases,
    delete_case,
    save_evidence,
    get_case_evidence,
    get_dashboard_metrics,
    log_custody_event,
    get_case_custody_log,
    AccessDeniedError,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def create_mock_user(prefix="investigator"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@test.local"
    h, s = hash_password("ValidPassword!99")
    return create_user(email=email, full_name=f"Agent {prefix.title()}", password_hash=h, salt=s)


def test_multi_user_case_isolation():
    user_a = create_mock_user("alpha")
    user_b = create_mock_user("bravo")

    # User A creates a case
    case_a = create_case(
        user_id=user_a.id,
        title="Classified Alpha Investigation",
        description="Top secret burglary evidence",
        incident_type="Burglary",
        status="Open",
    )

    # User A can retrieve it
    retrieved_a = get_case_for_user(case_a.id, user_a.id)
    assert retrieved_a is not None
    assert retrieved_a.id == case_a.id

    # User B CANNOT retrieve User A's case
    retrieved_b = get_case_for_user(case_a.id, user_b.id)
    assert retrieved_b is None

    # User B's case list does not contain User A's case
    cases_b = get_user_cases(user_b.id)
    assert not any(c.id == case_a.id for c in cases_b)

    # Metrics isolation: User A has 1 case, User B has 0
    metrics_a = get_dashboard_metrics(user_a.id)
    metrics_b = get_dashboard_metrics(user_b.id)
    assert metrics_a["total_cases"] >= 1
    assert metrics_b["total_cases"] == 0

    # User B cannot delete User A's case
    del_res = delete_case(case_a.id, user_b.id)
    assert del_res is False
    assert get_case_for_user(case_a.id, user_a.id) is not None

    # User B cannot upload evidence to User A's case
    with pytest.raises(AccessDeniedError):
        save_evidence(
            case_id=case_a.id,
            user_id=user_b.id,
            evidence_id="IMG-001",
            evidence_type="IMAGE",
            filename="fake.jpg",
            file_path="/tmp/fake.jpg",
            file_size=100,
            mime_type="image/jpeg",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )


def test_evidence_and_custody_isolation():
    user_x = create_mock_user("xray")
    user_y = create_mock_user("yankee")

    case_x = create_case(user_id=user_x.id, title="Case Xray")

    # Ingest evidence for User X
    ev_x = save_evidence(
        case_id=case_x.id,
        user_id=user_x.id,
        evidence_id="IMG-001",
        evidence_type="IMAGE",
        filename="crime_scene.jpg",
        file_path="data/uploads/crime_scene.jpg",
        file_size=2048,
        mime_type="image/jpeg",
        sha256_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    )
    assert ev_x.id == "IMG-001"

    log_custody_event(
        case_id=case_x.id,
        user_id=user_x.id,
        evidence_id="IMG-001",
        action="Ingested photo",
        investigator_name=user_x.full_name,
        sha256_digest=ev_x.sha256_hash,
    )

    # User X sees evidence and custody
    assert len(get_case_evidence(case_x.id, user_x.id)) == 1
    assert len(get_case_custody_log(case_x.id, user_x.id)) == 1

    # User Y sees 0 evidence and 0 custody for case_x
    assert len(get_case_evidence(case_x.id, user_y.id)) == 0
    assert len(get_case_custody_log(case_x.id, user_y.id)) == 0
