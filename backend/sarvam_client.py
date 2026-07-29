"""
Thin wrapper around Sarvam AI's APIs (chat completion, TTS, STT).

IMPORTANT: verify exact endpoint paths, request/response shapes, and model
names against https://docs.sarvam.ai before deploying — Sarvam's API
surface has changed as they've shipped new models (Sarvam-M, Sarvam-30B,
Sarvam-105B). This file was written from published pricing/docs pages but
was NOT executed against the live API in this environment (no network
access here), so treat it as a strong starting point, not a tested client.
"""

import os
import base64
import requests

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_BASE_URL = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")

CHAT_MODEL = "sarvam-105b"  # swap to "sarvam-30b" for stronger reasoning, higher cost


def _headers():
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set - copy .env.example to .env and fill it in.")
    return {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json",
    }


def chat_completion(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 400,
    reasoning_effort: str | None = "low",
) -> str:
    payload = {
        "model": CHAT_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "reasoning_effort": reasoning_effort,
    }
    resp = requests.post(
        f"{SARVAM_BASE_URL}/v1/chat/completions", headers=_headers(), json=payload, timeout=30
    )
    if not resp.ok:
        raise RuntimeError(f"Sarvam API error {resp.status_code}: {resp.text}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise RuntimeError(f"Sarvam returned empty content: {data}")
    return content
    
    
def text_to_speech(text: str, language_code: str = "en-IN", speaker: str = "meera") -> bytes:
    """Returns raw audio bytes (WAV). language_code examples: 'ta-IN', 'en-IN'."""
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": speaker,
    }
    resp = requests.post(
        f"{SARVAM_BASE_URL}/text-to-speech", headers=_headers(), json=payload, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    # Sarvam returns base64-encoded audio in `audios[0]`
    audio_b64 = data["audios"][0]
    return base64.b64decode(audio_b64)


def speech_to_text(audio_bytes: bytes, language_code: str = "ta-IN") -> str:
    """audio_bytes should be a WAV file's raw bytes."""
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"language_code": language_code, "model": "saarika:v2"}
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    resp = requests.post(
        f"{SARVAM_BASE_URL}/speech-to-text", headers=headers, files=files, data=data, timeout=30
    )
    resp.raise_for_status()
    return resp.json()["transcript"]
