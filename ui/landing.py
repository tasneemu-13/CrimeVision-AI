"""
Modern, professional landing page for CrimeVision AI.
"""
from __future__ import annotations

import streamlit as st
from ui.components import render_brand_header


def render_landing_page():
    """Renders the public landing page with platform introduction and action triggers."""
    render_brand_header(user=None)

    # Hero Section
    st.markdown(
        """
        <div class="cv-hero">
            <div class="cv-badge badge-info" style="margin-bottom:12px;">CRIMINAL JUSTICE FORENSIC INTELLIGENCE</div>
            <div class="cv-hero-title">CrimeVision AI — Multimodal Forensic Analysis Platform</div>
            <div class="cv-hero-subtitle">
                An auditable, court-ready digital forensics workbench integrating deep vision object detection, 
                speech-to-text transcript timelines, CCTV trajectory tracking, and cryptographic chain of custody.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action CTAs
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🔐 Investigator Sign In", type="primary", use_container_width=True):
                st.session_state["view"] = "sign_in"
                st.rerun()
        with btn_c2:
            if st.button("📝 Register New Account", use_container_width=True):
                st.session_state["view"] = "sign_up"
                st.rerun()

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # Feature Capabilities Grid
    st.markdown("### 🔬 Multimodal Forensic Capabilities")
    f_c1, f_c2, f_c3 = st.columns(3)

    with f_c1:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">📷 Scene Tagger</div>
                <div class="cv-feature-desc">
                    High-precision evidence detection across 5 critical classes (firearms, edged weapons, bloodstain spatter, forced entry). 
                    Automated threat scoring (Low → Critical) and prioritized investigative leads.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f_c2:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">🎙 Witness Audio</div>
                <div class="cv-feature-desc">
                    Whisper ASR transcription for emergency 112/911 dispatches and witness interviews. 
                    Automated speaker tags, verbatim transcript segments, and penal code keyword extraction.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f_c3:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">🎥 CCTV Progression</div>
                <div class="cv-feature-desc">
                    OpenCV frame sampling and frame-differencing motion analysis. 
                    Normalised suspect trajectory mapping and chronological event classification from perimeter footage.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    g_c1, g_c2, g_c3 = st.columns(3)

    with g_c1:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">🧠 Multimodal Fusion & Chat</div>
                <div class="cv-feature-desc">
                    Unified cross-modal ledger aligning image, audio, and video timelines. 
                    Strictly grounded Q&A engine that cites verified Evidence IDs and refuses speculation.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with g_c2:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">📄 Court-Ready PDF Reports</div>
                <div class="cv-feature-desc">
                    Automated generation of certified ReportLab forensic summaries with annotated plates, 
                    verbatim transcripts, trajectory charts, and investigator certification blocks.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with g_c3:
        st.markdown(
            """
            <div class="cv-feature-card">
                <div class="cv-feature-title">🧾 Cryptographic Chain of Custody</div>
                <div class="cv-feature-desc">
                    Immutable, tamper-evident audit ledger capturing intake, processing, transfers, and exports 
                    stamped with SHA-256 digests and investigator credentials.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    # Security & Compliance Section
    with st.expander("🛡️ Statutory Architecture & Data Isolation Standards", expanded=False):
        st.markdown(
            """
            - **Strict Relational Isolation:** Cases, evidence files, and analysis ledgers are indexed and scoped by authenticated user credentials. Multi-tenant cross-case leakage is strictly prevented at the database query layer.
            - **Persistent Evidence Vault:** Files are hashed upon ingestion and stored in permanent case directories rather than volatile temporary memory.
            - **Zero-Speculation Evidence Engine:** The system explicitly distinguishes observed forensic data from inferential leads, providing transparent engine accountability.
            """
        )
