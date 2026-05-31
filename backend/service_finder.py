"""
RoadSOS – Service Finder  (fully offline)

Never makes any network calls.
All data comes from data/offline_services.json.
"""

from typing import List, Dict, Optional
from backend.offline_services import (
    get_offline_services,
    get_national_helplines,
    haversine_distance,
    get_bearing,
    SERVICE_TYPE_ICONS,
)

ALL_SERVICE_TYPES = [
    "hospital", "ambulance", "police", "fire_station",
    "mechanic", "towing", "puncture_shop", "highway_patrol",
]


def find_services(
    lat: float,
    lon: float,
    service_types: Optional[List[str]] = None,
    radius_km: float = 50.0,     # wider default so offline data is always useful
    max_results: int = 10,
) -> Dict:
    """
    Return nearby emergency services from the offline JSON database.
    Always offline – no HTTP calls.
    """
    if service_types is None:
        service_types = ALL_SERVICE_TYPES

    services = get_offline_services(lat, lon, service_types, max_results)

    return {
        "services":         services[:max_results],
        "is_online":        False,      # always offline
        "total_found":      len(services),
        "search_radius_km": radius_km,
        "center":           {"lat": lat, "lon": lon},
        "source":           "offline",
    }


def get_all_emergency_services(lat: float, lon: float) -> Dict:
    """Return every category of emergency service near the user."""
    return find_services(lat, lon, ALL_SERVICE_TYPES, radius_km=50.0, max_results=20)
