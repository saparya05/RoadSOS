import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class EmergencyClassification:
    category: str
    confidence: float
    keywords_matched: List[str]
    services_needed: List[str]
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL


EMERGENCY_PATTERNS = {
    "accident": {
        "keywords": [
            "accident", "crash", "collision", "hit", "smash", "wreck",
            "banged", "rammed", "fell", "overturned", "rolled over",
            "met with accident", "car accident", "road accident",
            "vehicle accident", "truck hit", "bike fell", "skid"
        ],
        "services": ["ambulance", "hospital", "police", "mechanic", "towing"],
        "priority": "CRITICAL"
    },
    "injury": {
        "keywords": [
            "injured", "hurt", "bleeding", "blood", "broken", "fracture",
            "unconscious", "fainted", "pain", "wound", "cut", "bruise",
            "head injury", "chest pain", "heart attack", "stroke",
            "can't breathe", "breathing problem", "paralyzed", "cannot move"
        ],
        "services": ["ambulance", "hospital"],
        "priority": "CRITICAL"
    },
    "fire": {
        "keywords": [
            "fire", "burning", "flame", "smoke", "catching fire", "on fire",
            "explosion", "blast", "fuel leak", "petrol leak", "gas leak",
            "car on fire", "engine fire", "burnt", "exploded"
        ],
        "services": ["fire_station", "ambulance", "police"],
        "priority": "CRITICAL"
    },
    "breakdown": {
        "keywords": [
            "breakdown", "broke down", "not starting", "engine stopped",
            "won't start", "dead battery", "battery dead", "tyre flat",
            "tire flat", "puncture", "flat tyre", "fuel empty", "out of fuel",
            "no petrol", "overheating", "engine failure", "stalled",
            "car stopped", "vehicle stopped", "not moving", "gear problem",
            "brake fail", "brake failure", "no brakes", "steering problem"
        ],
        "services": ["mechanic", "towing", "puncture_shop"],
        "priority": "MEDIUM"
    },
    "theft": {
        "keywords": [
            "theft", "stolen", "robbed", "robbing", "rob", "robbery",
            "hijack", "carjacking", "snatched", "snatching", "pickpocket",
            "bag snatched", "phone stolen", "car stolen", "bike stolen",
            "looted", "loot", "mugged", "mugging", "attacked", "attack",
            "threatened", "threatening", "knife", "gun", "weapon",
            "dacoity", "dacoit", "chain snatching"
        ],
        "services": ["police", "highway_patrol"],
        "priority": "HIGH"
    },
    "medical": {
        "keywords": [
            "heart attack", "stroke", "seizure", "epilepsy", "diabetic",
            "insulin", "allergic", "anaphylaxis", "overdose", "poisoning",
            "pregnancy", "labor", "delivery", "miscarriage", "asthma",
            "inhaler", "oxygen", "baby", "child"
        ],
        "services": ["ambulance", "hospital"],
        "priority": "CRITICAL"
    },
    "flood_natural": {
        "keywords": [
            "flood", "flooded", "waterlogged", "submerged", "storm",
            "cyclone", "earthquake", "landslide", "tree fallen", "road blocked",
            "road closed", "highway blocked", "bridge broken"
        ],
        "services": ["police", "highway_patrol", "ambulance"],
        "priority": "HIGH"
    }
}

SEVERITY_KEYWORDS = {
    "critical": ["dying", "dead", "not breathing", "unconscious", "severe bleeding", "critical", "emergency"],
    "high": ["urgent", "serious", "bad", "major", "heavy"],
    "medium": ["moderate", "some", "minor issue"],
    "low": ["small", "minor", "slight", "little"]
}

FOLLOW_UP_QUESTIONS = {
    "accident": [
        "Are there any injuries? How many people are affected?",
        "Is the vehicle blocking traffic or in a dangerous position?",
        "Do you need an ambulance, police, or towing service?"
    ],
    "injury": [
        "Is the person conscious and breathing?",
        "Is there severe bleeding?",
        "Can you safely move the injured person?"
    ],
    "fire": [
        "Is everyone safely away from the vehicle?",
        "Has the fire spread to nearby structures or vehicles?",
        "Are there any injuries?"
    ],
    "breakdown": [
        "What type of vehicle is it (car/bike/truck)?",
        "What seems to be the problem (flat tyre, engine, battery)?",
        "Are you in a safe location or blocking traffic?"
    ],
    "theft": [
        "Are you physically safe right now?",
        "Can you describe the perpetrators or vehicle?",
        "What was stolen?"
    ],
    "medical": [
        "Is the patient conscious and breathing?",
        "Do they have any known medical conditions?",
        "Do you know their blood group?"
    ]
}


def classify_emergency(text: str) -> EmergencyClassification:
    """Classify the emergency type from user input text."""
    text_lower = text.lower()
    
    scores = {}
    matched_keywords_map = {}
    
    for category, data in EMERGENCY_PATTERNS.items():
        matched = []
        for keyword in data["keywords"]:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        if matched:
            scores[category] = len(matched)
            matched_keywords_map[category] = matched
    
    if not scores:
        return EmergencyClassification(
            category="unknown",
            confidence=0.0,
            keywords_matched=[],
            services_needed=["police", "ambulance", "hospital"],
            priority="HIGH"
        )
    
    best_category = max(scores, key=scores.get)
    total_keywords = len(EMERGENCY_PATTERNS[best_category]["keywords"])
    confidence = min(scores[best_category] / max(total_keywords * 0.3, 1), 1.0)
    
    priority = EMERGENCY_PATTERNS[best_category]["priority"]
    for sev_level, sev_words in SEVERITY_KEYWORDS.items():
        for word in sev_words:
            if word in text_lower:
                if sev_level == "critical":
                    priority = "CRITICAL"
                break
    
    return EmergencyClassification(
        category=best_category,
        confidence=round(confidence, 2),
        keywords_matched=matched_keywords_map[best_category],
        services_needed=EMERGENCY_PATTERNS[best_category]["services"],
        priority=priority
    )


