"""
AI Model Providers (Groq & Gemini) with robust error reporting and transparency.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional, Dict, Any, Tuple
import requests


class LLMProvider:
    def __init__(self, provider: str = "Groq", api_key: Optional[str] = None):
        self.provider = provider
        env_key = os.getenv("GROQ_API_KEY" if provider == "Groq" else "GEMINI_API_KEY", "")
        self.key = (api_key or env_key or "").strip()

    @property
    def is_live(self) -> bool:
        return bool(self.key)

    @property
    def status_label(self) -> str:
        if self.is_live:
            masked = f"{self.key[:4]}...{self.key[-4:]}" if len(self.key) > 8 else "***"
            return f"LIVE ({self.provider} - {masked})"
        return "LOCAL FORENSIC BASELINE (No API Key)"

    def chat(self, system: str, user: str, json_mode: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Executes chat completion.
        Returns: (success: bool, content_or_error: Optional[str], error_message: Optional[str])
        """
        if not self.is_live:
            return False, None, "No API key configured for live LLM."

        try:
            if self.provider == "Groq":
                body: Dict[str, Any] = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.1,
                }
                if json_mode:
                    body["response_format"] = {"type": "json_object"}

                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    json=body,
                    timeout=45,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return True, content, None
            else:  # Gemini
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-2.0-flash:generateContent?key={self.key}"
                )
                body = {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        **({"responseMimeType": "application/json"} if json_mode else {}),
                    },
                }
                resp = requests.post(url, json=body, timeout=45)
                resp.raise_for_status()
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                return True, content, None

        except requests.exceptions.RequestException as e:
            err_msg = f"{self.provider} API request failed: {e}"
            return False, None, err_msg
        except Exception as e:
            return False, None, f"Unexpected error during {self.provider} processing: {str(e)}"

    def vision_json(self, prompt: str, img_bytes: bytes, mime: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Executes vision JSON extraction.
        Returns: (success: bool, result_dict: Optional[dict], error_message: Optional[str])
        """
        if not self.is_live:
            return False, None, "No API key configured for multimodal vision."

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        try:
            if self.provider == "Groq":
                body = {
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    json=body,
                    timeout=60,
                )
                resp.raise_for_status()
                parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
                return True, parsed, None
            else:  # Gemini
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-2.0-flash:generateContent?key={self.key}"
                )
                body = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {"mime_type": mime, "data": b64}},
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
                }
                resp = requests.post(url, json=body, timeout=60)
                resp.raise_for_status()
                parsed = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                return True, parsed, None

        except requests.exceptions.RequestException as e:
            return False, None, f"{self.provider} vision API call failed: {e}"
        except json.JSONDecodeError as e:
            return False, None, f"{self.provider} returned invalid JSON: {e}"
        except Exception as e:
            return False, None, f"Vision analysis error: {str(e)}"

    def transcribe(self, audio_bytes: bytes, filename: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Executes audio transcription.
        Returns: (success: bool, result_dict: Optional[dict], error_message: Optional[str])
        """
        if not self.is_live:
            return False, None, "No API key configured for speech transcription."

        try:
            if self.provider == "Groq":
                resp = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    files={"file": (filename, audio_bytes)},
                    data={"model": "whisper-large-v3", "response_format": "verbose_json"},
                    timeout=90,
                )
                resp.raise_for_status()
                data = resp.json()
                segments = [
                    {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()}
                    for s in data.get("segments", [])
                ]
                return True, {"segments": segments}, None
            else:  # Gemini
                mime = "audio/mpeg" if filename.lower().endswith(".mp3") else "audio/wav"
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-2.0-flash:generateContent?key={self.key}"
                )
                prompt = (
                    'Transcribe this forensic audio. Return strict JSON: '
                    '{"segments":[{"start":0.0,"end":3.5,"speaker":"Caller|Dispatcher|Witness","text":"..."}]}'
                )
                body = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": mime,
                                        "data": base64.b64encode(audio_bytes).decode("utf-8"),
                                    }
                                },
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
                }
                resp = requests.post(url, json=body, timeout=90)
                resp.raise_for_status()
                parsed = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                return True, parsed, None

        except requests.exceptions.RequestException as e:
            return False, None, f"{self.provider} transcription API error: {e}"
        except Exception as e:
            return False, None, f"Audio transcription error: {str(e)}"
