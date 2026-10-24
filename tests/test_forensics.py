"""
Unit tests for multimodal forensic processing, ledger fusion, and grounded chat.
"""
import io
import uuid
from PIL import Image
import pytest

from ai_services.providers import LLMProvider
from ai_services.vision import (
    analyze_scene_image,
    score_scene,
    build_leads,
    annotate_image,
    sha256_bytes,
)
from ai_services.audio import analyze_witness_audio, tag_event
from ai_services.video import analyze_cctv_video
from ai_services.fusion import (
    extract_events_from_analysis,
    grounded_answer,
    retrieve_relevant_events,
)
from database.connection import init_db
from database.db_service import (
    create_user,
    create_case,
    sync_ledger_events,
    get_case_ledger,
)
from auth.security import hash_password


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def make_test_image_bytes():
    img = Image.new("RGB", (320, 240), color=(30, 40, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_scene_tagger_and_scoring():
    img_bytes = make_test_image_bytes()
    llm = LLMProvider(provider="Groq", api_key="")  # Unconfigured = test deterministic baseline

    res = analyze_scene_image(img_bytes, "image/jpeg", llm)
    assert "detections" in res
    assert len(res["detections"]) > 0
    assert res["threat"] in ["Low", "Medium", "High", "Critical"]
    assert res["scene"] in ["Burglary", "Homicide", "Vandalism", "Assault"]
    assert len(res["leads"]) > 0
    assert res["sha256"] == sha256_bytes(img_bytes)

    # Test annotation
    base_img = Image.open(io.BytesIO(img_bytes))
    annotated = annotate_image(base_img, res["detections"])
    assert annotated.size == base_img.size


def test_witness_audio_and_event_tagging():
    assert tag_event("He forced open the rear door with a crowbar") == "forced_entry"
    assert tag_event("Subject has a concealed knife") == "edged_weapon"
    assert tag_event("Someone was screaming, lots of blood") == "blood_spatter"
    assert tag_event("The white van fled down the avenue") == "vehicle_flee"
    assert tag_event("Just asking for directions") == ""

    llm = LLMProvider(provider="Groq", api_key="")
    audio_res = analyze_witness_audio(b"FAKE_AUDIO_SAMPLE_DATA", "call.wav", llm)
    assert len(audio_res["segments"]) > 0
    assert len(audio_res["key_events"]) > 0


def test_cctv_video_analysis():
    video_res = analyze_cctv_video(b"FAKE_CCTV_SAMPLE_STREAM", "cctv_cam_01.mp4")
    assert video_res["duration"] > 0
    assert len(video_res["track"]) > 0
    assert len(video_res["events"]) > 0
    assert any(e["key"] == "forced_entry" for e in video_res["events"])


def test_multimodal_ledger_and_grounded_qa():
    h, s = hash_password("ValidPassword!1")
    user = create_user(
        email=f"tester_{uuid.uuid4().hex[:6]}@lab.org",
        full_name="Forensic Analyst Gibbs",
        password_hash=h,
        salt=s,
    )
    case = create_case(user_id=user.id, title="14 Park Lane Burglary")

    img_bytes = make_test_image_bytes()
    llm = LLMProvider(provider="Groq", api_key="")
    img_res = analyze_scene_image(img_bytes, "image/jpeg", llm)
    audio_res = analyze_witness_audio(b"SAMPLE", "audio.wav", llm)
    video_res = analyze_cctv_video(b"SAMPLE", "video.mp4")

    # Ingest ledger events
    img_events = extract_events_from_analysis("IMG-001", "IMAGE", img_res)
    sync_ledger_events(case.id, user.id, "IMG-001", img_events)

    aud_events = extract_events_from_analysis("AUD-001", "AUDIO", audio_res)
    sync_ledger_events(case.id, user.id, "AUD-001", aud_events)

    vid_events = extract_events_from_analysis("VID-001", "VIDEO", video_res)
    sync_ledger_events(case.id, user.id, "VID-001", vid_events)

    ledger = get_case_ledger(case.id, user.id)
    assert len(ledger) == len(img_events) + len(aud_events) + len(vid_events)

    # Test Grounded QA
    ans = grounded_answer(case.id, user.id, "Was a weapon visible before the suspect fled?", llm)
    assert "weapon" in ans.lower() or "forensic" in ans.lower()
    assert "[" in ans  # Must cite evidence
