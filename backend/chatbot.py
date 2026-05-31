import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from backend.emergency_classifier import (
    classify_emergency,
    get_follow_up_questions,
    get_emergency_instructions,
    format_emergency_response,
    EmergencyClassification,
)
from backend.service_finder import find_services


# Data classes

@dataclass
class ChatMessage:
    role: str                               # user
    content: str
    timestamp: str = ""
    emergency_category: Optional[str] = None


@dataclass
class ConversationState:
    messages: List[ChatMessage] = field(default_factory=list)
    current_emergency: Optional[EmergencyClassification] = None
    last_lat: float = 0.0
    last_lon: float = 0.0
    follow_up_index: int = 0
    services_shown: bool = False
    turn_count: int = 0


_conversations: Dict[str, ConversationState] = {}


def get_or_create_conversation(session_id: str) -> ConversationState:
    if session_id not in _conversations:
        _conversations[session_id] = ConversationState()
    return _conversations[session_id]


def clear_conversation(session_id: str) -> None:
    _conversations.pop(session_id, None)


# Constants / lookup tables

_GREETINGS = {
    "hi", "hello", "hey", "start", "help", "sos",
    "helo", "namaste", "namaskar", "hii", "hlo",
}

_GREETING_RESPONSE = """👋 **Welcome to RoadSOS — AI Emergency Assistant**

I'm here to help you 24 × 7 during any road emergency.

🚗 I detect: Accidents · Injuries · Fire · Breakdown · Theft · Medical crises
📍 I find:   Hospitals · Police · Fire stations · Mechanics · Tow trucks

**Just describe what's happening** and I'll guide you immediately.

*Try: "My car met with an accident" · "Tyre puncture on highway" · "Engine overheating"*"""

_CATEGORY_OPENERS = {
    "accident":    "🚗 **Road accident detected.** Locating emergency services near you.",
    "injury":      "🩺 **Medical emergency detected.** Finding ambulance and hospital.",
    "fire":        "🔥 **Fire emergency detected.** Alerting fire brigade and rescue.",
    "breakdown":   "🔧 **Vehicle breakdown detected.** Finding mechanics and tow trucks.",
    "theft":       "🚨 **Security emergency detected.** Locating nearest police station.",
    "medical":     "💉 **Medical emergency detected.** Dispatching ambulance information.",
    "flood_natural": "🌊 **Road hazard detected.** Contacting highway patrol.",
    "unknown":     "⚠️ **Emergency received.** Locating all nearby services.",
}

_PRIORITY_BADGE = {
    "CRITICAL": "🔴 **Priority: CRITICAL — Call 112 immediately**",
    "HIGH":     "🟠 **Priority: HIGH — Act fast**",
    "MEDIUM":   "🟡 **Priority: MODERATE**",
    "LOW":      "🟢 **Priority: LOW — Help is nearby**",
}

_IMMEDIATE_STEPS = {
    "accident": [
        "Move to the road shoulder — away from moving traffic.",
        "Switch on hazard lights immediately.",
        "Check all passengers for injuries before anything else.",
        "Do **not** move anyone who may have a spinal/neck injury.",
        "Call **112** — National Emergency.",
    ],
    "injury": [
        "Keep the injured person still and calm.",
        "Apply firm pressure to any bleeding wounds with a cloth.",
        "Do **not** give water, food, or medication to an unconscious person.",
        "Call **108** — Ambulance.",
    ],
    "fire": [
        "**GET EVERYONE AWAY from the vehicle immediately.**",
        "Move at least 100 metres upwind from the fire.",
        "Do **not** go back inside the vehicle for any belongings.",
        "Call **101** — Fire Brigade.",
        "Call **108** — Ambulance if anyone is injured.",
    ],
    "breakdown": [
        "Pull over to the left shoulder and switch on hazard lights.",
        "Place warning triangles 50 m behind the vehicle if available.",
        "Stay **inside** the vehicle if you are on a busy highway.",
        "Call the mechanic or tow service listed below.",
    ],
    "theft": [
        "Move to a safe, well-lit, public area immediately.",
        "Do **not** resist or confront the perpetrators.",
        "Note any details — vehicle plate, clothing, direction of escape.",
        "Call **100** — Police Control Room.",
    ],
    "medical": [
        "Keep the person lying down in a comfortable position.",
        "Check for breathing and pulse every 30 seconds.",
        "Do not administer medication unless you know the prescription.",
        "Call **108** — Ambulance.",
    ],
    "flood_natural": [
        "Do **not** drive through flooded or waterlogged roads.",
        "Move to higher ground immediately.",
        "Stay away from electricity poles and fallen wires.",
        "Call **1078** — National Disaster Management.",
    ],
    "unknown": [
        "Move to a safe location away from hazards.",
        "Call **112** — National Emergency.",
        "Describe your situation clearly to the operator.",
    ],
}


def _format_service_line(svc: Dict, idx: int) -> str:
    dist = svc.get("distance_km", "?")
    dist_str = f"{dist:.1f} km" if isinstance(dist, (int, float)) else str(dist)
    direction = svc.get("direction", "")
    icon  = svc.get("icon", "📍")
    name  = svc.get("name", "Service")
    phone = svc.get("phone", "N/A")
    return f"{idx}. {icon} **{name}** — {dist_str} {direction} | 📞 {phone}"


