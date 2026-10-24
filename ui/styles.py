"""
Design System CSS for CrimeVision AI: Dark Graphite, Deep Navy, Precision Teal & Cyan.
"""
from __future__ import annotations

import streamlit as st

FORENSIC_CSS = """
<style>
/* CSS Variables */
:root {
    --cv-bg: #0b0f14;
    --cv-surface: #101723;
    --cv-panel: #141f2d;
    --cv-card: #182638;
    --cv-border: #1e2d42;
    --cv-border-light: #283a54;
    --cv-primary: #00e5a8;
    --cv-cyan: #0ea5e9;
    --cv-text: #e2e8f0;
    --cv-text-muted: #94a3b8;
    --cv-text-dim: #64748b;
    --cv-warn: #f59e0b;
    --cv-crit: #ef4444;
    --cv-success: #10b981;
}

/* Base Body and App Background */
.stApp {
    background-color: var(--cv-bg);
    color: var(--cv-text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Forensic Brand Bar */
.cv-brand-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--cv-border);
    padding: 12px 18px;
    background: var(--cv-surface);
    margin-bottom: 20px;
    border-radius: 8px;
}
.cv-brand-title {
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 8px;
}
.cv-brand-tag {
    font-size: 0.72rem;
    text-transform: uppercase;
    font-family: ui-monospace, monospace;
    background: rgba(0, 229, 168, 0.12);
    color: var(--cv-primary);
    border: 1px solid rgba(0, 229, 168, 0.3);
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
}

/* Metric / Stat Cards */
.cv-stat-card {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: border-color 0.15s ease;
}
.cv-stat-card:hover {
    border-color: var(--cv-border-light);
}
.cv-stat-label {
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--cv-text-muted);
    margin-bottom: 6px;
}
.cv-stat-val {
    font-size: 1.85rem;
    font-weight: 700;
    font-family: ui-monospace, monospace;
    color: #ffffff;
    line-height: 1.1;
}
.cv-stat-desc {
    font-size: 0.76rem;
    color: var(--cv-text-dim);
    margin-top: 5px;
}

/* General Forensic Card */
.cv-card {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 16px;
}

/* Forensic Badges */
.cv-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.74rem;
    font-family: ui-monospace, monospace;
    font-weight: 600;
    border: 1px solid transparent;
}
.badge-low {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border-color: rgba(16, 185, 129, 0.3);
}
.badge-medium {
    background: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
    border-color: rgba(245, 158, 11, 0.3);
}
.badge-high {
    background: rgba(249, 115, 22, 0.12);
    color: #fb923c;
    border-color: rgba(249, 115, 22, 0.3);
}
.badge-critical {
    background: rgba(239, 68, 68, 0.12);
    color: #f87171;
    border-color: rgba(239, 68, 68, 0.3);
}
.badge-info {
    background: rgba(14, 165, 233, 0.12);
    color: #38bdf8;
    border-color: rgba(14, 165, 233, 0.3);
}
.badge-neutral {
    background: rgba(148, 163, 184, 0.12);
    color: #cbd5e1;
    border-color: rgba(148, 163, 184, 0.25);
}

/* Landing Page Hero */
.cv-hero {
    border: 1px solid var(--cv-border);
    background: linear-gradient(180deg, #101924 0%, #0c1219 100%);
    border-radius: 12px;
    padding: 44px 32px;
    text-align: center;
    margin-bottom: 30px;
}
.cv-hero-title {
    font-size: 2.25rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
}
.cv-hero-subtitle {
    font-size: 1.05rem;
    color: var(--cv-text-muted);
    max-width: 680px;
    margin: 0 auto 24px auto;
    line-height: 1.55;
}

/* Feature Grid Cards */
.cv-feature-card {
    background: var(--cv-surface);
    border: 1px solid var(--cv-border);
    border-radius: 8px;
    padding: 20px;
    height: 100%;
}
.cv-feature-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.cv-feature-desc {
    font-size: 0.85rem;
    color: var(--cv-text-muted);
    line-height: 1.45;
}

/* Tab Styling Overrides */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid var(--cv-border);
    padding-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.88rem;
    font-weight: 500;
    padding: 8px 16px;
    border-radius: 6px;
    color: var(--cv-text-muted);
    background: transparent;
    border: 1px solid transparent;
}
.stTabs [aria-selected="true"] {
    background: var(--cv-surface) !important;
    border-color: var(--cv-border) !important;
    color: var(--cv-primary) !important;
    font-weight: 600;
}

/* Form & Input Adjustments */
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] select {
    background-color: var(--cv-surface);
    border: 1px solid var(--cv-border);
    color: var(--cv-text);
    border-radius: 6px;
}

/* Table styling */
.stDataFrame {
    border: 1px solid var(--cv-border);
    border-radius: 6px;
}
</style>
"""


def apply_styles():
    """Inject the design system CSS into the current Streamlit page."""
    st.markdown(FORENSIC_CSS, unsafe_allow_html=True)
