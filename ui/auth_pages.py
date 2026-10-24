"""
Authentication views: Sign In, Sign Up, Password Strength Meter, and Password Recovery.
"""
from __future__ import annotations

import streamlit as st

from auth.security import (
    hash_password,
    verify_password,
    validate_email,
    evaluate_password_strength,
)
from auth.session import login_user
from database.db_service import (
    create_user,
    get_user_by_email,
    update_user_password,
)
from ui.components import render_brand_header, render_password_strength_bar


def render_sign_in():
    """Renders the investigator sign-in form with validation and show/hide password."""
    render_brand_header()

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(
            """
            <div style="margin-bottom:20px;">
                <h2 style="margin:0; font-size:1.6rem; color:#ffffff;">Investigator Sign In</h2>
                <p style="margin:4px 0 0; color:#94a3b8; font-size:0.88rem;">
                    Access authorized case workspaces and digital evidence files.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("sign_in_form", clear_on_submit=False):
            email = st.text_input("Investigator Email", placeholder="officer@agency.gov").strip()

            c_pwd, c_show = st.columns([5, 1])
            with c_show:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                show_pwd = st.checkbox("Show", key="si_show_pwd")
            with c_pwd:
                pwd_type = "default" if show_pwd else "password"
                password = st.text_input("Password", type=pwd_type, placeholder="Enter master password")

            remember = st.checkbox("Remember session on this forensic terminal", value=True)
            submit = st.form_submit_button("Sign In to Case Workbench", type="primary", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please provide both investigator email and password.")
            elif not validate_email(email):
                st.error("Invalid email address format.")
            else:
                user = get_user_by_email(email)
                if not user or not verify_password(password, user.password_hash, user.salt or ""):
                    st.error("Authentication failed. Invalid email or password credentials.")
                else:
                    st.success(f"Authentication successful. Welcome, Investigator {user.full_name}.")
                    login_user(user, remember=remember)
                    st.rerun()

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        nav_c1, nav_c2 = st.columns(2)
        with nav_c1:
            if st.button("Forgot password?", use_container_width=True):
                st.session_state["view"] = "forgot_password"
                st.rerun()
        with nav_c2:
            if st.button("Create new account", use_container_width=True):
                st.session_state["view"] = "sign_up"
                st.rerun()

        st.markdown("<div style='text-align:center; margin-top:12px;'>", unsafe_allow_html=True)
        if st.button("← Return to Platform Overview", key="si_back"):
            st.session_state["view"] = "landing"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_sign_up():
    """Renders the investigator registration form with live password evaluation and duplicate validation."""
    render_brand_header()

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(
            """
            <div style="margin-bottom:20px;">
                <h2 style="margin:0; font-size:1.6rem; color:#ffffff;">Register Investigator Profile</h2>
                <p style="margin:4px 0 0; color:#94a3b8; font-size:0.88rem;">
                    Establish verifiable credentials for custody logs and forensic reporting.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        full_name = st.text_input("Full Name", placeholder="e.g. Detective Sarah Connor", key="su_name").strip()
        email = st.text_input("Agency Email", placeholder="e.g. s.connor@police.gov", key="su_email").strip()

        col_b, col_d = st.columns(2)
        with col_b:
            badge = st.text_input("Badge / ID No.", placeholder="e.g. DET-8942", key="su_badge").strip()
        with col_d:
            dept = st.text_input("Department / Unit", placeholder="e.g. Special Investigations Division", key="su_dept").strip()

        c_pwd, c_show = st.columns([5, 1])
        with c_show:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            show_pwd = st.checkbox("Show", key="su_show_pwd")
        with c_pwd:
            pwd_type = "default" if show_pwd else "password"
            password = st.text_input("Password", type=pwd_type, placeholder="Create secure password", key="su_pwd")

        # Password Strength Indicator
        if password:
            strength_res = evaluate_password_strength(password)
            render_password_strength_bar(strength_res)

        confirm_pwd = st.text_input(
            "Confirm Password",
            type=pwd_type,
            placeholder="Re-enter password",
            key="su_pwd_conf",
        )

        terms_agreed = st.checkbox(
            "I certify that all forensic actions on this platform comply with statutory SOPs and CJIS standards.",
            key="su_terms",
        )

        if st.button("Complete Registration & Enter Platform", type="primary", use_container_width=True):
            if not full_name or not email or not password:
                st.error("Full name, email, and password are required fields.")
            elif not validate_email(email):
                st.error("Please provide a valid agency email address.")
            elif get_user_by_email(email) is not None:
                st.error(f"An investigator account with email '{email}' already exists. Please sign in.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            elif password != confirm_pwd:
                st.error("Passwords do not match. Please verify your entries.")
            elif not terms_agreed:
                st.error("You must acknowledge forensic SOP compliance to register.")
            else:
                hashed, salt = hash_password(password)
                new_user = create_user(
                    email=email,
                    full_name=full_name,
                    password_hash=hashed,
                    salt=salt,
                    badge_number=badge or None,
                    department=dept or None,
                )
                st.success(f"Account successfully registered for {new_user.full_name}.")
                login_user(new_user, remember=True)
                st.rerun()

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        nav_c1, nav_c2 = st.columns(2)
        with nav_c1:
            if st.button("Already registered? Sign in", use_container_width=True):
                st.session_state["view"] = "sign_in"
                st.rerun()
        with nav_c2:
            if st.button("← Platform Overview", use_container_width=True):
                st.session_state["view"] = "landing"
                st.rerun()


def render_forgot_password():
    """Renders password recovery workflow."""
    render_brand_header()

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(
            """
            <div style="margin-bottom:20px;">
                <h2 style="margin:0; font-size:1.6rem; color:#ffffff;">Investigator Password Recovery</h2>
                <p style="margin:4px 0 0; color:#94a3b8; font-size:0.88rem;">
                    Reset access credentials for your investigator profile.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("forgot_form"):
            email = st.text_input("Registered Email Address", placeholder="officer@agency.gov").strip()
            badge = st.text_input("Badge / Investigator ID Verification", placeholder="e.g. DET-8942").strip()
            new_pwd = st.text_input("New Secure Password", type="password", placeholder="Enter new password")
            conf_pwd = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
            submit = st.form_submit_button("Reset Password", type="primary", use_container_width=True)

        if submit:
            if not email or not new_pwd:
                st.error("Email and new password are required.")
            elif not validate_email(email):
                st.error("Invalid email address format.")
            elif len(new_pwd) < 8:
                st.error("New password must be at least 8 characters long.")
            elif new_pwd != conf_pwd:
                st.error("Passwords do not match.")
            else:
                user = get_user_by_email(email)
                if not user:
                    # Generic message to avoid email enumeration
                    st.info("If this account exists in the registry, the credentials have been updated.")
                else:
                    if user.badge_number and user.badge_number.lower() != badge.lower():
                        st.error("Badge verification failed for this registered account.")
                    else:
                        hashed, salt = hash_password(new_pwd)
                        update_user_password(user.id, hashed, salt)
                        st.success("Password reset successfully. You may now sign in with your new credentials.")
                        st.session_state["view"] = "sign_in"
                        st.rerun()

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state["view"] = "sign_in"
            st.rerun()
