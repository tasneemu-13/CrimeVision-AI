"""
Reusable UI components for CrimeVision AI.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
import streamlit as st


def render_brand_header(user: Optional[Any] = None) -> None:
    """Renders the top branding and user profile indicator bar."""
    if user:
        dept_str = f" · {user.department}" if user.department else ""
        badge_str = f" [Badge: {user.badge_number}]" if user.badge_number else ""
        user_info = (
            f"<div style='text-align: right;'>"
            f"<span style='font-size:0.85rem; color:#f1f5f9; font-weight:600;'>{user.full_name}</span>"
            f"<span style='font-size:0.75rem; color:#94a3b8;'>{badge_str}{dept_str}</span>"
            f"</div>"
        )
    else:
        user_info = (
            "<div style='text-align: right; font-size:0.78rem; color:#94a3b8; font-family:ui-monospace, monospace;'>"
            "SECURE FORENSIC INTELLIGENCE</div>"
        )

    html = f"""
    <div class="cv-brand-bar">
        <div class="cv-brand-title">
            <span>🔍 CrimeVision AI</span>
            <span class="cv-brand-tag">v2.0 Forensic OS</span>
        </div>
        {user_info}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_stat_card(label: str, value: Any, desc: Optional[str] = None) -> None:
    """Renders a consistent, clean forensic metric card."""
    desc_html = f"<div class='cv-stat-desc'>{desc}</div>" if desc else ""
    html = f"""
    <div class="cv-stat-card">
        <div class="cv-stat-label">{label}</div>
        <div class="cv-stat-val">{value}</div>
        {desc_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_threat_badge(threat: str) -> str:
    """Returns HTML for threat level badge."""
    cls_map = {
        "low": "badge-low",
        "medium": "badge-medium",
        "high": "badge-high",
        "critical": "badge-critical",
    }
    c = cls_map.get(threat.lower(), "badge-neutral")
    return f"<span class='cv-badge {c}'>THREAT: {threat.upper()}</span>"


def render_status_badge(status: str) -> str:
    """Returns HTML for case status badge."""
    cls_map = {
        "open": "badge-info",
        "in progress": "badge-medium",
        "under review": "badge-neutral",
        "closed": "badge-low",
    }
    c = cls_map.get(status.lower(), "badge-neutral")
    return f"<span class='cv-badge {c}'>{status.upper()}</span>"


def render_password_strength_bar(eval_res: Dict[str, Any]) -> None:
    """Renders a password strength meter with checklist."""
    color = eval_res["color"]
    percent = eval_res["percent"]
    label = eval_res["label"]

    st.markdown(
        f"""
        <div style="margin: 6px 0 10px 0;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px;">
                <span style="color:#94a3b8;">Strength Assessment:</span>
                <span style="color:{color}; font-weight:600;">{label}</span>
            </div>
            <div style="background:#1e2d42; height:5px; border-radius:3px; overflow:hidden;">
                <div style="background:{color}; width:{percent}%; height:100%; transition:width 0.3s ease;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    checks = list(eval_res["checks"].items())
    for i, (req, passed) in enumerate(checks):
        col = cols[i % 2]
        icon = "✓" if passed else "○"
        c = "#00e5a8" if passed else "#64748b"
        col.markdown(f"<span style='font-size:0.73rem; color:{c};'>{icon} {req}</span>", unsafe_allow_html=True)
