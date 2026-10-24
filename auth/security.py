"""
Cryptographic security, password hashing, strength estimation, and token generation.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from typing import Tuple, Dict, Any

try:
    import bcrypt
except ImportError:
    bcrypt = None


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random URL-safe token."""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> Tuple[str, str]:
    """
    Hash a password securely using bcrypt (if available) or PBKDF2-HMAC-SHA256.
    Returns (password_hash, salt).
    """
    if bcrypt is not None:
        salt = bcrypt.gensalt().decode("utf-8")
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt.encode("utf-8")).decode("utf-8")
        return hashed, salt
    else:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        ).hex()
        return f"pbkdf2${hashed}", salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a plain password against the stored hash and salt."""
    if not password or not hashed:
        return False
    try:
        if hashed.startswith("pbkdf2$"):
            clean_hash = hashed.split("$", 1)[1]
            calculated = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                100000,
            ).hex()
            return hmac.compare_digest(clean_hash, calculated)
        elif bcrypt is not None and hashed.startswith("$2"):
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        else:
            # Fallback to PBKDF2 verification
            calculated = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                100000,
            ).hex()
            return hmac.compare_digest(hashed, calculated)
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """Basic RFC-compliant email regex validation."""
    if not email or len(email) > 254:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def evaluate_password_strength(password: str) -> Dict[str, Any]:
    """
    Evaluates password strength and returns a dictionary with score (0-4),
    label, color, and list of passed requirements.
    """
    p = password or ""
    length_ok = len(p) >= 8
    upper_ok = bool(re.search(r"[A-Z]", p))
    lower_ok = bool(re.search(r"[a-z]", p))
    digit_ok = bool(re.search(r"\d", p))
    special_ok = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", p))

    score = 0
    if length_ok:
        score += 1
    if upper_ok and lower_ok:
        score += 1
    if digit_ok:
        score += 1
    if special_ok:
        score += 1

    labels = {
        0: ("Very Weak", "#ef4444", 15),
        1: ("Weak", "#f97316", 35),
        2: ("Moderate", "#f59e0b", 60),
        3: ("Good", "#0ea5e9", 80),
        4: ("Strong (Forensic Grade)", "#00e5a8", 100),
    }

    label, color, percent = labels.get(score, ("Weak", "#ef4444", 20))

    return {
        "score": score,
        "label": label,
        "color": color,
        "percent": percent,
        "checks": {
            "At least 8 characters": length_ok,
            "Uppercase & lowercase letters": upper_ok and lower_ok,
            "At least one number (0-9)": digit_ok,
            "At least one special symbol": special_ok,
        },
    }
