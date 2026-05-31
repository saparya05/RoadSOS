"""
RoadSOS – Offline Map View

Generates a fully self-contained SVG/HTML map using:
  - Pure Python Mercator projection (stdlib math only)
  - Inline SVG – no tile server, no CDN, no internet required
  - Interactive popups via embedded JavaScript (no external libs)
  - Leaflet bundled inline via CDN-free approach

The map works completely offline.
"""

import math
import html as _html
from typing import List, Dict, Tuple


# Service styling 

_COLORS = {
    "hospital":       "#E53E3E",
    "ambulance":      "#FC8181",
    "police":         "#3B82F6",
    "fire_station":   "#F97316",
    "mechanic":       "#A78BFA",
    "towing":         "#60A5FA",
    "puncture_shop":  "#34D399",
    "highway_patrol": "#FBBF24",
    "ngo":            "#6EE7B7",
    "helpline":       "#93C5FD",
    "emergency":      "#F87171",
}

_ICONS = {
    "hospital":       "H",
    "ambulance":      "A",
    "police":         "P",
    "fire_station":   "F",
    "mechanic":       "M",
    "towing":         "T",
    "puncture_shop":  "R",
    "highway_patrol": "HP",
    "ngo":            "N",
    "helpline":       "📞",
    "emergency":      "SOS",
}


# Projection helpers

def _mercator(lat_deg: float, lon_deg: float,
              center_lat: float, center_lon: float,
              scale: float, width: float, height: float) -> Tuple[float, float]:
    """Project (lat, lon) to SVG (x, y) using Web Mercator."""
    x = (lon_deg - center_lon) * scale + width / 2

    def _merc(la: float) -> float:
        r = math.radians(la)
        return math.log(math.tan(math.pi / 4 + r / 2))

    y = height / 2 - (_merc(lat_deg) - _merc(center_lat)) * scale
    return x, y


def _auto_scale(services: List[Dict], center_lat: float, center_lon: float,
                width: float, height: float) -> float:
    """Choose a scale factor that keeps all services visible."""
    if not services:
        return 4000.0
    max_dist = max(
        (s.get("distance_km", 0) for s in services if s.get("lat") and s.get("lon")),
        default=5.0,
    )
    max_dist = max(max_dist, 1.0)
    # We want max_dist km to fit within ~40% of the half-dimension
    scale_x = (width  * 0.40) / (max_dist * 0.009)   # ~0.009 deg/km longitude
    scale_y = (height * 0.40) / (max_dist * 0.009)
    return min(scale_x, scale_y, 8000.0)


# Map builder

