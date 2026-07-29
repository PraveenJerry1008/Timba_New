import os
import base64
from typing import Literal

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag
import sarvam_client
import safety
import re

def _strip_leaked_markup(text: str) -> str:
    text = re.sub(r"</?grounding_content>", "", text)
    text = re.sub(r"(?im)^title:\s*.*$", "", text)
    return text.strip()

app = FastAPI(title="TIMBA backend")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

Language = Literal["en", "ta"]


class ChatRequest(BaseModel):
    child_name: str | None = None
    child_age: int | None = None
    message: str
    language: Language = "en"
    history: list[dict] = []  # [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str
    source_story_id: str | None = None
    source_story_title: str | None = None


class TTSRequest(BaseModel):
    text: str
    language: Language = "en"


class STTRequest(BaseModel):
    audio_base64: str
    language: Language = "ta"


SYSTEM_PROMPT_TEMPLATE = """You are TIMBA, a warm companion character for Indian children.
You must ONLY narrate and adapt the story/content given to you below in
<grounding_content> - do not invent new stories, facts, or morals beyond
what's given. You may personalize it (use the child's name if given,
adjust a couple of details for warmth), shorten or lightly rephrase it,
and add a gentle follow-up question - but the plot, characters, and values
must come from the grounding content only. Never reproduce the tags <grounding_content> or the word "Title:" 
in your reply, and never invent a different story than the one given above - speak naturally in your own voice, 
as TIMBA talking directly to the child.

{language_instruction}

Child's name: {child_name}
Child's age: {child_age}

<grounding_content>
Title: {story_title}
{story_text}
</grounding_content>
"""


def build_system_prompt(story, language: str, child_name: str | None, child_age: int | None) -> str:
    language_instruction = (
        "Respond primarily in Tamil script, naturally mixing in a few simple "
        "English words the way bilingual Indian households do."
        if language == "ta"
        else "Respond in simple, warm English."
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        language_instruction=language_instruction,
        child_name=child_name or "friend",
        child_age=child_age or "unknown",
        story_title=story["metadata"]["title"],
        story_text=story["text"],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not safety.is_input_safe(req.message):
        return ChatResponse(reply=safety.fallback_reply(req.language))

    try:
        matches = rag.retrieve(req.message, language=req.language, child_age=req.child_age, top_k=1)
    except Exception:
        matches = []

    if not matches:
        return ChatResponse(reply=safety.fallback_reply(req.language))

    story = matches[0]
    system_prompt = build_system_prompt(story, req.language, req.child_name, req.child_age)

    try:
        reply = sarvam_client.chat_completion(
            system_prompt=system_prompt,
            messages=[*req.history, {"role": "user", "content": req.message}],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sarvam chat call failed: {e}")
        
    reply = _strip_leaked_markup(reply)

    if not safety.is_output_safe(reply):
        return ChatResponse(reply=safety.fallback_reply(req.language))

    return ChatResponse(
        reply=reply,
        source_story_id=story["metadata"]["story_id"],
        source_story_title=story["metadata"]["title"],
    )

@app.post("/tts")
def tts(req: TTSRequest):
    lang_code = "ta-IN" if req.language == "ta" else "en-IN"
    try:
        audio_bytes = sarvam_client.text_to_speech(req.text, language_code=lang_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sarvam TTS call failed: {e}")
    return {"audio_base64": base64.b64encode(audio_bytes).decode()}


@app.post("/stt")
def stt(req: STTRequest):
    lang_code = "ta-IN" if req.language == "ta" else "en-IN"
    audio_bytes = base64.b64decode(req.audio_base64)
    try:
        transcript = sarvam_client.speech_to_text(audio_bytes, language_code=lang_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sarvam STT call failed: {e}")
    return {"transcript": transcript}
