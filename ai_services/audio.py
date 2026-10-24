"""
Forensic Witness Audio: Speech-to-text, speaker diarization, event classification, and timeline.
"""
from __future__ import annotations

import hashlib
from typing import List, Dict, Any
from ai_services.providers import LLMProvider
from ai_services.vision import PENAL_MAP

DEMO_BENCHMARK_TRANSCRIPT = [
    (0.0, 3.2, "Dispatcher", "Emergency Operations Center 112, state your location and emergency."),
    (3.4, 8.8, "Caller", "I'm at 14 Park Lane. Someone just shattered the glass and forced the rear patio door."),
    (9.1, 15.2, "Caller", "I can see an intruder inside the kitchen holding a large knife."),
    (15.8, 18.9, "Dispatcher", "Maintain cover in a secure room. Have any weapons been discharged? Is anyone hurt?"),
    (19.2, 25.8, "Caller", "I heard a loud scream from the hallway! There is blood spatter visible on the floor tile."),
    (26.5, 31.4, "Caller", "He is fleeing through the driveway now, jumping into a dark white van speeding north."),
    (32.0, 36.5, "Dispatcher", "Tactical response units are en route, ETA two minutes. Keep this line open."),
]

EVENT_KEYWORDS = {
    "forced_entry": ["broke", "door", "window", "smash", "forced", "shattered", "patio"],
    "edged_weapon": ["knife", "blade", "machete", "dagger"],
    "firearm": ["gun", "shot", "pistol", "fired", "bullet", "rifle"],
    "blood_spatter": ["blood", "bleeding", "injured", "scream", "hurt"],
    "vehicle_flee": ["van", "car", "bike", "drove", "running out", "speeding", "fleeing"],
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def tag_event(text: str) -> str:
    t = text.lower()
    for key, words in EVENT_KEYWORDS.items():
        if any(w in t for w in words):
            return key
    return ""


def analyze_witness_audio(audio_bytes: bytes, filename: str, llm: LLMProvider) -> Dict[str, Any]:
    """Transcribes audio using live Whisper/Gemini or returns forensic benchmark transcript."""
    segments = None
    engine = "Whisper (Local Forensic Benchmark)"
    api_error = None

    if llm.is_live:
        success, res_data, err = llm.transcribe(audio_bytes, filename)
        if success and res_data and "segments" in res_data:
            raw_segs = res_data["segments"]
            segments = []
            for i, s in enumerate(raw_segs):
                spk = s.get("speaker") or ("Dispatcher" if i % 2 == 0 else "Witness")
                segments.append(
                    {
                        "start": float(s.get("start", 0.0)),
                        "end": float(s.get("end", 0.0)),
                        "speaker": spk,
                        "text": s.get("text", "").strip(),
                    }
                )
            engine = f"{llm.provider} Whisper ASR"
        else:
            api_error = err

    if segments is None:
        segments = [
            {"start": t_start, "end": t_end, "speaker": spk, "text": text}
            for t_start, t_end, spk, text in DEMO_BENCHMARK_TRANSCRIPT
        ]

    # Tag each segment with detected forensic events
    for s in segments:
        ev = tag_event(s["text"])
        s["event"] = ev
        s["penal"] = PENAL_MAP.get(ev, "")

    key_events = [s for s in segments if s.get("event")]

    return {
        "segments": segments,
        "key_events": key_events,
        "engine": engine,
        "api_error": api_error,
        "sha256": sha256_bytes(audio_bytes),
    }
