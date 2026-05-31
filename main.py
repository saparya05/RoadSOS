"""
RoadSOS FastAPI Backend
Main API entry point.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

from backend.chatbot import handle_chat, get_quick_response, generate_greeting, clear_conversation
from backend.service_finder import get_all_emergency_services, find_services
from backend.offline_services import get_national_helplines, get_offline_services
from backend.voice_input import transcribe_audio_bytes, is_voice_available, get_available_voice_method
from backend.emergency_classifier import classify_emergency


app = FastAPI(
    title="RoadSOS API",
    description="AI Emergency Assistant for Road Emergencies",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    text: str = Field(..., description="User message text", min_length=1)
    lat: float = Field(default=28.6139, description="User latitude")
    lon: float = Field(default=77.2090, description="User longitude")
    session_id: Optional[str] = Field(default=None, description="Session identifier")


class ServiceSearchRequest(BaseModel):
    lat: float
    lon: float
    service_types: Optional[List[str]] = None
    radius_km: float = 5.0


class QuickEmergencyRequest(BaseModel):
    emergency_type: str
    lat: float
    lon: float


@app.get("/")
def root():
    return {
        "service": "RoadSOS API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": ["/chat", "/services", "/helplines", "/classify", "/voice", "/quick-emergency"]
    }


@app.get("/health")
def health():
    return {"status": "ok", "voice_available": is_voice_available()}


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Main chat endpoint. Accepts emergency text + coordinates.
    Returns AI message and nearby services.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        result = handle_chat(
            user_text=request.text,
            lat=request.lat,
            lon=request.lon,
            session_id=session_id
        )
        result["session_id"] = session_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")


@app.post("/services")
def search_services(request: ServiceSearchRequest):
    """Find nearby emergency services."""
    try:
        result = find_services(
            lat=request.lat,
            lon=request.lon,
            service_types=request.service_types,
            radius_km=request.radius_km
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/services/all")
def all_services(lat: float = 28.6139, lon: float = 77.2090):
    """Get all emergency services near a location."""
    return get_all_emergency_services(lat, lon)


@app.get("/helplines")
def helplines():
    """Get national emergency helplines."""
    return {"helplines": get_national_helplines()}


@app.post("/classify")
def classify(request: ChatRequest):
    """Classify emergency type from text."""
    classification = classify_emergency(request.text)
    return {
        "category": classification.category,
        "confidence": classification.confidence,
        "priority": classification.priority,
        "services_needed": classification.services_needed,
        "keywords_matched": classification.keywords_matched
    }


@app.post("/voice")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcribe audio to text."""
    if not is_voice_available():
        raise HTTPException(
            status_code=503,
            detail=f"Voice transcription unavailable. Install: pip install SpeechRecognition"
        )
    
    try:
        audio_bytes = await audio.read()
        text, method = transcribe_audio_bytes(audio_bytes)
        
        if not text:
            raise HTTPException(status_code=422, detail="Could not transcribe audio")
        
        return {"text": text, "method": method}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quick-emergency")
def quick_emergency(request: QuickEmergencyRequest):
    """Handle quick emergency button presses."""
    result = get_quick_response(request.emergency_type, request.lat, request.lon)
    return result


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Clear conversation history for a session."""
    clear_conversation(session_id)
    return {"message": "Session cleared", "session_id": session_id}


@app.get("/offline-services")
def offline_services_endpoint(lat: float = 28.6139, lon: float = 77.2090):
    """Get offline emergency services."""
    services = get_offline_services(lat, lon)
    return {"services": services, "source": "offline"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
