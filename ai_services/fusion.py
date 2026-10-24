"""
Multimodal Fusion Ledger & Grounded Evidence Chat with verification and strict citation.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple
from ai_services.providers import LLMProvider
from database.db_service import get_case_ledger, sync_ledger_events


def extract_events_from_analysis(
    evidence_id: str,
    evidence_type: str,
    analysis_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Converts raw analysis output into structured ledger events."""
    events = []
    if evidence_type == "IMAGE":
        detections = analysis_data.get("detections", [])
        for i, d in enumerate(detections):
            label = d.get("label", "unknown")
            conf = d.get("confidence", 1.0)
            bbox = d.get("bbox", [])
            events.append(
                {
                    "id": f"{evidence_id}.D{i+1}",
                    "source": "IMAGE",
                    "t_offset": 0.0,
                    "description": f"Visual detection: {label} (confidence {conf:.2f}, bbox {bbox})",
                    "category": label,
                    "confidence": conf,
                }
            )
    elif evidence_type == "AUDIO":
        segments = analysis_data.get("segments", [])
        for i, s in enumerate(segments):
            events.append(
                {
                    "id": f"{evidence_id}.S{i+1}",
                    "source": "AUDIO",
                    "t_offset": float(s.get("start", 0.0)),
                    "description": f"{s.get('speaker', 'Unknown')}: {s.get('text', '')}",
                    "category": s.get("event", ""),
                    "confidence": 1.0,
                }
            )
    elif evidence_type == "VIDEO":
        cctv_events = analysis_data.get("events", [])
        for i, e in enumerate(cctv_events):
            events.append(
                {
                    "id": f"{evidence_id}.E{i+1}",
                    "source": "VIDEO",
                    "t_offset": float(e.get("t", 0.0)),
                    "description": e.get("event", ""),
                    "category": e.get("key", ""),
                    "confidence": float(e.get("confidence", 1.0)),
                }
            )
    return events


def retrieve_relevant_events(ledger: List[Dict[str, Any]], query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Rank ledger events using lexical and domain synonym overlap."""
    stop_words = {"the", "a", "an", "is", "was", "did", "were", "what", "how", "when", "where", "any"}
    tokens = set(re.findall(r"[a-z0-9]+", query.lower())) - stop_words

    synonym_map = {
        "weapon": {"knife", "firearm", "edged", "gun", "blade", "weapon", "machete"},
        "fled": {"exits", "departs", "running", "van", "flee", "speeding", "fleeing", "escape"},
        "suspect": {"s1", "intruder", "subject", "man", "person", "suspect"},
        "entry": {"door", "window", "forced", "smash", "broke", "patio", "lock"},
        "hurt": {"blood", "scream", "altercation", "assault", "injured", "knife"},
    }

    expanded_tokens = set(tokens)
    for t in list(tokens):
        expanded_tokens |= synonym_map.get(t, set())

    scored = []
    for ev in ledger:
        text = f"{ev.get('description', '')} {ev.get('category', '')}".lower()
        words = set(re.findall(r"[a-z0-9]+", text))
        matches = len(expanded_tokens & words)
        if matches > 0:
            scored.append((matches, ev))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]


def grounded_answer(
    case_id: str,
    user_id: str,
    question: str,
    llm: LLMProvider,
) -> str:
    """Provides a verified forensic answer strictly grounded in the case ledger."""
    ledger = get_case_ledger(case_id, user_id)
    if not ledger:
        return (
            "⚠️ **No evidence records in ledger.** Please upload and analyze visual, audio, "
            "or CCTV evidence in Tabs 1–3 before querying."
        )

    matched_events = retrieve_relevant_events(ledger, question) or ledger[:12]
    context_lines = [
        f"[{e['evidence_id']}] ({e['source']}, t={e['t_offset']:.1f}s) {e['description']}"
        for e in matched_events
    ]
    context_str = "\n".join(context_lines)

    if llm.is_live:
        system_prompt = (
            "You are a Senior Digital Forensic Investigator. Answer the investigator's question "
            "using ONLY the provided forensic evidence lines below.\n"
            "RULES:\n"
            "1. Every factual claim MUST cite its Evidence ID in brackets (e.g. [IMG-001.D1], [AUD-001.S3]).\n"
            "2. Distinguish direct observations from inferences.\n"
            "3. If the evidence lines do not contain sufficient facts to answer, respond exactly: "
            "'Insufficient evidence in the ledger to answer.'\n"
            "4. NEVER speculate or assume facts not documented in the evidence."
        )
        user_prompt = f"FORENSIC EVIDENCE LEDGER:\n{context_str}\n\nINVESTIGATOR QUESTION: {question}"

        success, content, err = llm.chat(system_prompt, user_prompt)
        if success and content:
            # Verify citations
            cited = set(re.findall(r"\[([A-Z0-9_-]+(?:\.[A-Z0-9]+)?)\]", content))
            valid = {e["evidence_id"] for e in matched_events}
            if cited and not (cited <= valid):
                return (
                    "⚠️ *Automated citation check flagged unsupported claims.* "
                    "Falling back to verified extractive summary:\n\n"
                    + extractive_answer(matched_events, question)
                )
            return content

    # Deterministic extractive fallback
    return extractive_answer(matched_events, question)


def extractive_answer(ctx: List[Dict[str, Any]], q: str) -> str:
    """Deterministic, verified extractive synthesis based on the retrieved evidence."""
    ql = q.lower()
    chronological = sorted(ctx, key=lambda e: (e["t_offset"], e["source"]))

    # Temporal correlation: weapon before flight
    if "before" in ql and ("fled" in ql or "flee" in ql or "flight" in ql):
        flight_events = [
            e for e in chronological
            if any(w in e["description"].lower() for w in ("departs", "running", "van", "exits", "flee"))
        ]
        weapon_events = [
            e for e in chronological
            if any(w in e["description"].lower() for w in ("knife", "firearm", "edged", "weapon", "gun"))
        ]

        if flight_events and weapon_events:
            first_flight = min(e["t_offset"] for e in flight_events)
            prior_weapons = [w for w in weapon_events if w["t_offset"] <= first_flight]
            if prior_weapons:
                cites = ", ".join(f"[{w['evidence_id']}]" for w in prior_weapons)
                return (
                    f"**Forensic Corroboration:** Yes. A weapon is documented at or before the suspect fled "
                    f"(first flight logged at t={first_flight:.1f}s). Supporting evidence: {cites}."
                )
            else:
                return f"**Forensic Corroboration:** No weapon event was recorded prior to the initial flight event (t={first_flight:.1f}s)."

    # General extractive listing
    lines = [f"- **t={e['t_offset']:.1f}s** [{e['source']}]: {e['description']} `[{e['evidence_id']}]`" for e in chronological]
    return (
        "**Relevant Corroborating Evidence:**\n\n"
        + "\n".join(lines)
        + "\n\n*(Extractive forensic synthesis; zero speculative hallucination)*"
    )
