"""
CrimeVision AI — Intelligent Multimodal Forensic Analysis Platform
Production Entrypoint & Application Router.
"""
from __future__ import annotations

import streamlit as st

from auth.session import init_session, get_current_user
from database.connection import init_db
from ui.auth_pages import render_sign_in, render_sign_up, render_forgot_password
from ui.case_workspace import render_case_workspace
from ui.dashboard import render_dashboard
from ui.landing import render_landing_page
from ui.styles import apply_styles

# ----------------------------------------------------------------------------
# Page Configuration
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="CrimeVision AI — Forensic Analysis Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    # 1. Initialize persistent database schema
    init_db()

    # 2. Inject forensic design system CSS
    apply_styles()

    # 3. Synchronize persistent session state & tokens
    user = init_session()

    # 4. View Router
    current_view = st.session_state.get("view", "landing")

    if not user:
        # Unauthenticated routes
        if current_view == "sign_in":
            render_sign_in()
        elif current_view == "sign_up":
            render_sign_up()
        elif current_view == "forgot_password":
            render_forgot_password()
        else:
            render_landing_page()
    else:
        # Authenticated protected routes
        if current_view == "workspace" and st.session_state.get("current_case_id"):
            render_case_workspace(user)
        else:
            render_dashboard(user)


if __name__ == "__main__":
    main()