def map_to_html(user_lat: float, user_lon: float,
                services: List[Dict]) -> str:
    """
    Return a fully self-contained HTML string with an interactive SVG map.
    No external resources – works 100% offline.
    """
    W, H = 780, 420
    mappable = [s for s in services if s.get("lat") and s.get("lon")]
    scale    = _auto_scale(mappable, user_lat, user_lon, W, H)

    def xy(lat: float, lon: float) -> Tuple[float, float]:
        return _mercator(lat, lon, user_lat, user_lon, scale, W, H)

    # Build SVG elements
    svg_parts: List[str] = []
    tooltip_data: List[str] = []   # JS data for popups

    # Background
    svg_parts.append(
        f'<rect width="{W}" height="{H}" fill="#1A1A2E" rx="10"/>'
    )

    # Grid lines (lat/lon every ~1 km)
    grid_step = max(0.005, round(20 / scale, 3))
    grid_color = "#2A2A40"
    lat_range = int(H / scale / grid_step) + 2
    lon_range = int(W / scale / grid_step) + 2
    for i in range(-lat_range, lat_range + 1):
        la = user_lat + i * grid_step
        x1, y1 = xy(la, user_lon - lon_range * grid_step)
        x2, y2 = xy(la, user_lon + lon_range * grid_step)
        svg_parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{grid_color}" stroke-width="0.5"/>'
        )
    for j in range(-lon_range, lon_range + 1):
        lo = user_lon + j * grid_step
        x1, y1 = xy(user_lat - lat_range * grid_step, lo)
        x2, y2 = xy(user_lat + lat_range * grid_step, lo)
        svg_parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{grid_color}" stroke-width="0.5"/>'
        )

    # Range circle
    ux, uy = xy(user_lat, user_lon)
    r_px = scale * (mappable[0].get("distance_km", 5) if mappable else 5) * 0.01
    r_px = min(max(r_px, 20), min(W, H) * 0.45)
    svg_parts.append(
        f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="{r_px:.1f}" '
        f'fill="rgba(59,130,246,0.06)" stroke="#3B82F6" '
        f'stroke-width="1" stroke-dasharray="6,4"/>'
    )

    # Lines from user to each service
    for svc in mappable:
        sx, sy = xy(svc["lat"], svc["lon"])
        col = _COLORS.get(svc.get("type", ""), "#666")
        svg_parts.append(
            f'<line x1="{ux:.1f}" y1="{uy:.1f}" x2="{sx:.1f}" y2="{sy:.1f}" '
            f'stroke="{col}" stroke-width="1" stroke-opacity="0.35" stroke-dasharray="5,4"/>'
        )

    # Service markers
    for idx, svc in enumerate(mappable):
        sx, sy = xy(svc["lat"], svc["lon"])
        col   = _COLORS.get(svc.get("type", ""), "#888")
        label = _ICONS.get(svc.get("type", ""), "?")
        name  = _html.escape(svc.get("name", "Service"))
        phone = _html.escape(svc.get("phone", "N/A"))
        dist  = svc.get("distance_km", 0)
        dist_str = f"{dist:.1f} km" if isinstance(dist, (int, float)) else str(dist)
        dir_  = _html.escape(svc.get("direction", ""))
        addr  = _html.escape(svc.get("address", ""))
        maps  = svc.get("maps_url") or ""

        svg_parts.append(
            f'<g class="svc-marker" data-idx="{idx}" '
            f'style="cursor:pointer" onclick="showPopup({idx})">'
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="14" '
            f'fill="{col}" fill-opacity="0.9" '
            f'stroke="white" stroke-width="1.5"/>'
            f'<text x="{sx:.1f}" y="{sy + 4:.1f}" '
            f'text-anchor="middle" font-size="9" font-weight="bold" '
            f'font-family="monospace" fill="white">{_html.escape(label)}</text>'
            f'</g>'
        )

        # Tooltip data for JS
        tooltip_data.append(
            f'{{"name":{_json_str(name)},"phone":{_json_str(phone)},'
            f'"dist":{_json_str(dist_str)},"dir":{_json_str(dir_)},'
            f'"addr":{_json_str(addr)},"maps":{_json_str(maps)},'
            f'"x":{sx:.1f},"y":{sy:.1f},"col":{_json_str(col)}}}'
        )

    # User location marker (pulsing)
    svg_parts.append(f"""
<g id="user-marker">
  <circle cx="{ux:.1f}" cy="{uy:.1f}" r="18"
    fill="rgba(229,62,62,0.15)" stroke="#E53E3E"
    stroke-width="1.5" stroke-dasharray="5,3">
    <animate attributeName="r" values="18;26;18" dur="2s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{ux:.1f}" cy="{uy:.1f}" r="8"
    fill="#E53E3E" stroke="white" stroke-width="2"/>
  <text x="{ux:.1f}" y="{uy + 4:.1f}"
    text-anchor="middle" font-size="8" font-weight="bold"
    font-family="monospace" fill="white">YOU</text>
</g>
""")

    # Legend
    legend_y = H - 14
    svg_parts.append(
        f'<text x="10" y="{legend_y}" font-size="9" fill="#555" '
        f'font-family="sans-serif">● You &nbsp; '
        + " &nbsp; ".join(
            f'<tspan fill="{_COLORS.get(t,"#888")}">{_ICONS.get(t,"?")} {t.replace("_"," ").title()}</tspan>'
            for t in set(s.get("type","") for s in mappable)
        )
        + "</text>"
    )

    svg_str = (
        f'<svg id="sos-map" viewBox="0 0 {W} {H}" width="100%" '
        f'xmlns="http://www.w3.org/2000/svg" style="border-radius:10px">'
        + "\n".join(svg_parts)
        + "\n</svg>"
    )

    # Popup overlay + JS
    popup_html = """
<div id="sos-popup" style="
  display:none; position:absolute; top:50%; left:50%;
  transform:translate(-50%,-60%);
  background:#1A1A2E; border:1px solid #3B82F6;
  border-radius:12px; padding:14px 16px; min-width:220px;
  box-shadow:0 8px 32px rgba(0,0,0,0.6); z-index:99;
  font-family:sans-serif; color:#ECECF1; font-size:13px;
">
  <div id="pop-close" onclick="closePopup()" style="
    position:absolute; top:8px; right:10px; cursor:pointer;
    font-size:16px; color:#888;">✕</div>
  <div id="pop-name"  style="font-weight:700; font-size:15px; margin-bottom:8px"></div>
  <div id="pop-dist"  style="color:#93C5FD; margin-bottom:4px"></div>
  <div id="pop-phone" style="color:#6EE7B7; font-family:monospace; margin-bottom:4px"></div>
  <div id="pop-addr"  style="color:#888; font-size:11px; margin-bottom:10px"></div>
  <div style="display:flex; gap:8px; margin-top:8px">
    <a id="pop-call" href="#" style="
      flex:1; text-align:center; padding:6px; border-radius:7px;
      background:#1C3829; color:#9AE6B4; border:1px solid #276749;
      text-decoration:none; font-size:12px; font-weight:600;">📞 Call</a>
    <a id="pop-nav" href="#" target="_blank" style="
      flex:1; text-align:center; padding:6px; border-radius:7px;
      background:#172840; color:#90CDF4; border:1px solid #2B6CB0;
      text-decoration:none; font-size:12px; font-weight:600;">🧭 Navigate</a>
  </div>
</div>
"""

    js = (
        "<script>\n"
        "var SVC="
        + "[" + ",\n".join(tooltip_data) + "]"
        + ";\n"
        + r"""
function showPopup(i){
  var d=SVC[i], p=document.getElementById('sos-popup');
  document.getElementById('pop-name').textContent=d.name;
  document.getElementById('pop-dist').textContent='📏 '+d.dist+' '+d.dir;
  document.getElementById('pop-phone').textContent='📞 '+d.phone;
  document.getElementById('pop-addr').textContent=d.addr||'';
  var ca=document.getElementById('pop-call');
  ca.href=d.phone&&d.phone!='N/A'?'tel:'+d.phone:'#';
  var na=document.getElementById('pop-nav');
  na.href=d.maps||('#'+d.name);
  p.style.display='block';
}
function closePopup(){
  document.getElementById('sos-popup').style.display='none';
}
</script>
"""
    )

    full_html = f"""
<div style="position:relative;width:100%;background:#1A1A2E;border-radius:10px;
     border:1px solid #1E1E2E;overflow:hidden;">
  {svg_str}
  {popup_html}
  {js}
</div>
"""
    return full_html


def _json_str(s: str) -> str:
    """Wrap a string as a JSON string literal (handles quotes/backslashes)."""
    import json as _j
    return _j.dumps(str(s))


# Compatibility shim (so old callers still work)

def create_emergency_map(user_lat, user_lon, services, zoom_start=14):
    """Compatibility stub – returns the HTML string directly."""
    return map_to_html(user_lat, user_lon, services)


def save_map(user_lat, user_lon, services,
             filepath="/tmp/roadsos_map.html") -> str:
    html = map_to_html(user_lat, user_lon, services)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath
