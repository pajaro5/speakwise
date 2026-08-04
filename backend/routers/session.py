import sqlite3

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel

from backend.database import get_db
from backend.providers.base import LLMProvider, STTProvider, TTSProvider
from backend.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
from backend.services.acoustic import transcribe_and_analyze
from backend.services.tutor import get_tutor_reply

router = APIRouter(prefix="/api", tags=["session"])


class SpeakRequest(BaseModel):
    text: str
    voice: str = "default"


class TutorRequest(BaseModel):
    text: str
    history: list[dict] = []
    session_id: int | None = None
    topic: str = ""
    wpm: float = 0.0
    fillers: int = 0


@router.post("/transcribe")
async def post_transcribe(
    audio: UploadFile = File(...),
    stt: STTProvider = Depends(get_stt_provider),
) -> dict:
    audio_bytes = await audio.read()
    transcript = await transcribe_and_analyze(audio_bytes, provider=stt)
    return {
        "text": transcript.text,
        "wpm": transcript.wpm,
        "fillers": transcript.fillers,
        "words": transcript.words,
    }


@router.post("/speak")
async def post_speak(
    body: SpeakRequest, tts: TTSProvider = Depends(get_tts_provider)
) -> Response:
    audio_bytes = await tts.synthesize(body.text, voice=body.voice)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/tutor")
async def post_tutor(
    body: TutorRequest,
    db: sqlite3.Connection = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> dict:
    reply, session_id = await get_tutor_reply(
        db, llm,
        text=body.text, history=body.history, session_id=body.session_id,
        topic=body.topic, wpm=body.wpm, fillers=body.fillers,
    )
    return {"reply": reply, "session_id": session_id}