def _build_response(
    classification: EmergencyClassification,
    services: List[Dict],
    is_online: bool,
) -> str:
    cat      = classification.category
    priority = classification.priority
    parts: List[str] = []

    parts.append(_CATEGORY_OPENERS.get(cat, _CATEGORY_OPENERS["unknown"]))
    parts.append("")
    parts.append(_PRIORITY_BADGE.get(priority, _PRIORITY_BADGE["MEDIUM"]))
    parts.append("")

    steps = _IMMEDIATE_STEPS.get(cat, _IMMEDIATE_STEPS["unknown"])
    parts.append("**📋 Do this right now:**")
    for i, step in enumerate(steps, 1):
        parts.append(f"{i}. {step}")
    parts.append("")

    if services:
        parts.append("**📍 Nearest help found:**")
        for i, svc in enumerate(services[:5], 1):
            parts.append(_format_service_line(svc, i))
        parts.append("")

    follow_ups = get_follow_up_questions(cat)
    if follow_ups:
        parts.append(f"❓ {follow_ups[0]}")
        parts.append("")

    if not is_online:
        parts.append(
            "⚠️ *Offline mode — showing saved emergency contacts. "
            "Connect to internet for live nearby services.*"
        )
        parts.append("")

    parts.append("---")
    parts.append("💬 *Reply with updates or ask for more help. I'm here.*")
    return "\n".join(parts)


def _build_followup_response(
    state: ConversationState,
    services: List[Dict],
    is_online: bool,
) -> str:
    cat = state.current_emergency.category if state.current_emergency else "unknown"
    follow_ups = get_follow_up_questions(cat)
    idx = state.follow_up_index

    parts: List[str] = []
    if idx < len(follow_ups):
        parts.append(f"Understood. {follow_ups[idx]}")
        state.follow_up_index += 1
    else:
        parts.append("I'm monitoring your situation. Here are the closest services:")

    parts.append("")
    if services:
        parts.append("**📍 Nearest services:**")
        for i, svc in enumerate(services[:4], 1):
            parts.append(_format_service_line(svc, i))

    if not is_online:
        parts.append("")
        parts.append("⚠️ *Using offline contact data.*")

    return "\n".join(parts)


# Public API

def handle_chat(
    user_text: str,
    lat: float,
    lon: float,
    session_id: str = "default",
) -> Dict:
    state = get_or_create_conversation(session_id)
    state.turn_count += 1
    state.last_lat = lat
    state.last_lon = lon

    cleaned = user_text.strip()

    # Greeting
    if cleaned.lower() in _GREETINGS and state.turn_count == 1:
        state.messages.append(ChatMessage(role="user",      content=cleaned))
        state.messages.append(ChatMessage(role="assistant", content=_GREETING_RESPONSE))
        return {
            "ai_message": _GREETING_RESPONSE,
            "services": [], "emergency_category": None,
            "priority": None, "confidence": None,
            "is_online": False, "show_map": False,
        }

    classification = classify_emergency(cleaned)
    new_emergency  = classification.category != "unknown"

    if new_emergency:
        state.current_emergency = classification
        state.follow_up_index   = 0
        state.services_shown    = False
    elif state.current_emergency is None:
        state.current_emergency = classification

    service_types = (
        state.current_emergency.services_needed
        if state.current_emergency else None
    )
    result    = find_services(lat, lon, service_types=service_types,
                              radius_km=7.0, max_results=8)
    services  = result.get("services", [])
    is_online = result.get("is_online", False)

    if new_emergency:
        ai_msg = _build_response(classification, services, is_online)
        state.services_shown = True
    else:
        ai_msg = _build_followup_response(state, services, is_online)

    state.messages.append(ChatMessage(role="user",      content=cleaned))
    state.messages.append(ChatMessage(
        role="assistant", content=ai_msg,
        emergency_category=classification.category,
    ))

    return {
        "ai_message":         ai_msg,
        "services":           services,
        "emergency_category": classification.category,
        "priority":           classification.priority,
        "confidence":         classification.confidence,
        "is_online":          is_online,
        "show_map":           True,
        "instructions":       _IMMEDIATE_STEPS.get(
            classification.category, _IMMEDIATE_STEPS["unknown"]
        ),
    }


def get_quick_response(emergency_type: str, lat: float, lon: float) -> Dict:
    _quick_text = {
        "accident":  "I met with an accident on the road",
        "breakdown": "My vehicle broke down and won't start",
        "medical":   "Someone needs urgent medical help",
        "fire":      "There is a fire emergency",
        "theft":     "I am being robbed or attacked",
        "puncture":  "I have a flat tyre on the highway",
    }
    text = _quick_text.get(emergency_type, f"Emergency: {emergency_type}")
    return handle_chat(text, lat, lon, session_id=f"quick_{emergency_type}")


def generate_greeting() -> str:
    return _GREETING_RESPONSE
