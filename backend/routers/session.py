import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel

from backend.database import create_session, get_db
from backend.providers.base import LLMProvider, STTProvider, TTSProvider
from backend.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
from backend.services.acoustic import transcribe_and_analyze
from backend.services.chunk_examples import get_chunk_examples
from backend.services.log import handle_log_event
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
    stress_results: list[dict] | None = None
    pattern_words: list[str] | None = None
    chunk_today: str | None = None
    week_words: list[str] | None = None


class SessionStartRequest(BaseModel):
    topic: str = ""


class ChunkExamplesRequest(BaseModel):
    chunk: str
    function: str


class LogRequest(BaseModel):
    session_id: int
    event: Literal["pattern_practiced", "chunk_used", "chunk_spontaneous", "words_used"]
    pattern_id: int | None = None
    chunk: str | None = None
    transcript: str | None = None
    stress_results: list[dict] | None = None
    phoneme_errors: list[dict] | None = None
    phoneme_evaluated: int | None = None
    week_words: list[dict] | None = None


@router.post("/session/start")
async def post_session_start(
    body: SessionStartRequest, db: sqlite3.Connection = Depends(get_db)
) -> dict:
    session_id = create_session(
        db, date=date.today().isoformat(), topic=body.topic,
        transcript="", wpm=0.0, fillers=0, feedback="",
    )
    return {"session_id": session_id}


@router.post("/transcribe")
async def post_transcribe(
    audio: UploadFile = File(...),
    target_words: str = Form(""),
    pattern_name: str = Form(""),
    stt: STTProvider = Depends(get_stt_provider),
) -> dict:
    audio_bytes = await audio.read()
    words = [w.strip() for w in target_words.split(",") if w.strip()]
    transcript = await transcribe_and_analyze(
        audio_bytes, provider=stt, target_words=words, pattern_name=pattern_name or None
    )
    return {
        "text": transcript.text,
        "wpm": transcript.wpm,
        "fillers": transcript.fillers,
        "words": transcript.words,
        "stress_results": transcript.stress_results,
        "phoneme_errors": transcript.phoneme_errors,
        "phoneme_evaluated": transcript.phoneme_evaluated,
        "pattern_errors": transcript.pattern_errors,
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
        stress_results=body.stress_results,
        pattern_words=body.pattern_words,
        chunk_today=body.chunk_today,
        week_words=body.week_words,
    )
    return {"reply": reply, "session_id": session_id}


@router.post("/chunk-examples")
async def post_chunk_examples(
    body: ChunkExamplesRequest, llm: LLMProvider = Depends(get_llm_provider)
) -> dict:
    return await get_chunk_examples(llm, chunk=body.chunk, function=body.function)


@router.post("/log")
async def post_log(body: LogRequest, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return handle_log_event(
        db, session_id=body.session_id, event=body.event,
        pattern_id=body.pattern_id, chunk=body.chunk, transcript=body.transcript,
        stress_results=body.stress_results,
        phoneme_errors=body.phoneme_errors,
        phoneme_evaluated=body.phoneme_evaluated,
        week_words=body.week_words,
    )