def get_follow_up_questions(category: str) -> List[str]:
    """Return follow-up questions for the given emergency category."""
    return FOLLOW_UP_QUESTIONS.get(category, [
        "Can you describe what happened?",
        "Are you in a safe location?",
        "Do you need immediate medical assistance?"
    ])


def get_emergency_instructions(category: str, priority: str) -> List[str]:
    """Return immediate action instructions for the emergency category."""
    instructions = {
        "accident": [
            "🚨 Move to a safe area away from traffic immediately",
            "🔴 Turn on hazard lights if safe to do so",
            "📞 Call 112 for emergency services",
            "🚑 Check for injuries before moving anyone",
            "📸 Document the scene for insurance if safe",
            "⚠️ Do NOT move seriously injured persons unless in immediate danger"
        ],
        "injury": [
            "🚨 Call ambulance immediately - Dial 108",
            "🩹 Apply pressure to any bleeding wounds",
            "⚠️ Do NOT move the person if spinal injury suspected",
            "🌬️ Check breathing and pulse",
            "🔥 Keep the person warm and calm",
            "💬 Talk to them to keep them conscious"
        ],
        "fire": [
            "🔥 GET EVERYONE AWAY FROM THE VEHICLE IMMEDIATELY",
            "📞 Call Fire Brigade - Dial 101",
            "🚗 Move at least 100 meters away",
            "⛽ Do NOT attempt to retrieve belongings",
            "💨 Stay upwind from the smoke",
            "🚒 Call ambulance if anyone is injured - Dial 108"
        ],
        "breakdown": [
            "⚠️ Move vehicle to the shoulder/safe area",
            "🔴 Turn on hazard lights immediately",
            "🔺 Place warning triangles behind vehicle",
            "🚗 Stay inside vehicle if on highway",
            "📞 Call towing service or mechanic",
            "💡 Do NOT attempt repairs on a busy highway"
        ],
        "theft": [
            "🏃 Get to a safe, public location immediately",
            "📞 Call Police - Dial 100",
            "📝 Note down any details (description, vehicle number)",
            "📷 Check nearby cameras for evidence",
            "🏦 Block your cards/accounts if stolen",
            "👥 Stay with other people if possible"
        ],
        "medical": [
            "🚑 Call ambulance immediately - Dial 108",
            "💊 Do NOT give any medication without knowing the person's condition",
            "🌬️ Ensure airway is clear and person is breathing",
            "❤️ Begin CPR if trained and no pulse detected",
            "🏥 Note any medications the person takes",
            "🩺 Inform paramedics of any known conditions"
        ],
        "flood_natural": [
            "🌊 Do NOT drive through flooded roads",
            "📞 Call NDRF - Dial 1078 for disasters",
            "📡 Listen to official emergency broadcasts",
            "🔼 Move to higher ground immediately",
            "⚡ Stay away from electrical poles/lines",
            "📞 Inform local authorities of your position"
        ],
        "unknown": [
            "📞 Call National Emergency - Dial 112",
            "🔴 Turn on hazard lights if in vehicle",
            "🏃 Move to a safe location",
            "📍 Note your GPS location to share with responders",
            "👥 Stay calm and with other people if possible"
        ]
    }
    return instructions.get(category, instructions["unknown"])


def format_emergency_response(
    classification: EmergencyClassification,
    services: list,
    user_text: str
) -> str:
    """Format a complete AI response for the emergency."""
    
    category_labels = {
        "accident": "🚗 Road Accident Detected",
        "injury": "🩺 Medical Emergency Detected",
        "fire": "🔥 Fire Emergency Detected",
        "breakdown": "🔧 Vehicle Breakdown Detected",
        "theft": "🚨 Theft/Crime Emergency Detected",
        "medical": "💉 Medical Emergency Detected",
        "flood_natural": "🌊 Natural Disaster/Road Hazard Detected",
        "unknown": "⚠️ Emergency Detected"
    }
    
    label = category_labels.get(classification.category, "⚠️ Emergency Detected")
    priority_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
    p_emoji = priority_emoji.get(classification.priority, "🟡")
    
    response_parts = [
        f"**{label}**",
        f"{p_emoji} Priority: **{classification.priority}**",
        "",
        "**📋 Immediate Actions:**"
    ]
    
    instructions = get_emergency_instructions(classification.category, classification.priority)
    for instruction in instructions:
        response_parts.append(f"• {instruction}")
    
    if services:
        response_parts.append("")
        response_parts.append("**📍 Nearest Emergency Services:**")
        for i, svc in enumerate(services[:5], 1):
            dist = svc.get("distance_km", "?")
            dist_str = f"{dist:.1f} km" if isinstance(dist, float) else str(dist)
            phone = svc.get("phone", "N/A")
            name = svc.get("name", "Unknown")
            direction = svc.get("direction", "")
            dir_str = f" ({direction})" if direction else ""
            response_parts.append(f"{i}. **{name}** — {dist_str}{dir_str} | 📞 {phone}")
    
    follow_ups = get_follow_up_questions(classification.category)
    if follow_ups:
        response_parts.append("")
        response_parts.append("**❓ Quick Assessment:**")
        response_parts.append(follow_ups[0])
    
    response_parts.append("")
    response_parts.append("---")
    response_parts.append("💬 *Type your response or ask for more help. I'm here to assist.*")
    
    return "\n".join(response_parts)
