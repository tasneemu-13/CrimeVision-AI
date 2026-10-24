"""
Database services and CRUD operations with strict multi-user case isolation.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from database.connection import get_db, init_db
from database.models import (
    User,
    Session as UserSession,
    Case,
    Evidence,
    AnalysisResult,
    LedgerEvent,
    CustodyEvent,
    Report,
    ChatMessage,
    utc_now,
)


class AccessDeniedError(Exception):
    """Raised when an operation violates user data isolation boundaries."""
    pass


# ----------------------------------------------------------------------------
# User & Session Services
# ----------------------------------------------------------------------------
def create_user(
    email: str,
    full_name: str,
    password_hash: str,
    salt: str,
    badge_number: Optional[str] = None,
    department: Optional[str] = None,
) -> User:
    with get_db() as db:
        user = User(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            badge_number=badge_number.strip() if badge_number else None,
            department=department.strip() if department else None,
            password_hash=password_hash,
            salt=salt,
            created_at=utc_now(),
        )
        db.add(user)
        db.flush()
        db.refresh(user)
        return user


def get_user_by_email(email: str) -> Optional[User]:
    with get_db() as db:
        return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def get_user_by_id(user_id: str) -> Optional[User]:
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()


def update_last_login(user_id: str) -> None:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = utc_now()


def update_user_password(user_id: str, new_hash: str, new_salt: str) -> bool:
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.password_hash = new_hash
            user.salt = new_salt
            return True
        return False


def create_session_token(user_id: str, token: str, expiry_hours: int = 168) -> UserSession:
    with get_db() as db:
        # Delete any existing sessions for this token if any
        db.query(UserSession).filter(UserSession.token == token).delete()
        sess = UserSession(
            token=token,
            user_id=user_id,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(hours=expiry_hours),
        )
        db.add(sess)
        db.flush()
        db.refresh(sess)
        return sess


def get_valid_session(token: str) -> Optional[tuple[UserSession, User]]:
    if not token:
        return None
    with get_db() as db:
        now = utc_now()
        sess = (
            db.query(UserSession)
            .filter(UserSession.token == token, UserSession.expires_at > now)
            .first()
        )
        if not sess:
            return None
        user = db.query(User).filter(User.id == sess.user_id).first()
        if not user:
            return None
        return sess, user


def delete_session_token(token: str) -> None:
    if not token:
        return
    with get_db() as db:
        db.query(UserSession).filter(UserSession.token == token).delete()


# ----------------------------------------------------------------------------
# Case Services (Strictly user-scoped)
# ----------------------------------------------------------------------------
def generate_case_id() -> str:
    today_str = datetime.now().strftime("%Y%m%d")
    rand_suffix = random.randint(1000, 9999)
    return f"CV-{today_str}-{rand_suffix}"


def create_case(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    incident_type: str = "Burglary",
    status: str = "Open",
    location: Optional[str] = None,
    incident_date: Optional[str] = None,
    custom_case_id: Optional[str] = None,
) -> Case:
    case_id = (custom_case_id.strip() if custom_case_id and custom_case_id.strip() else generate_case_id())
    with get_db() as db:
        # Ensure ID is unique
        existing = db.query(Case).filter(Case.id == case_id).first()
        if existing:
            case_id = generate_case_id()

        case = Case(
            id=case_id,
            user_id=user_id,
            title=title.strip(),
            description=description.strip() if description else "",
            incident_type=incident_type,
            status=status,
            location=location.strip() if location else "",
            incident_date=incident_date.strip() if incident_date else datetime.now().strftime("%Y-%m-%d %H:%M"),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(case)
        db.flush()
        db.refresh(case)
        return case


def get_user_cases(
    user_id: str,
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "newest",
) -> List[Case]:
    with get_db() as db:
        q = db.query(Case).filter(Case.user_id == user_id)

        if status_filter and status_filter != "All":
            q = q.filter(Case.status == status_filter)

        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            q = q.filter(
                (Case.title.ilike(sq))
                | (Case.id.ilike(sq))
                | (Case.description.ilike(sq))
                | (Case.location.ilike(sq))
                | (Case.incident_type.ilike(sq))
            )

        if sort_by == "oldest":
            q = q.order_by(Case.created_at.asc())
        elif sort_by == "title":
            q = q.order_by(Case.title.asc())
        else:  # newest
            q = q.order_by(desc(Case.updated_at))

        return q.all()


def get_case_for_user(case_id: str, user_id: str) -> Optional[Case]:
    """Retrieve a single case strictly scoped to the requesting user."""
    with get_db() as db:
        return db.query(Case).filter(Case.id == case_id, Case.user_id == user_id).first()


def update_case(
    case_id: str,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    incident_type: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    incident_date: Optional[str] = None,
) -> Optional[Case]:
    with get_db() as db:
        case = db.query(Case).filter(Case.id == case_id, Case.user_id == user_id).first()
        if not case:
            return None
        if title is not None:
            case.title = title.strip()
        if description is not None:
            case.description = description.strip()
        if incident_type is not None:
            case.incident_type = incident_type
        if status is not None:
            case.status = status
        if location is not None:
            case.location = location.strip()
        if incident_date is not None:
            case.incident_date = incident_date.strip()
        case.updated_at = utc_now()
        db.flush()
        db.refresh(case)
        return case


def delete_case(case_id: str, user_id: str) -> bool:
    with get_db() as db:
        case = db.query(Case).filter(Case.id == case_id, Case.user_id == user_id).first()
        if not case:
            return False
        db.delete(case)
        return True


def get_dashboard_metrics(user_id: str) -> Dict[str, Any]:
    """Calculate real, persistent metrics from stored records for authenticated user."""
    with get_db() as db:
        total_cases = db.query(func.count(Case.id)).filter(Case.user_id == user_id).scalar() or 0
        active_investigations = (
            db.query(func.count(Case.id))
            .filter(Case.user_id == user_id, Case.status.in_(["Open", "In Progress"]))
            .scalar()
            or 0
        )
        total_evidence = (
            db.query(func.count(Evidence.id)).filter(Evidence.user_id == user_id).scalar() or 0
        )
        total_reports = (
            db.query(func.count(Report.id)).filter(Report.user_id == user_id).scalar() or 0
        )
        recent_cases = (
            db.query(Case)
            .filter(Case.user_id == user_id)
            .order_by(desc(Case.updated_at))
            .limit(5)
            .all()
        )
        recent_activity = (
            db.query(CustodyEvent)
            .filter(CustodyEvent.user_id == user_id)
            .order_by(desc(CustodyEvent.timestamp_utc))
            .limit(8)
            .all()
        )

        return {
            "total_cases": total_cases,
            "active_investigations": active_investigations,
            "total_evidence": total_evidence,
            "total_reports": total_reports,
            "recent_cases": recent_cases,
            "recent_activity": recent_activity,
        }


# ----------------------------------------------------------------------------
# Evidence Services (Scoped to case & user)
# ----------------------------------------------------------------------------
def get_next_evidence_id(case_id: str, user_id: str, prefix: str) -> str:
    with get_db() as db:
        count = (
            db.query(func.count(Evidence.id))
            .filter(Evidence.case_id == case_id, Evidence.user_id == user_id, Evidence.evidence_type == prefix)
            .scalar()
            or 0
        )
        return f"{prefix}-{count + 1:03d}"


def save_evidence(
    case_id: str,
    user_id: str,
    evidence_id: str,
    evidence_type: str,
    filename: str,
    file_path: str,
    file_size: int,
    mime_type: str,
    sha256_hash: str,
    notes: Optional[str] = None,
) -> Evidence:
    with get_db() as db:
        # Verify case ownership
        case = db.query(Case).filter(Case.id == case_id, Case.user_id == user_id).first()
        if not case:
            raise AccessDeniedError(f"Case {case_id} not found or not owned by user.")

        evidence = Evidence(
            id=evidence_id,
            case_id=case_id,
            user_id=user_id,
            evidence_type=evidence_type,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            uploaded_at=utc_now(),
            notes=notes,
        )
        db.add(evidence)
        case.updated_at = utc_now()
        db.flush()
        db.refresh(evidence)
        return evidence


def get_case_evidence(case_id: str, user_id: str) -> List[Evidence]:
    with get_db() as db:
        return (
            db.query(Evidence)
            .filter(Evidence.case_id == case_id, Evidence.user_id == user_id)
            .order_by(Evidence.uploaded_at.asc())
            .all()
        )


def get_evidence_by_id(evidence_id: str, case_id: str, user_id: str) -> Optional[Evidence]:
    with get_db() as db:
        return (
            db.query(Evidence)
            .filter(Evidence.id == evidence_id, Evidence.case_id == case_id, Evidence.user_id == user_id)
            .first()
        )


def delete_evidence(evidence_id: str, case_id: str, user_id: str) -> bool:
    with get_db() as db:
        ev = (
            db.query(Evidence)
            .filter(Evidence.id == evidence_id, Evidence.case_id == case_id, Evidence.user_id == user_id)
            .first()
        )
        if not ev:
            return False
        db.delete(ev)
        return True


# ----------------------------------------------------------------------------
# Analysis Result Services
# ----------------------------------------------------------------------------
def save_analysis_result(
    evidence_id: str,
    case_id: str,
    user_id: str,
    analysis_type: str,
    engine_used: str,
    result_data: Dict[str, Any],
    status: str = "completed",
) -> AnalysisResult:
    with get_db() as db:
        # Remove previous analysis result for this evidence if any
        db.query(AnalysisResult).filter(
            AnalysisResult.evidence_id == evidence_id,
            AnalysisResult.case_id == case_id,
            AnalysisResult.user_id == user_id,
        ).delete()

        res = AnalysisResult(
            evidence_id=evidence_id,
            case_id=case_id,
            user_id=user_id,
            analysis_type=analysis_type,
            engine_used=engine_used,
            status=status,
            result_json=json.dumps(result_data),
            created_at=utc_now(),
        )
        db.add(res)
        db.flush()
        db.refresh(res)
        return res


def get_analysis_for_evidence(evidence_id: str, case_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        row = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.evidence_id == evidence_id,
                AnalysisResult.case_id == case_id,
                AnalysisResult.user_id == user_id,
            )
            .order_by(desc(AnalysisResult.created_at))
            .first()
        )
        if not row:
            return None
        try:
            parsed = json.loads(row.result_json)
            parsed["engine_used"] = row.engine_used
            parsed["analysis_type"] = row.analysis_type
            parsed["analysis_status"] = row.status
            return parsed
        except Exception:
            return None


def get_all_analyses_for_case(case_id: str, user_id: str) -> Dict[str, Dict[str, Any]]:
    """Returns a dictionary mapping evidence_id -> analysis result dict."""
    with get_db() as db:
        rows = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.case_id == case_id, AnalysisResult.user_id == user_id)
            .all()
        )
        results = {}
        for r in rows:
            try:
                d = json.loads(r.result_json)
                d["engine_used"] = r.engine_used
                d["analysis_type"] = r.analysis_type
                results[r.evidence_id] = d
            except Exception:
                continue
        return results


# ----------------------------------------------------------------------------
# Ledger Services
# ----------------------------------------------------------------------------
def sync_ledger_events(
    case_id: str,
    user_id: str,
    evidence_id: str,
    events: List[Dict[str, Any]],
) -> None:
    """Overwrites ledger events for a given evidence item."""
    with get_db() as db:
        db.query(LedgerEvent).filter(
            LedgerEvent.case_id == case_id,
            LedgerEvent.user_id == user_id,
            LedgerEvent.evidence_id == evidence_id,
        ).delete()

        for ev in events:
            le = LedgerEvent(
                id=ev.get("id") or f"{evidence_id}.{random.randint(1000, 9999)}",
                case_id=case_id,
                user_id=user_id,
                evidence_id=evidence_id,
                source=ev.get("source", "IMAGE"),
                t_offset=float(ev.get("t_offset", 0.0)),
                description=ev.get("description", ""),
                legal_category=ev.get("category", "") or ev.get("legal_category", ""),
                confidence=float(ev.get("confidence", 1.0)),
                created_at=utc_now(),
            )
            db.add(le)


def get_case_ledger(case_id: str, user_id: str) -> List[Dict[str, Any]]:
    with get_db() as db:
        rows = (
            db.query(LedgerEvent)
            .filter(LedgerEvent.case_id == case_id, LedgerEvent.user_id == user_id)
            .order_by(LedgerEvent.t_offset.asc(), LedgerEvent.source.asc())
            .all()
        )
        return [
            {
                "id": r.id,
                "evidence_id": r.evidence_id,
                "source": r.source,
                "t_offset": r.t_offset,
                "description": r.description,
                "category": r.legal_category,
                "confidence": r.confidence,
            }
            for r in rows
        ]


# ----------------------------------------------------------------------------
# Chain of Custody Services
# ----------------------------------------------------------------------------
def log_custody_event(
    case_id: str,
    user_id: str,
    evidence_id: str,
    action: str,
    investigator_name: str,
    badge_number: Optional[str] = None,
    sha256_digest: Optional[str] = None,
) -> CustodyEvent:
    with get_db() as db:
        ce = CustodyEvent(
            case_id=case_id,
            user_id=user_id,
            evidence_id=evidence_id,
            action=action,
            investigator_name=investigator_name,
            badge_number=badge_number,
            sha256_digest=sha256_digest,
            timestamp_utc=utc_now(),
        )
        db.add(ce)
        db.flush()
        db.refresh(ce)
        return ce


def get_case_custody_log(case_id: str, user_id: str) -> List[Dict[str, Any]]:
    with get_db() as db:
        rows = (
            db.query(CustodyEvent)
            .filter(CustodyEvent.case_id == case_id, CustodyEvent.user_id == user_id)
            .order_by(CustodyEvent.timestamp_utc.asc())
            .all()
        )
        return [
            {
                "Evidence ID": r.evidence_id,
                "Timestamp (UTC)": r.timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Action": r.action,
                "Investigator": f"{r.investigator_name} ({r.badge_number or '-'})",
                "SHA-256": (r.sha256_digest[:16] + "…") if r.sha256_digest else "",
            }
            for r in rows
        ]


# ----------------------------------------------------------------------------
# Report Services
# ----------------------------------------------------------------------------
def save_report_record(
    case_id: str,
    user_id: str,
    filename: str,
    file_path: str,
    sha256_hash: str,
    investigator_name: Optional[str] = None,
    badge_number: Optional[str] = None,
) -> Report:
    with get_db() as db:
        rpt = Report(
            case_id=case_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            sha256_hash=sha256_hash,
            signoff_investigator=investigator_name,
            signoff_badge=badge_number,
            generated_at=utc_now(),
        )
        db.add(rpt)
        db.flush()
        db.refresh(rpt)
        return rpt


def get_case_reports(case_id: str, user_id: str) -> List[Report]:
    with get_db() as db:
        return (
            db.query(Report)
            .filter(Report.case_id == case_id, Report.user_id == user_id)
            .order_by(desc(Report.generated_at))
            .all()
        )


# ----------------------------------------------------------------------------
# Chat History Services (Persistent per case)
# ----------------------------------------------------------------------------
def save_chat_message(case_id: str, user_id: str, role: str, content: str) -> ChatMessage:
    with get_db() as db:
        msg = ChatMessage(
            case_id=case_id,
            user_id=user_id,
            role=role,
            content=content,
            timestamp_utc=utc_now(),
        )
        db.add(msg)
        db.flush()
        db.refresh(msg)
        return msg


def get_case_chat_history(case_id: str, user_id: str) -> List[Dict[str, str]]:
    with get_db() as db:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.case_id == case_id, ChatMessage.user_id == user_id)
            .order_by(ChatMessage.timestamp_utc.asc())
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in msgs]


def clear_case_chat_history(case_id: str, user_id: str) -> None:
    with get_db() as db:
        db.query(ChatMessage).filter(
            ChatMessage.case_id == case_id, ChatMessage.user_id == user_id
        ).delete()
