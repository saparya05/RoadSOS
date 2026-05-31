"""
RoadSOS – Offline Services
Loads emergency contacts from data/offline_services.json.
Zero network calls.  All distance/direction math is pure stdlib.
"""

import json
import math
import os
from typing import List, Dict, Optional

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "offline_services.json"
)

SERVICE_TYPE_ICONS = {
    "hospital":      "🏥",
    "ambulance":     "🚑",
    "police":        "👮",
    "fire_station":  "🚒",
    "mechanic":      "🔧",
    "towing":        "🚛",
    "puncture_shop": "🔩",
    "highway_patrol":"🚔",
    "ngo":           "🤝",
    "helpline":      "📞",
    "emergency":     "🆘",
}


# ── math helpers ──────────────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """Great-circle distance in km (pure stdlib math)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlam       = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def get_bearing(lat1: float, lon1: float,
                lat2: float, lon2: float) -> str:
    """Cardinal compass direction from point 1 → point 2."""
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlam = rlon2 - rlon1
    x = math.sin(dlam) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlam)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][round(bearing / 45) % 8]


# ── data loader ───────────────────────────────────────────────────────────────

def _load() -> Dict:
    try:
        with open(_DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"india": {}, "cities": {}, "generic_services": []}
    except json.JSONDecodeError:
        return {"india": {}, "cities": {}, "generic_services": []}


# ── public API ────────────────────────────────────────────────────────────────

def _nearest_city(lat: float, lon: float, data: Dict) -> Optional[str]:
    """Return name of the city in offline data closest to (lat, lon)."""
    best_dist, best_name = float("inf"), None
    for name, info in data.get("cities", {}).items():
        d = haversine_distance(lat, lon, info["lat"], info["lon"])
        if d < best_dist:
            best_dist, best_name = d, name
    # Use city data only if within 250 km; otherwise fall back to generic
    return best_name if best_dist < 250 else None


def _enrich(svc: Dict, user_lat: float, user_lon: float,
            source: str) -> Dict:
    """Add distance, direction, icon, source and maps_url to a service dict."""
    svc_lat = svc.get("lat", user_lat)
    svc_lon = svc.get("lon", user_lon)
    icon    = SERVICE_TYPE_ICONS.get(svc.get("type", ""), "📍")

    # For national helplines (no coordinates) distance = 0 / direction = National
    if svc_lat == user_lat and svc_lon == user_lon:
        dist, direction = 0.0, "National"
    else:
        dist      = haversine_distance(user_lat, user_lon, svc_lat, svc_lon)
        direction = get_bearing(user_lat, user_lon, svc_lat, svc_lon)

    # Offline-friendly navigation: OSM deep link (works in any browser)
    if svc_lat != user_lat or svc_lon != user_lon:
        maps_url = (
            f"https://www.openstreetmap.org/directions"
            f"?engine=fossgis_osrm_car"
            f"&route={user_lat},{user_lon};{svc_lat},{svc_lon}"
        )
    else:
        maps_url = None

    return {
        **svc,
        "distance_km": dist,
        "direction":   direction,
        "icon":        icon,
        "source":      source,
        "maps_url":    maps_url,
    }


def get_offline_services(
    lat: float,
    lon: float,
    service_types: Optional[List[str]] = None,
    max_results: int = 12,
) -> List[Dict]:
    """
    Return nearby emergency services sorted by distance.
    Source: offline JSON only – zero network calls.
    """
    data     = _load()
    services: List[Dict] = []
    seen_names: set = set()

    # 1. City-specific services
    city = _nearest_city(lat, lon, data)
    if city:
        for svc in data["cities"][city]["services"]:
            if service_types and svc.get("type") not in service_types:
                continue
            enriched = _enrich(svc, lat, lon, "offline_city")
            services.append(enriched)
            seen_names.add(svc["name"].lower())

    # 2. National helplines (always included)
    for svc in data.get("india", {}).get("national_emergency", []):
        if service_types and svc.get("type") not in service_types:
            continue
        if svc["name"].lower() in seen_names:
            continue
        enriched = _enrich(dict(svc), lat, lon, "national_helpline")
        services.append(enriched)
        seen_names.add(svc["name"].lower())

    # 3. Towing + NGO supplements
    for category in ("towing_services", "ngos"):
        for svc in data.get("india", {}).get(category, []):
            if service_types and svc.get("type") not in service_types:
                continue
            if svc["name"].lower() in seen_names:
                continue
            enriched = _enrich(dict(svc), lat, lon, "national_helpline")
            services.append(enriched)
            seen_names.add(svc["name"].lower())

    # 4. Generic fallback if still sparse
    if len(services) < 4:
        for svc in data.get("generic_services", []):
            if service_types and svc.get("type") not in service_types:
                continue
            if svc["name"].lower() in seen_names:
                continue
            enriched = _enrich(dict(svc), lat, lon, "generic")
            services.append(enriched)
            seen_names.add(svc["name"].lower())

    services.sort(key=lambda s: s.get("distance_km", 0))
    return services[:max_results]


def get_national_helplines() -> List[Dict]:
    """Return all national-level emergency helplines."""
    data      = _load()
    helplines = []
    for category, items in data.get("india", {}).items():
        if not isinstance(items, list):
            continue
        for item in items:
            icon = SERVICE_TYPE_ICONS.get(item.get("type", ""), "📞")
            helplines.append({**item, "icon": icon, "category": category,
                              "distance_km": 0, "direction": "National"})
    return helplines
