"""
RoadSOS – FastAPI Backend  (fully offline)
Run from project root:
    uvicorn backend.main:app --reload
"""

import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from backend.chatbot import handle_chat, get_quick_response, clear_conversation
from backend.service_finder import get_all_emergency_services, find_services
from backend.offline_services import get_national_helplines, get_offline_services
from backend.voice_input import transcribe_audio_bytes, is_voice_available, get_available_engine
from backend.emergency_classifier import classify_emergency
from backend.database import (
    save_chat_turn, log_emergency,
    get_chat_history, get_all_sessions_with_last_message,
    delete_session as db_delete_session,
    get_emergency_stats, upsert_session,
)

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RoadSOS API",
    description="AI Emergency Assistant – fully offline capable",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    text:       str   = Field(..., min_length=1)
    lat:        float = Field(default=28.6139)
    lon:        float = Field(default=77.2090)
    session_id: Optional[str] = None


class ServiceSearchRequest(BaseModel):
    lat:           float
    lon:           float
    service_types: Optional[List[str]] = None
    radius_km:     float = 50.0


class QuickEmergencyRequest(BaseModel):
    emergency_type: str
    lat: float
    lon: float


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service":  "RoadSOS API",
        "version":  "3.0.0",
        "status":   "operational",
        "offline":  True,
        "voice_engine": get_available_engine(),
    }


@app.get("/health")
def health():
    return {
        "status":        "ok",
        "voice_engine":  get_available_engine(),
        "voice_offline": not get_available_engine() in ("google_online", "none"),
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """Main chat endpoint – persists every turn to SQLite."""
    session_id = request.session_id or str(uuid.uuid4())
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        result = handle_chat(
            user_text=text,
            lat=request.lat,
            lon=request.lon,
            session_id=session_id,
        )

        emergency_type = result.get("emergency_category")
        priority       = result.get("priority")
        services       = result.get("services", [])

        # Persist to DB
        save_chat_turn(
            session_id=session_id,
            user_text=text,
            ai_response=result.get("ai_message", ""),
            emergency_type=emergency_type,
            priority=priority,
            confidence=result.get("confidence"),
            lat=request.lat,
            lon=request.lon,
            services=services,
        )

        if emergency_type and emergency_type not in ("unknown", None):
            log_emergency(
                session_id=session_id,
                emergency_type=emergency_type,
                priority=priority or "MEDIUM",
                user_text=text,
                lat=request.lat,
                lon=request.lon,
                services_count=len(services),
            )

        result["session_id"] = session_id
        result["is_online"]  = False   # always offline
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {e}")


@app.post("/services")
def search_services(req: ServiceSearchRequest):
    try:
        return find_services(
            req.lat, req.lon,
            service_types=req.service_types,
            radius_km=req.radius_km,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/all")
def all_services(lat: float = 28.6139, lon: float = 77.2090):
    return get_all_emergency_services(lat, lon)


@app.get("/helplines")
def helplines():
    return {"helplines": get_national_helplines()}


@app.post("/classify")
def classify(req: ChatRequest):
    c = classify_emergency(req.text)
    return {
        "category":         c.category,
        "confidence":       c.confidence,
        "priority":         c.priority,
        "services_needed":  c.services_needed,
        "keywords_matched": c.keywords_matched,
    }


@app.post("/voice")
async def voice_transcribe(audio: UploadFile = File(...)):
    """
    Transcribe uploaded audio.
    Uses offline engine (Whisper / Vosk / Sphinx) when available.
    Falls back to Google only as last resort.
    """
    if not is_voice_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "No STT engine found. "
                "Install whisper: pip install openai-whisper  "
                "or SpeechRecognition: pip install SpeechRecognition"
            ),
        )
    try:
        audio_bytes = await audio.read()
        # Detect format from filename
        fname  = audio.filename or "audio.webm"
        suffix = fname.rsplit(".", 1)[-1].lower() if "." in fname else "webm"
        text, engine = transcribe_audio_bytes(audio_bytes, audio_format=suffix)
        if not text:
            raise HTTPException(status_code=422, detail="Could not transcribe audio")
        return {"text": text, "engine": engine, "offline": engine != "google_online"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quick-emergency")
def quick_emergency(req: QuickEmergencyRequest):
    return get_quick_response(req.emergency_type, req.lat, req.lon)


# ── Session / history ─────────────────────────────────────────────────────────

@app.get("/sessions")
def list_sessions():
    return {"sessions": get_all_sessions_with_last_message()}


@app.get("/sessions/{session_id}/history")
def session_history(session_id: str):
    return {"history": get_chat_history(session_id)}


@app.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    clear_conversation(session_id)
    db_delete_session(session_id)
    return {"message": "Session deleted", "session_id": session_id}


@app.get("/stats")
def stats():
    return get_emergency_stats()


@app.get("/offline-services")
def offline_services_endpoint(lat: float = 28.6139, lon: float = 77.2090):
    return {"services": get_offline_services(lat, lon), "source": "offline"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
