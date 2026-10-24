"""
Case Workspace: Scoped context hosting the 6 core multimodal forensic modules.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import streamlit as st
from PIL import Image

from ai_services.providers import LLMProvider
from ai_services.vision import (
    analyze_scene_image,
    annotate_image,
    PENAL_MAP,
    sha256_bytes,
)
from ai_services.audio import analyze_witness_audio
from ai_services.video import analyze_cctv_video
from ai_services.fusion import (
    extract_events_from_analysis,
    grounded_answer,
)
from database.connection import UPLOAD_DIR
from database.db_service import (
    get_case_for_user,
    update_case,
    save_evidence,
    get_case_evidence,
    get_next_evidence_id,
    save_analysis_result,
    get_analysis_for_evidence,
    get_all_analyses_for_case,
    sync_ledger_events,
    get_case_ledger,
    log_custody_event,
    get_case_custody_log,
    save_report_record,
    get_case_reports,
    save_chat_message,
    get_case_chat_history,
    clear_case_chat_history,
)
from database.models import User
from reporting.pdf_generator import generate_forensic_pdf
from ui.components import (
    render_brand_header,
    render_status_badge,
    render_threat_badge,
)


def get_active_llm(user: User) -> LLMProvider:
    """Returns active LLM provider configured in session or environment."""
    provider_name = st.session_state.get("dash_provider", "Groq")
    key = st.session_state.get(f"{provider_name.lower()}_api_key")
    return LLMProvider(provider=provider_name, api_key=key)


def render_case_workspace(user: User):
    """Renders the case-scoped workspace for the active investigation."""
    case_id = st.session_state.get("current_case_id")
    if not case_id:
        st.session_state["view"] = "dashboard"
        st.rerun()
        return

    case = get_case_for_user(case_id, user.id)
    if not case:
        st.error(f"Unauthorized or non-existent case ID: {case_id}")
        if st.button("Return to Dashboard"):
            st.session_state["view"] = "dashboard"
            st.rerun()
        return

    render_brand_header(user)
    llm = get_active_llm(user)

    # Case Header Bar
    top_nav_c1, top_nav_c2 = st.columns([4, 1])
    with top_nav_c1:
        st.markdown(
            f"""
            <div>
                <span style="font-family:ui-monospace, monospace; font-size:0.75rem; color:#94a3b8;">
                    ACTIVE INVESTIGATION: {case.id} · {case.incident_type}
                </span>
                <h2 style="margin:2px 0 4px 0; font-size:1.6rem; color:#ffffff;">{case.title}</h2>
                <div style="font-size:0.82rem; color:#94a3b8;">
                    📍 {case.location or 'Scene location not specified'} &nbsp;|&nbsp; 
                    ⏱ {case.incident_date or 'Recent'} &nbsp;|&nbsp; Status: {render_status_badge(case.status)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_nav_c2:
        if st.button("← All Cases", use_container_width=True):
            st.session_state["view"] = "dashboard"
            st.rerun()
        # Engine status pill
        badge_color = "#00e5a8" if llm.is_live else "#f59e0b"
        st.markdown(
            f"<div style='text-align:right; margin-top:6px;'>"
            f"<span class='cv-badge' style='color:{badge_color}; border-color:{badge_color};'>"
            f"{llm.status_label}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # The 6 Forensic Module Tabs
    t1, t2, t3, t4, t5, t6 = st.tabs(
        [
            "📷 Scene Tagger",
            "🎙 Witness Audio",
            "🎥 CCTV Analysis",
            "🧠 Fusion & Chat",
            "📄 PDF Export",
            "🧾 Chain of Custody",
        ]
    )

    with t1:
        render_tab_scene_tagger(user, case, llm)
    with t2:
        render_tab_witness_audio(user, case, llm)
    with t3:
        render_tab_cctv_analysis(user, case)
    with t4:
        render_tab_fusion_chat(user, case, llm)
    with t5:
        render_tab_pdf_export(user, case)
    with t6:
        render_tab_chain_of_custody(user, case)


# ----------------------------------------------------------------------------
# 1. Scene Tagger Tab
# ----------------------------------------------------------------------------
def render_tab_scene_tagger(user: User, case: Any, llm: LLMProvider):
    st.markdown("### 📷 Crime Scene Visual Evidence Tagger")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "Upload high-resolution scene photography. Runs visual feature extraction, threat level scoring, "
        "and prioritized investigative lead derivation.</p>",
        unsafe_allow_html=True,
    )

    ev_items = [e for e in get_case_evidence(case.id, user.id) if e.evidence_type == "IMAGE"]
    active_ev = ev_items[-1] if ev_items else None

    up_file = st.file_uploader(
        "Ingest Crime Scene Photograph",
        type=["jpg", "jpeg", "png", "webp"],
        key="uploader_img",
    )

    if up_file:
        c_action1, c_action2 = st.columns([3, 1])
        with c_action1:
            st.info(f"Selected: **{up_file.name}** ({len(up_file.getvalue()) / 1024:.1f} KB)")
        with c_action2:
            if st.button("Ingest & Run Detection", type="primary", use_container_width=True):
                img_bytes = up_file.getvalue()
                digest = sha256_bytes(img_bytes)

                # Persist file
                case_dir = UPLOAD_DIR / case.id
                case_dir.mkdir(parents=True, exist_ok=True)
                file_path = case_dir / f"{digest[:12]}_{up_file.name}"
                with open(file_path, "wb") as f:
                    f.write(img_bytes)

                # Generate ID & record evidence in DB
                ev_id = get_next_evidence_id(case.id, user.id, "IMG")
                ev_record = save_evidence(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    evidence_type="IMAGE",
                    filename=up_file.name,
                    file_path=str(file_path),
                    file_size=len(img_bytes),
                    mime_type=up_file.type or "image/jpeg",
                    sha256_hash=digest,
                )

                log_custody_event(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    action=f"Photograph ingested & SHA-256 hashed ({up_file.name})",
                    investigator_name=user.full_name,
                    badge_number=user.badge_number,
                    sha256_digest=digest,
                )

                # Run Analysis
                with st.spinner("Processing computer vision detections…"):
                    analysis_data = analyze_scene_image(img_bytes, up_file.type or "image/jpeg", llm)

                # Save analysis & sync ledger events
                save_analysis_result(
                    evidence_id=ev_id,
                    case_id=case.id,
                    user_id=user.id,
                    analysis_type="IMAGE_DETECTION",
                    engine_used=analysis_data["engine"],
                    result_data=analysis_data,
                )
                ledger_events = extract_events_from_analysis(ev_id, "IMAGE", analysis_data)
                sync_ledger_events(case.id, user.id, ev_id, ledger_events)

                st.success(f"Evidence {ev_id} successfully cataloged and analyzed.")
                st.rerun()

    # Display active analyzed image if present
    if active_ev:
        analysis = get_analysis_for_evidence(active_ev.id, case.id, user.id)
        if analysis and os.path.exists(active_ev.file_path):
            with open(active_ev.file_path, "rb") as f:
                raw_bytes = f.read()

            st.markdown("---")
            c_img, c_meta = st.columns([3, 2])
            with c_img:
                annotated = annotate_image(Image.open(io.BytesIO(raw_bytes)), analysis.get("detections", []))
                st.image(
                    annotated,
                    caption=f"{active_ev.id} · Engine: {analysis.get('engine_used', 'RT-DETR')}",
                    use_container_width=True,
                )
            with c_meta:
                st.markdown(
                    f"""
                    <div class="cv-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            {render_threat_badge(analysis.get('threat', 'Low'))}
                            <span class="cv-badge badge-info">{analysis.get('scene', 'General').upper()}</span>
                        </div>
                        <div style="font-family:ui-monospace, monospace; font-size:0.75rem; color:#94a3b8; margin-top:8px;">
                            SHA-256: {active_ev.sha256_hash[:20]}…
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("**Prioritized Investigative Leads:**")
                for lead in analysis.get("leads", []):
                    st.markdown(f"- {lead}")

            # Detections table
            dets = analysis.get("detections", [])
            if dets:
                st.markdown("##### Detected Forensic Entities")
                df_dets = pd.DataFrame(
                    [
                        {
                            "Class": d.get("label"),
                            "Confidence": f"{d.get('confidence', 0):.2f}",
                            "Bounding Box": str(d.get("bbox")),
                            "Legal / Penal Note": PENAL_MAP.get(d.get("label", ""), ""),
                        }
                        for d in dets
                    ]
                )
                st.dataframe(df_dets, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# 2. Witness Audio Tab
# ----------------------------------------------------------------------------
def render_tab_witness_audio(user: User, case: Any, llm: LLMProvider):
    st.markdown("### 🎙 Witness Audio & Emergency Dispatch Timeline")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "Upload audio from emergency calls, dispatch feeds, or on-scene witness recordings. "
        "Provides verbatim speech transcription, speaker diarization tags, and penal keyword classification.</p>",
        unsafe_allow_html=True,
    )

    ev_items = [e for e in get_case_evidence(case.id, user.id) if e.evidence_type == "AUDIO"]
    active_ev = ev_items[-1] if ev_items else None

    up_audio = st.file_uploader(
        "Ingest Witness Audio Recording",
        type=["mp3", "wav", "m4a", "ogg", "webm"],
        key="uploader_aud",
    )

    if up_audio:
        c_a1, c_a2 = st.columns([3, 1])
        with c_a1:
            st.audio(up_audio)
        with c_a2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("Transcribe Audio", type="primary", use_container_width=True):
                audio_bytes = up_audio.getvalue()
                digest = sha256_bytes(audio_bytes)

                case_dir = UPLOAD_DIR / case.id
                case_dir.mkdir(parents=True, exist_ok=True)
                file_path = case_dir / f"{digest[:12]}_{up_audio.name}"
                with open(file_path, "wb") as f:
                    f.write(audio_bytes)

                ev_id = get_next_evidence_id(case.id, user.id, "AUD")
                save_evidence(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    evidence_type="AUDIO",
                    filename=up_audio.name,
                    file_path=str(file_path),
                    file_size=len(audio_bytes),
                    mime_type="audio/wav",
                    sha256_hash=digest,
                )

                log_custody_event(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    action=f"Audio ingested & transcribed ({up_audio.name})",
                    investigator_name=user.full_name,
                    badge_number=user.badge_number,
                    sha256_digest=digest,
                )

                with st.spinner("Extracting speech and aligning timestamps…"):
                    analysis_data = analyze_witness_audio(audio_bytes, up_audio.name, llm)

                save_analysis_result(
                    evidence_id=ev_id,
                    case_id=case.id,
                    user_id=user.id,
                    analysis_type="AUDIO_TRANSCRIPT",
                    engine_used=analysis_data["engine"],
                    result_data=analysis_data,
                )
                ledger_events = extract_events_from_analysis(ev_id, "AUDIO", analysis_data)
                sync_ledger_events(case.id, user.id, ev_id, ledger_events)

                st.success(f"Audio evidence {ev_id} cataloged.")
                st.rerun()

    if active_ev:
        analysis = get_analysis_for_evidence(active_ev.id, case.id, user.id)
        if analysis and os.path.exists(active_ev.file_path):
            st.markdown("---")
            st.markdown(
                f"**Evidence Reference:** `{active_ev.id}` · **Engine:** `{analysis.get('engine_used', 'Whisper')}`"
            )
            with open(active_ev.file_path, "rb") as f:
                st.audio(f.read())

            segs = analysis.get("segments", [])
            if segs:
                st.markdown("##### Verbatim Dialogue & Timestamps")
                df_segs = pd.DataFrame(segs).rename(
                    columns={
                        "start": "t_start (s)",
                        "end": "t_end (s)",
                        "speaker": "Speaker",
                        "text": "Statement",
                        "event": "Forensic Tag",
                        "penal": "Legal Note",
                    }
                )
                st.dataframe(df_segs, use_container_width=True, hide_index=True)

            key_events = analysis.get("key_events", [])
            if key_events:
                st.markdown("##### Chronological Key Events Extracted")
                for k in key_events:
                    st.markdown(
                        f"<div class='cv-card' style='padding:8px 14px; font-family:ui-monospace, monospace; font-size:0.8rem;'>"
                        f"⏱ <b>{k['start']:.1f}s</b> · <span style='color:#00e5a8;'>{k['event'].upper()}</span> — "
                        f"{k['speaker']}: {k['text']}</div>",
                        unsafe_allow_html=True,
                    )


# ----------------------------------------------------------------------------
# 3. CCTV Video Tab
# ----------------------------------------------------------------------------
def render_tab_cctv_analysis(user: User, case: Any):
    st.markdown("### 🎥 CCTV Video Analysis & Event Progression")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "Upload surveillance or dashcam footage. Samples frames via OpenCV, computes motion differential intensity, "
        "and tracks suspect movement progression.</p>",
        unsafe_allow_html=True,
    )

    ev_items = [e for e in get_case_evidence(case.id, user.id) if e.evidence_type == "VIDEO"]
    active_ev = ev_items[-1] if ev_items else None

    up_vid = st.file_uploader(
        "Ingest Surveillance Footage",
        type=["mp4", "mov", "avi", "mkv"],
        key="uploader_vid",
    )

    if up_vid:
        c_v1, c_v2 = st.columns([3, 1])
        with c_v1:
            st.video(up_vid)
        with c_v2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("Analyse CCTV Footage", type="primary", use_container_width=True):
                vid_bytes = up_vid.getvalue()
                digest = sha256_bytes(vid_bytes)

                case_dir = UPLOAD_DIR / case.id
                case_dir.mkdir(parents=True, exist_ok=True)
                file_path = case_dir / f"{digest[:12]}_{up_vid.name}"
                with open(file_path, "wb") as f:
                    f.write(vid_bytes)

                ev_id = get_next_evidence_id(case.id, user.id, "VID")
                save_evidence(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    evidence_type="VIDEO",
                    filename=up_vid.name,
                    file_path=str(file_path),
                    file_size=len(vid_bytes),
                    mime_type="video/mp4",
                    sha256_hash=digest,
                )

                log_custody_event(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    action=f"CCTV footage ingested & sampled ({up_vid.name})",
                    investigator_name=user.full_name,
                    badge_number=user.badge_number,
                    sha256_digest=digest,
                )

                with st.spinner("Sampling video frames and computing movement vectors…"):
                    analysis_data = analyze_cctv_video(vid_bytes, up_vid.name)

                save_analysis_result(
                    evidence_id=ev_id,
                    case_id=case.id,
                    user_id=user.id,
                    analysis_type="VIDEO_TRACKING",
                    engine_used=analysis_data["engine"],
                    result_data=analysis_data,
                )
                ledger_events = extract_events_from_analysis(ev_id, "VIDEO", analysis_data)
                sync_ledger_events(case.id, user.id, ev_id, ledger_events)

                st.success(f"CCTV Evidence {ev_id} analyzed.")
                st.rerun()

    if active_ev:
        analysis = get_analysis_for_evidence(active_ev.id, case.id, user.id)
        if analysis and os.path.exists(active_ev.file_path):
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Video Duration", f"{analysis.get('duration', 0)} s")
            m2.metric("Frames Sampled", analysis.get("frames_sampled", 0))
            m3.metric("Classified Events", len(analysis.get("events", [])))

            with open(active_ev.file_path, "rb") as f:
                st.video(f.read())

            track = analysis.get("track", [])
            if track:
                tdf = pd.DataFrame(track).set_index("t")
                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    st.markdown("**Suspect Trajectory Tracking (Normalised Coordinates)**")
                    st.line_chart(tdf[["suspect_x", "suspect_y"]])
                with c_t2:
                    st.markdown("**Motion Differential Intensity Profile**")
                    st.area_chart(tdf[["motion"]])

            events = analysis.get("events", [])
            if events:
                st.markdown("##### Temporal Event Progression")
                df_ev = pd.DataFrame(events).rename(
                    columns={
                        "t": "t (s)",
                        "event": "Observed Occurrence",
                        "penal": "Legal Classification",
                        "confidence": "Confidence",
                    }
                )
                if "key" in df_ev.columns:
                    df_ev = df_ev.drop(columns=["key"])
                st.dataframe(df_ev, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# 4. Fusion & Grounded Chat Tab
# ----------------------------------------------------------------------------
def render_tab_fusion_chat(user: User, case: Any, llm: LLMProvider):
    st.markdown("### 🧠 Multimodal Fusion & Grounded Evidence Chat")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "The master forensic ledger correlates visual, auditory, and surveillance evidence on a unified timeline. "
        "Interrogate case facts with guaranteed evidence-backed citations.</p>",
        unsafe_allow_html=True,
    )

    ledger = get_case_ledger(case.id, user.id)
    if not ledger:
        st.info("No evidence events recorded yet. Ingest and analyze evidence in Tabs 1–3 to populate the master ledger.")
        return

    st.markdown(f"##### Master Event Ledger ({len(ledger)} entries)")
    df_ledger = pd.DataFrame(ledger).rename(
        columns={
            "evidence_id": "Evidence ID",
            "source": "Source",
            "t_offset": "Offset (s)",
            "description": "Corroborated Event",
            "category": "Category",
            "confidence": "Conf.",
        }
    )
    if "id" in df_ledger.columns:
        df_ledger = df_ledger.drop(columns=["id"])
    st.dataframe(df_ledger, use_container_width=True, hide_index=True, height=220)

    st.markdown("---")
    st.markdown("##### Case Evidence Q&A Assistant")

    chat_history = get_case_chat_history(case.id, user.id)
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    q = st.chat_input("Ask a forensic question (e.g. 'Was a weapon visible before the suspect fled?')")
    if q:
        save_chat_message(case.id, user.id, "user", q)
        with st.spinner("Cross-referencing evidence ledger…"):
            ans = grounded_answer(case.id, user.id, q, llm)
        save_chat_message(case.id, user.id, "assistant", ans)
        st.rerun()

    if chat_history:
        if st.button("Clear Chat History", type="secondary"):
            clear_case_chat_history(case.id, user.id)
            st.rerun()


# ----------------------------------------------------------------------------
# 5. PDF Export Tab
# ----------------------------------------------------------------------------
def render_tab_pdf_export(user: User, case: Any):
    st.markdown("### 📄 Court-Ready Forensic PDF Report Export")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "Compile an official, court-ready ReportLab document complete with evidence inventories, "
        "annotated scene images, transcripts, trajectory logs, and cryptographic chain of custody.</p>",
        unsafe_allow_html=True,
    )

    evidence_items = get_case_evidence(case.id, user.id)
    analyses = get_all_analyses_for_case(case.id, user.id)
    ledger = get_case_ledger(case.id, user.id)
    custody_log = get_case_custody_log(case.id, user.id)

    with st.form("pdf_signoff_form"):
        col_inv, col_bg = st.columns(2)
        with col_inv:
            inv_name = st.text_input("Certifying Investigator", value=user.full_name)
        with col_bg:
            inv_badge = st.text_input("Badge / Certification No.", value=user.badge_number or "")

        certified = st.checkbox(
            "I certify under penalty of perjury that this report accurately reflects the automated and supervised "
            "forensic analysis of the chain-of-custody items referenced herein.",
            value=True,
        )
        gen_btn = st.form_submit_button("Generate Court-Ready PDF", type="primary", use_container_width=True)

    if gen_btn:
        if not certified:
            st.error("You must certify the forensic statement before generating an official report.")
        else:
            with st.spinner("Compiling forensic document with cryptographic checksums…"):
                # Get image bytes if image evidence exists
                img_bytes = None
                img_ev = next((e for e in evidence_items if e.evidence_type == "IMAGE"), None)
                if img_ev and os.path.exists(img_ev.file_path):
                    with open(img_ev.file_path, "rb") as f:
                        img_bytes = f.read()

                pdf_bytes, file_path, digest = generate_forensic_pdf(
                    case=case,
                    investigator_name=inv_name,
                    badge_number=inv_badge,
                    department=user.department,
                    analyses=analyses,
                    evidence_items=evidence_items,
                    ledger=ledger,
                    custody_log=custody_log,
                    image_bytes=img_bytes,
                )

                # Record in database & custody log
                filename = os.path.basename(file_path)
                save_report_record(
                    case_id=case.id,
                    user_id=user.id,
                    filename=filename,
                    file_path=file_path,
                    sha256_hash=digest,
                    investigator_name=inv_name,
                    badge_number=inv_badge,
                )
                log_custody_event(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id="REPORT",
                    action=f"Official forensic PDF generated ({filename})",
                    investigator_name=inv_name,
                    badge_number=inv_badge,
                    sha256_digest=digest,
                )

            st.success(f"Forensic Report Generated · SHA-256: `{digest[:24]}…`")
            st.download_button(
                "⬇ Download Official Court-Ready PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )

    # Previously generated reports
    reports = get_case_reports(case.id, user.id)
    if reports:
        st.markdown("##### Generated Case Reports Archive")
        for r in reports:
            if os.path.exists(r.file_path):
                with open(r.file_path, "rb") as f:
                    r_bytes = f.read()
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    st.markdown(
                        f"**{r.filename}**<br>"
                        f"<span style='font-size:0.75rem; color:#94a3b8; font-family:ui-monospace, monospace;'>"
                        f"Generated: {r.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | SHA-256: {r.sha256_hash[:20]}…</span>",
                        unsafe_allow_html=True,
                    )
                with col_r2:
                    st.download_button("Download", r_bytes, r.filename, "application/pdf", key=f"dl_{r.id}")


# ----------------------------------------------------------------------------
# 6. Chain of Custody Tab
# ----------------------------------------------------------------------------
def render_tab_chain_of_custody(user: User, case: Any):
    st.markdown("### 🧾 Official Chain of Custody & Audit Trail")
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.86rem; margin-top:-8px;'>"
        "Chronological, tamper-evident log of all digital evidence intake, analytical actions, and forensic transfers."
        "</p>",
        unsafe_allow_html=True,
    )

    custody_log = get_case_custody_log(case.id, user.id)
    if custody_log:
        df_cust = pd.DataFrame(custody_log)
        st.dataframe(df_cust, use_container_width=True, hide_index=True)

        csv_data = df_cust.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇ Export Custody Log (CSV)",
            data=csv_data,
            file_name=f"{case.id}_chain_of_custody.csv",
            mime="text/csv",
        )
    else:
        st.info("No chain-of-custody transactions recorded yet.")

    st.markdown("---")
    st.markdown("##### Record Manual Custody Action / Transfer")
    with st.form("manual_custody_form"):
        c_ev, c_act = st.columns([1, 2])
        with c_ev:
            ev_id = st.text_input("Evidence Item ID", placeholder="e.g. IMG-001 or CASE").strip()
        with c_act:
            action_desc = st.text_input("Custodial Transfer / Action Description", placeholder="e.g. Transferred drive to State Crime Lab").strip()

        submitted = st.form_submit_button("Record Custodial Event", type="primary")
        if submitted:
            if not ev_id or not action_desc:
                st.error("Both Evidence ID and Action Description are required.")
            else:
                log_custody_event(
                    case_id=case.id,
                    user_id=user.id,
                    evidence_id=ev_id,
                    action=action_desc,
                    investigator_name=user.full_name,
                    badge_number=user.badge_number,
                )
                st.success("Custodial transaction documented in permanent ledger.")
                st.rerun()
