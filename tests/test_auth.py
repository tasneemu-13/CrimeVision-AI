"""
Unit tests for authentication, password hashing, strength calculation, and session tokens.
"""
import uuid
import pytest
from auth.security import (
    hash_password,
    verify_password,
    validate_email,
    evaluate_password_strength,
    generate_token,
)
from database.connection import init_db
from database.db_service import (
    create_user,
    get_user_by_email,
    create_session_token,
    get_valid_session,
    delete_session_token,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_password_hashing_and_verification():
    raw_pwd = "SuperSecretForensicPassword!123"
    hashed, salt = hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert salt is not None
    assert verify_password(raw_pwd, hashed, salt) is True
    assert verify_password("WrongPassword999", hashed, salt) is False
    assert verify_password("", hashed, salt) is False


def test_email_validation():
    assert validate_email("investigator@police.gov") is True
    assert validate_email("officer.smith+special@agency.org") is True
    assert validate_email("invalid-email") is False
    assert validate_email("@domain.com") is False
    assert validate_email("") is False


def test_password_strength_evaluation():
    weak = evaluate_password_strength("abc")
    assert weak["score"] < 2

    moderate = evaluate_password_strength("Password123")
    assert moderate["score"] >= 2

    strong = evaluate_password_strength("C0mpl3x#P@ssw0rd!2026")
    assert strong["score"] >= 3
    assert strong["percent"] >= 75


def test_user_creation_and_session_token():
    unique_email = f"test_{uuid.uuid4().hex[:8]}@forensics.gov"
    hashed, salt = hash_password("SecurePassword!894")
    user = create_user(
        email=unique_email,
        full_name="Agent Dana Scully",
        password_hash=hashed,
        salt=salt,
        badge_number="FBI-2311",
        department="Unexplained Crimes Unit",
    )

    assert user.id is not None
    assert user.email == unique_email
    assert user.badge_number == "FBI-2311"

    # Fetch user
    fetched = get_user_by_email(unique_email)
    assert fetched is not None
    assert fetched.id == user.id

    # Session token management
    token = generate_token(32)
    session_obj = create_session_token(user.id, token, expiry_hours=24)
    assert session_obj.token == token

    # Validate active session
    valid = get_valid_session(token)
    assert valid is not None
    sess, session_user = valid
    assert session_user.id == user.id

    # Terminate session
    delete_session_token(token)
    assert get_valid_session(token) is None
