"""
Investigator Dashboard: Live metrics, search/filtering, case management, and activity feed.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import datetime

from auth.session import logout_user
from database.db_service import (
    get_dashboard_metrics,
    get_user_cases,
    create_case,
    delete_case,
    get_case_evidence,
    log_custody_event,
)
from database.models import User
from ui.components import (
    render_brand_header,
    render_stat_card,
    render_status_badge,
    render_threat_badge,
)


def render_dashboard(user: User):
    """Renders the main dashboard for the authenticated investigator."""
    render_brand_header(user)

    # Top Navigation and Investigator Profile Bar
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown(
            f"""
            <div>
                <h2 style="margin:0; font-size:1.6rem; color:#ffffff;">Forensic Operations Dashboard</h2>
                <p style="margin:3px 0 0; color:#94a3b8; font-size:0.86rem;">
                    Investigator: <b>{user.full_name}</b> &nbsp;|&nbsp; Agency: <b>{user.department or 'Unassigned'}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_c2:
        btn_prof_col, btn_out_col = st.columns(2)
        with btn_prof_col:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state["show_settings"] = not st.session_state.get("show_settings", False)
        with btn_out_col:
            if st.button("Sign Out", type="secondary", use_container_width=True):
                logout_user()

    # Settings Drawer / Expander
    if st.session_state.get("show_settings"):
        with st.expander("🛠️ Investigator Terminal & AI Configuration", expanded=True):
            st.markdown("#### AI Model Provider Credentials")
            prov = st.radio("Active Multimodal Provider", ["Groq", "Gemini"], horizontal=True, key="dash_provider")
            current_key = st.session_state.get(f"{prov.lower()}_api_key", "")
            new_key = st.text_input(
                f"{prov} API Key",
                value=current_key,
                type="password",
                placeholder="Leave blank for local deterministic forensic baselines",
                key="dash_key_input",
            )
            if st.button("Save API Configuration"):
                st.session_state[f"{prov.lower()}_api_key"] = new_key.strip()
                st.success(f"{prov} configuration updated.")
            st.markdown("---")
            st.markdown(f"**Investigator ID:** `{user.id}` &nbsp;|&nbsp; **Registered Email:** `{user.email}`")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Calculate real persistent metrics from database
    metrics = get_dashboard_metrics(user.id)

    # 4 Metric Cards Row
    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
    with m_c1:
        render_stat_card("Total Cases", metrics["total_cases"], "Stored in persistent vault")
    with m_c2:
        render_stat_card("Active Investigations", metrics["active_investigations"], "Open & In-Progress cases")
    with m_c3:
        render_stat_card("Evidence Ingested", metrics["total_evidence"], "Photos, Audio & CCTV items")
    with m_c4:
        render_stat_card("Reports Generated", metrics["total_reports"], "Court-ready PDF exports")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Action Bar: Create Case, Search, Filter & Sort
    action_col1, action_col2 = st.columns([1, 2])
    with action_col1:
        if st.button("➕ Create New Case", type="primary", use_container_width=True):
            st.session_state["show_create_modal"] = True

    # Case Creation Modal / Section
    if st.session_state.get("show_create_modal"):
        with st.expander("📁 Register New Investigation Case", expanded=True):
            with st.form("new_case_form"):
                st.markdown("##### Case Registration Details")
                c_title = st.text_input("Case Title", placeholder="e.g. 14 Park Lane Residential Burglary").strip()
                c_desc = st.text_area("Incident Overview / Summary", placeholder="Brief description of incident circumstances...").strip()

                col_t, col_s = st.columns(2)
                with col_t:
                    c_type = st.selectbox(
                        "Incident Category",
                        ["Burglary", "Homicide", "Assault", "Vandalism", "Armed Robbery", "Vehicle Theft", "Other"],
                    )
                with col_s:
                    c_status = st.selectbox("Initial Status", ["Open", "In Progress", "Under Review"])

                col_loc, col_dt = st.columns(2)
                with col_loc:
                    c_loc = st.text_input("Incident Location / Address", placeholder="e.g. 14 Park Lane, Sector 4").strip()
                with col_dt:
                    c_dt = st.text_input("Incident Date & Time", value=datetime.now().strftime("%Y-%m-%d %H:%M")).strip()

                c_submit = st.form_submit_button("Initialize Case Workspace", type="primary", use_container_width=True)

            if c_submit:
                if not c_title:
                    st.error("Case title is required.")
                else:
                    new_case = create_case(
                        user_id=user.id,
                        title=c_title,
                        description=c_desc,
                        incident_type=c_type,
                        status=c_status,
                        location=c_loc,
                        incident_date=c_dt,
                    )
                    log_custody_event(
                        case_id=new_case.id,
                        user_id=user.id,
                        evidence_id="CASE",
                        action=f"Case initialized: {new_case.title}",
                        investigator_name=user.full_name,
                        badge_number=user.badge_number,
                    )
                    st.session_state["show_create_modal"] = False
                    st.session_state["current_case_id"] = new_case.id
                    st.session_state["view"] = "workspace"
                    st.rerun()

            if st.button("Cancel Registration"):
                st.session_state["show_create_modal"] = False
                st.rerun()

    # Search and Filter Toolbar
    f_c1, f_c2, f_c3 = st.columns([2, 1, 1])
    with f_c1:
        search_query = st.text_input("Search cases", placeholder="Filter by Title, Case ID, Location, or Category...", label_visibility="collapsed")
    with f_c2:
        status_filter = st.selectbox("Status", ["All", "Open", "In Progress", "Under Review", "Closed"], label_visibility="collapsed")
    with f_c3:
        sort_by = st.selectbox("Sort By", ["Newest", "Oldest", "Title"], label_visibility="collapsed")

    # Fetch filtered cases from database
    cases = get_user_cases(
        user_id=user.id,
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by.lower(),
    )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Main Content Area: Cases List + Recent Activity Feed
    content_c1, content_c2 = st.columns([3, 2])

    with content_c1:
        st.markdown(f"### 📂 Investigation Cases ({len(cases)})")
        if not cases:
            st.markdown(
                """
                <div class="cv-card" style="text-align:center; padding:36px 20px;">
                    <div style="font-size:2rem; margin-bottom:8px;">📁</div>
                    <div style="font-weight:600; color:#ffffff; font-size:1.05rem;">No Cases Found</div>
                    <div style="color:#94a3b8; font-size:0.85rem; margin-top:4px; max-width:380px; margin:0 auto 16px auto;">
                        You have no active investigations matching the current criteria. 
                        Click <b>Create New Case</b> above to register your first investigation.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Optional Benchmark Case Seeder for effortless grading / exploration
            st.markdown(
                "<div style='text-align:center; color:#64748b; font-size:0.8rem; margin-top:8px;'>"
                "Want to explore with sample multimodal evidence?</div>",
                unsafe_allow_html=True,
            )
            if st.button("⚡ Initialize Forensic Benchmark Case (Demo Data)", use_container_width=True):
                sample_case = create_case(
                    user_id=user.id,
                    title="14 Park Lane Armed Residential Burglary",
                    description="Multimodal investigation into residential forced entry, armed intruder, and vehicle flight.",
                    incident_type="Burglary",
                    status="In Progress",
                    location="14 Park Lane, Sector 4",
                    incident_date="2026-10-23 21:15",
                )
                log_custody_event(
                    case_id=sample_case.id,
                    user_id=user.id,
                    evidence_id="CASE",
                    action="Benchmark investigation initialized",
                    investigator_name=user.full_name,
                    badge_number=user.badge_number,
                )
                st.session_state["current_case_id"] = sample_case.id
                st.session_state["view"] = "workspace"
                st.rerun()

        else:
            for c in cases:
                ev_items = get_case_evidence(c.id, user.id)
                with st.container():
                    st.markdown(
                        f"""
                        <div class="cv-card" style="margin-bottom:12px; padding:16px 18px;">
                            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                <div>
                                    <span style="font-family:ui-monospace, monospace; font-size:0.75rem; color:#94a3b8;">
                                        {c.id} · {c.incident_type}
                                    </span>
                                    <h4 style="margin:2px 0 6px 0; color:#ffffff; font-size:1.1rem;">{c.title}</h4>
                                    <div style="font-size:0.8rem; color:#94a3b8;">
                                        📍 {c.location or 'Location not specified'} &nbsp;|&nbsp; ⏱ {c.incident_date or 'Recent'}
                                    </div>
                                </div>
                                <div>
                                    {render_status_badge(c.status)}
                                </div>
                            </div>
                            <div style="margin-top:10px; font-size:0.82rem; color:#64748b;">
                                📦 {len(ev_items)} Evidence Items &nbsp;|&nbsp; Updated: {c.updated_at.strftime('%Y-%m-%d %H:%M')}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    action_c1, action_c2 = st.columns([4, 1])
                    with action_c1:
                        if st.button(f"🔍 Open Case Workspace ({c.id})", key=f"open_{c.id}", use_container_width=True):
                            st.session_state["current_case_id"] = c.id
                            st.session_state["view"] = "workspace"
                            st.rerun()
                    with action_c2:
                        if st.button("🗑️", key=f"del_{c.id}", help="Delete case"):
                            delete_case(c.id, user.id)
                            st.rerun()

    with content_c2:
        st.markdown("### 📋 Recent Forensic Audit Trail")
        recent_activity = metrics["recent_activity"]
        if not recent_activity:
            st.markdown(
                """
                <div class="cv-card" style="text-align:center; padding:24px 16px; color:#94a3b8; font-size:0.84rem;">
                    No custody events recorded yet.<br>All evidence intake and analysis actions will be logged here.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for act in recent_activity:
                ts_str = act.timestamp_utc.strftime("%H:%M:%S UTC")
                st.markdown(
                    f"""
                    <div class="cv-card" style="padding:10px 14px; margin-bottom:8px; font-family:ui-monospace, monospace; font-size:0.78rem;">
                        <div style="display:flex; justify-content:space-between; color:#94a3b8; margin-bottom:3px;">
                            <span style="color:#00e5a8; font-weight:600;">[{act.evidence_id}]</span>
                            <span>{ts_str}</span>
                        </div>
                        <div style="color:#ffffff;">{act.action}</div>
                        <div style="color:#64748b; font-size:0.72rem; margin-top:2px;">
                            By: {act.investigator_name} &nbsp;|&nbsp; Case: {act.case_id}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
