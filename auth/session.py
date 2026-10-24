"""
Session state manager for Streamlit with persistent session tokens.
"""
from __future__ import annotations

from typing import Optional
import streamlit as st

from auth.security import generate_token
from database.db_service import (
    create_session_token,
    get_valid_session,
    delete_session_token,
    update_last_login,
)
from database.models import User


def init_session() -> Optional[User]:
    """
    Validates and restores the user session from query params or session state.
    Returns the authenticated User or None.
    """
    token = st.query_params.get("session") or st.session_state.get("session_token")
    if not token:
        st.session_state["user"] = None
        st.session_state["session_token"] = None
        return None

    # Check database for valid unexpired session
    valid = get_valid_session(token)
    if not valid:
        # Invalid or expired token
        st.query_params.clear()
        st.session_state["user"] = None
        st.session_state["session_token"] = None
        return None

    _, user = valid
    st.session_state["user"] = user
    st.session_state["session_token"] = token
    # Keep query param synchronized for browser refreshes
    if st.query_params.get("session") != token:
        st.query_params["session"] = token

    return user


def get_current_user() -> Optional[User]:
    """Returns the currently authenticated user from session state."""
    return st.session_state.get("user")


def login_user(user: User, remember: bool = True) -> None:
    """Creates a persistent session in DB and logs the user into Streamlit."""
    token = generate_token(32)
    create_session_token(user.id, token, expiry_hours=168 if remember else 24)
    update_last_login(user.id)

    st.session_state["user"] = user
    st.session_state["session_token"] = token
    st.query_params["session"] = token
    st.session_state["view"] = "dashboard"


def logout_user() -> None:
    """Terminates the active session and clears query params and session state."""
    token = st.session_state.get("session_token") or st.query_params.get("session")
    if token:
        delete_session_token(token)

    st.session_state.pop("user", None)
    st.session_state.pop("session_token", None)
    st.session_state.pop("current_case_id", None)
    st.query_params.clear()
    st.session_state["view"] = "landing"
    st.rerun()
