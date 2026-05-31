"""
RoadSOS – Streamlit Frontend  (fully offline)

All network calls removed:
  • No Google Fonts CDN  →  system-safe font stack only
  • No Overpass / OSM tile server  →  offline JSON + SVG map
  • FastAPI call is localhost (optional) with direct-import fallback
  • Voice STT uses Whisper offline-first
  • Navigation links use OSM (open in browser, no API key)

Run:  streamlit run frontend/app.py
"""

import sys, os, uuid, re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
import requests

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Road SOS",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ──────────────────────────────────────────────────────────────────
API_BASE    = os.getenv("ROADSOS_API_URL", "http://localhost:8000")
DEFAULT_LAT = 28.6139   # New Delhi fallback
DEFAULT_LON = 77.2090

QUICK_ACTIONS = [
    ("🚗 Accident",  "I met with an accident on the road"),
    ("🔧 Breakdown", "My vehicle broke down and will not start"),
    ("🩺 Injury",    "Someone is injured and needs medical help"),
    ("🔥 Fire",      "There is a fire emergency"),
    ("👮 Theft",     "I am being robbed or attacked"),
    ("🔩 Puncture",  "I have a flat tyre on the highway"),
]

EMERGENCY_NUMBERS = [
    ("National Emergency", "112"),
    ("Ambulance (EMRI)",   "108"),
    ("Police",             "100"),
    ("Fire Brigade",       "101"),
    ("Highway Helpline",   "1033"),
    ("NDRF / Disaster",    "1078"),
]

_QUICK_MAP = {label: text for label, text in QUICK_ACTIONS}

# ── Session state ──────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "session_id":        lambda: str(uuid.uuid4()),
    "messages":          list,
    "sidebar_sessions":  list,
    "user_lat":          lambda: DEFAULT_LAT,
    "user_lon":          lambda: DEFAULT_LON,
    "last_services":     list,
    "current_emergency": lambda: None,
    "loc_acquired":      lambda: False,
    "show_map":          lambda: False,
    "show_loc":          lambda: False,
    "pending_input":     lambda: None,
}
for _k, _f in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _f() if callable(_f) else _f

# ── CSS – no external font CDN ─────────────────────────────────────────────────
st.markdown("""
<style>
/*
  Offline-safe font stack:
  Tries system UI fonts → common installed fonts → generic sans-serif.
  No CDN fetch whatsoever.
*/
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    background: #0D0D14 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, "Noto Sans", sans-serif !important;
    color: #ECECF1 !important;
}

/* hide Streamlit chrome */
header[data-testid="stHeader"],
footer, #MainMenu, .stDeployButton,
div[data-testid="stToolbar"],
div[data-testid="stDecoration"] { display:none !important; }

.main .block-container { padding:0 0 80px 0 !important; max-width:100% !important; }

/* ── sidebar ── */
section[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: 1px solid #1E1E2E !important;
    width: 260px !important;
}
section[data-testid="stSidebar"] > div { padding:0 !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label { color:#ECECF1 !important; }

section[data-testid="stSidebar"] .stButton>button {
    background: transparent !important;
    color: #C5C5D2 !important;
    border: 1px solid #2A2A3E !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    width: 100% !important;
    text-align: left !important;
    transition: background .15s, border-color .15s !important;
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background: #1E1E2E !important;
    border-color: #E53E3E !important;
    color: #fff !important;
}

/* ── header ── */
.sos-header {
    display:flex; align-items:center; height:56px;
    padding:0 24px;
    background:#111118; border-bottom:1px solid #1E1E2E;
    position:sticky; top:0; z-index:100;
}
.sos-header-title { font-size:17px; font-weight:600; color:#ECECF1; letter-spacing:-.3px; }
.sos-live-dot {
    width:7px; height:7px; background:#48BB78; border-radius:50%;
    margin-left:10px; box-shadow:0 0 6px #48BB78;
    animation:blink-dot 2s infinite;
}
@keyframes blink-dot{0%,100%{opacity:1}50%{opacity:.2}}

/* ── chat bubbles ── */
.chat-wrap { display:flex; flex-direction:column; gap:0; padding:16px 0; }
.chat-inner { width:100%; max-width:760px; margin:0 auto; padding:0 18px; }

.msg-row { display:flex; margin-bottom:4px; }
.msg-row-user { justify-content:flex-end; }
.msg-row-ai   { justify-content:flex-start; align-items:flex-end; gap:10px; }

.ai-avatar {
    width:28px; height:28px; flex-shrink:0;
    background:linear-gradient(135deg,#E53E3E,#C05621);
    border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:13px; margin-bottom:18px;
}
.bubble {
    max-width:82%; padding:11px 16px;
    font-size:14px; line-height:1.65; word-break:break-word;
}
.bubble-user {
    background:#2A3F8F; color:#EBF4FF;
    border-radius:18px 18px 4px 18px;
    box-shadow:0 1px 8px rgba(42,63,143,.4);
}
.bubble-ai {
    background:#16161F; border:1px solid #1E1E30; color:#ECECF1;
    border-radius:4px 18px 18px 18px;
    box-shadow:0 1px 8px rgba(0,0,0,.3);
}
.bubble-ai.prio-critical { border-color:#9B2C2C; }
.bubble-ai.prio-high     { border-color:#7B341E; }

.msg-meta { font-size:10px; color:#555; margin-top:4px; margin-bottom:14px; padding:0 4px; }
.msg-meta-user { text-align:right; }

/* ── service cards ── */
.svc-section-title {
    font-size:11px; font-weight:600; color:#555;
    letter-spacing:.08em; text-transform:uppercase;
    margin:18px 0 8px;
}
.svc-grid {
    display:grid;
    grid-template-columns:repeat(auto-fill, minmax(210px,1fr));
    gap:10px; margin-bottom:18px;
}
.svc-card {
    background:#13131C; border:1px solid #1E1E2E; border-radius:12px;
    padding:13px; transition:border-color .2s,transform .2s;
}
.svc-card:hover { border-color:#4A5568; transform:translateY(-2px); }
.svc-name  { font-size:14px; font-weight:600; color:#ECECF1; margin-bottom:4px; }
.svc-dist  { font-size:12px; color:#718096; margin-bottom:3px; }
.svc-phone { font-size:13px; color:#68D391; font-weight:600; margin-bottom:10px; font-family:monospace; }
.svc-actions { display:flex; gap:7px; }
.svc-btn {
    flex:1; padding:6px 10px; border-radius:7px; font-size:12px; font-weight:600;
    text-align:center; text-decoration:none; display:block; transition:opacity .15s;
}
.svc-btn:hover { opacity:.8; text-decoration:none; }
.svc-call { background:#1C3829; color:#9AE6B4; border:1px solid #276749; }
.svc-nav  { background:#172840; color:#90CDF4; border:1px solid #2B6CB0; }

/* ── quick-action pills ── */
.qa-wrap { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 16px; }
.qa-pill {
    background:#1A1A2A; border:1px solid #2A2A40; border-radius:20px;
    padding:7px 16px; font-size:13px; color:#C5C5D2; white-space:nowrap;
}

/* ── welcome ── */
.welcome-wrap {
    display:flex; flex-direction:column; align-items:center;
    justify-content:center; min-height:46vh; text-align:center;
    padding:40px 20px; gap:14px;
}
.welcome-icon { font-size:52px; }
.welcome-title { font-size:26px; font-weight:700; color:#ECECF1; margin:0; }
.welcome-sub { font-size:14px; color:#888; max-width:460px; line-height:1.7; margin:0; }
.wnum-row {
    display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:8px;
}
.wnum-pill {
    background:#1A1A26; border:1px solid #2A2A3E; border-radius:20px;
    padding:5px 14px; font-size:13px; color:#A0AEC0;
}
.wnum-pill strong { color:#FC8181; }

/* ── chat input ── */
div[data-testid="stChatInput"] {
    background:#0D0D14 !important; border-top:1px solid #1E1E2E !important;
    padding:10px 20px 14px !important;
    position:sticky !important; bottom:0 !important; z-index:90 !important;
}
div[data-testid="stChatInput"] > div {
    max-width:760px !important; margin:0 auto !important;
    background:#16161F !important; border:1px solid #2A2A3E !important;
    border-radius:14px !important; box-shadow:none !important;
}
div[data-testid="stChatInput"] textarea {
    background:transparent !important; color:#ECECF1 !important;
    border:none !important; font-size:14px !important;
    outline:none !important; box-shadow:none !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color:#555 !important; }

/* ── sidebar internals ── */
.sb-logo { padding:20px 16px 12px; border-bottom:1px solid #1E1E2E; }
.sb-logo-title { font-size:16px; font-weight:700; color:#ECECF1; }
.sb-logo-sub   { font-size:11px; color:#555; margin-top:2px; }
.sb-divider    { height:1px; background:#1E1E2E; margin:6px 16px; }
.sb-section    { padding:10px 16px 4px; }
.sb-label {
    font-size:11px; font-weight:600; color:#555;
    letter-spacing:.08em; text-transform:uppercase;
    margin-bottom:7px; display:block;
}
.sb-num-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:5px 0; border-bottom:1px solid #111;
}
.sb-num-label { font-size:12px; color:#A0AEC0; }
.sb-num-val   { font-size:13px; font-weight:700; color:#FC8181; font-family:monospace; }
.sb-sess-item {
    padding:9px 12px; border-radius:8px; margin:2px 0;
    border:1px solid transparent; transition:background .15s;
}
.sb-sess-item:hover { background:#1A1A26; border-color:#2A2A3E; }
.sb-sess-title {
    font-size:13px; color:#C5C5D2; font-weight:500;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.sb-sess-meta { font-size:11px; color:#555; margin-top:2px; font-family:monospace; }

.loc-panel {
    background:#13131C; border:1px solid #1E1E2E; border-radius:10px;
    padding:11px; margin:8px 0;
}
.loc-row { display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }
.loc-key { color:#666; }
.loc-val { color:#A0AEC0; font-family:monospace; }

/* ── map ── */
.map-title { font-size:12px; font-weight:600; color:#555; letter-spacing:.06em;
             text-transform:uppercase; margin:18px 0 8px; }

/* ── scrollbar ── */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#2A2A3E; border-radius:2px; }

/* ── sidebar overrides ── */
section[data-testid="stSidebar"] input[type="number"] {
    background:#1A1A26 !important; color:#ECECF1 !important;
    border:1px solid #2A2A3E !important; border-radius:6px !important;
    font-size:12px !important;
}
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    background:#1A1A26 !important; border-color:#2A2A3E !important;
    font-size:12px !important;
}

/* hide audio playback widget from mic recorder */
.stAudio,[data-testid="stAudio"]{ display:none !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _api(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    """Call FastAPI; silently return {} if unavailable (offline)."""
    try:
        url = f"{API_BASE}{endpoint}"
        r   = (requests.post(url, json=payload, timeout=10)
               if method == "POST"
               else requests.get(url, timeout=8))
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def _direct_chat(text: str, lat: float, lon: float) -> dict:
    """Call backend Python directly – no HTTP, works 100% offline."""
    try:
        from backend.chatbot  import handle_chat
        from backend.database import save_chat_turn, log_emergency

        result = handle_chat(text, lat, lon,
                             session_id=st.session_state.session_id)
        try:
            save_chat_turn(
                session_id     = st.session_state.session_id,
                user_text      = text,
                ai_response    = result.get("ai_message", ""),
                emergency_type = result.get("emergency_category"),
                priority       = result.get("priority"),
                confidence     = result.get("confidence"),
                lat=lat, lon=lon,
                services       = result.get("services", []),
            )
            etype = result.get("emergency_category")
            if etype and etype not in ("unknown", None):
                log_emergency(
                    session_id     = st.session_state.session_id,
                    emergency_type = etype,
                    priority       = result.get("priority", "MEDIUM"),
                    user_text      = text,
                    lat=lat, lon=lon,
                    services_count = len(result.get("services", [])),
                )
        except Exception:
            pass
        return result
    except Exception:
        return {
            "ai_message":        "⚠️ Could not process request. Please call **112** immediately.",
            "services":          [],
            "emergency_category":"unknown",
            "priority":          "HIGH",
            "is_online":         False,
        }


def send_message(text: str) -> None:
    text = text.strip()
    if not text:
        return

    ts  = datetime.now().strftime("%H:%M")
    lat = st.session_state.user_lat
    lon = st.session_state.user_lon

    st.session_state.messages.append({"role":"user","content":text,"ts":ts})

    # Try FastAPI first; fall back to direct import (offline)
    result = _api("/chat","POST",{
        "text":text,"lat":lat,"lon":lon,
        "session_id":st.session_state.session_id,
    })
    if not result:
        result = _direct_chat(text, lat, lon)

    services = result.get("services", [])
    priority = result.get("priority") or "MEDIUM"
    category = result.get("emergency_category")

    st.session_state.messages.append({
        "role":     "assistant",
        "content":  result.get("ai_message","I could not process that."),
        "ts":       datetime.now().strftime("%H:%M"),
        "priority": priority,
        "category": category,
        "services": services,
    })

    if services:
        st.session_state.last_services = services
    if category and category not in ("unknown", None):
        st.session_state.current_emergency = category
        st.session_state.show_map          = True

    _refresh_sessions()


def _refresh_sessions() -> None:
    try:
        from backend.database import get_all_sessions_with_last_message
        st.session_state.sidebar_sessions = get_all_sessions_with_last_message()
    except Exception:
        pass


def _new_chat() -> None:
    st.session_state.session_id        = str(uuid.uuid4())
    st.session_state.messages          = []
    st.session_state.last_services     = []
    st.session_state.current_emergency = None
    st.session_state.show_map          = False
    _refresh_sessions()
    st.rerun()


# ── HTML render helpers ────────────────────────────────────────────────────────

def _md(txt: str) -> str:
    """Minimal markdown → HTML (bold + line breaks)."""
    txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', txt)
    return txt.replace("\n", "<br>")


def _bubble(msg: dict) -> str:
    role     = msg["role"]
    content  = _md(msg["content"])
    ts       = msg.get("ts","")
    priority = (msg.get("priority") or "").lower()

    if role == "user":
        return (f'<div class="chat-inner">'
                f'<div class="msg-row msg-row-user">'
                f'<div><div class="bubble bubble-user">{content}</div>'
                f'<div class="msg-meta" style="text-align:right">{ts}</div>'
                f'</div></div></div>')

    p_cls = f"prio-{priority}" if priority in ("critical","high") else ""
    return (f'<div class="chat-inner">'
            f'<div class="msg-row msg-row-ai">'
            f'<div class="ai-avatar">🤖</div>'
            f'<div><div class="bubble bubble-ai {p_cls}">{content}</div>'
            f'<div class="msg-meta">Road SOS · {ts}</div>'
            f'</div></div></div>')


def _services_html(services: list) -> str:
    if not services:
        return ""
    lat = st.session_state.user_lat
    lon = st.session_state.user_lon
    cards = []
    for svc in services[:6]:
        name     = svc.get("name","Service")
        icon     = svc.get("icon","📍")
        phone    = svc.get("phone","N/A")
        dist     = svc.get("distance_km","?")
        direction= svc.get("direction","")
        svc_lat  = svc.get("lat", lat)
        svc_lon  = svc.get("lon", lon)
        dist_str = f"{dist:.1f} km" if isinstance(dist,(int,float)) else str(dist)
        # Offline-friendly OSM navigate link
        maps_url = (svc.get("maps_url") or
                    f"https://www.openstreetmap.org/directions"
                    f"?engine=fossgis_osrm_car"
                    f"&route={lat},{lon};{svc_lat},{svc_lon}")
        call_href = f"tel:{phone}" if phone and phone != "N/A" else "#"
        cards.append(
            f'<div class="svc-card">'
            f'<div class="svc-name">{icon} {name}</div>'
            f'<div class="svc-dist">📏 {dist_str} {direction}</div>'
            f'<div class="svc-phone">{phone}</div>'
            f'<div class="svc-actions">'
            f'<a class="svc-btn svc-call" href="{call_href}">📞 Call</a>'
            f'<a class="svc-btn svc-nav" href="{maps_url}" target="_blank">🧭 Navigate</a>'
            f'</div></div>'
        )
    return (f'<div class="chat-inner">'
            f'<div class="svc-section-title">Nearby Emergency Services</div>'
            f'<div class="svc-grid">{"".join(cards)}</div>'
            f'</div>')


def _welcome() -> str:
    pills = "".join(
        f'<span class="wnum-pill">{lbl}: <strong>{num}</strong></span>'
        for lbl, num in EMERGENCY_NUMBERS[:4]
    )
    return (f'<div class="chat-inner">'
            f'<div class="welcome-wrap">'
            f'<div class="welcome-icon">🚨</div>'
            f'<h2 class="welcome-title">Road SOS</h2>'
            f'<p class="welcome-sub">Describe your emergency and I\'ll detect '
            f'the situation, find the nearest help, and guide you through it.</p>'
            f'<div class="wnum-row">{pills}</div>'
            f'</div></div>')


def _render_map() -> None:
    lat      = st.session_state.user_lat
    lon      = st.session_state.user_lon
    services = st.session_state.last_services
    try:
        from frontend.map_view import map_to_html
        html = map_to_html(lat, lon, services)
        st.components.v1.html(html, height=350, scrolling=False)
    except Exception as e:
        st.markdown(
            f'<div style="background:#13131C;border:1px solid #1E1E2E;'
            f'border-radius:10px;padding:16px;text-align:center;color:#666;">'
            f'Map unavailable — {e}</div>',
            unsafe_allow_html=True,
        )


# ── Silent geolocation injection ──────────────────────────────────────────────

def _inject_geo() -> None:
    """Write GPS coords to URL query params; Streamlit picks them up on rerun."""
    st.components.v1.html("""
<script>
(function(){
  if(!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(function(p){
    var la=p.coords.latitude.toFixed(6), lo=p.coords.longitude.toFixed(6);
    var url=new URL(window.location.href);
    if(url.searchParams.get('lat')!==la||url.searchParams.get('lon')!==lo){
      url.searchParams.set('lat',la); url.searchParams.set('lon',lo);
      window.history.replaceState({},'',url.toString());
    }
  },null,{enableHighAccuracy:true,timeout:8000});
})();
</script>
""", height=0, scrolling=False)


def _pickup_geo() -> None:
    try:
        p = st.query_params
        if "lat" in p and "lon" in p and not st.session_state.loc_acquired:
            la, lo = float(p["lat"]), float(p["lon"])
            if -90 <= la <= 90 and -180 <= lo <= 180:
                st.session_state.user_lat    = la
                st.session_state.user_lon    = lo
                st.session_state.loc_acquired = True
    except Exception:
        pass


_pickup_geo()
_inject_geo()


# ── Voice transcription ────────────────────────────────────────────────────────

def _transcribe(audio_bytes: bytes) -> str:
    """Offline-first STT: Whisper → Sphinx → (Google online fallback)."""
    try:
        from backend.voice_input import transcribe_audio_bytes
        text, _ = transcribe_audio_bytes(audio_bytes, audio_format="webm")
        return text
    except Exception:
        return ""


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sb-logo">'
        '<div class="sb-logo-title">🚨 Road SOS</div>'
        '<div class="sb-logo-sub">AI Emergency Assistant · Offline Ready</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="padding:10px 16px 4px">', unsafe_allow_html=True)
    if st.button("＋  New Chat", use_container_width=True, key="btn_new"):
        _new_chat()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # Location toggle
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<span class="sb-label">Location</span>', unsafe_allow_html=True)
    loc_lbl = "📍 GPS acquired" if st.session_state.loc_acquired else "📡 Default (New Delhi)"
    if st.button(loc_lbl, use_container_width=True, key="btn_loc"):
        st.session_state.show_loc = not st.session_state.show_loc

    if st.session_state.show_loc:
        lat = st.session_state.user_lat
        lon = st.session_state.user_lon
        status = "GPS" if st.session_state.loc_acquired else "Default"
        st.markdown(
            f'<div class="loc-panel">'
            f'<div class="loc-row"><span class="loc-key">Status</span>'
            f'<span class="loc-val">{status}</span></div>'
            f'<div class="loc-row"><span class="loc-key">Latitude</span>'
            f'<span class="loc-val">{lat:.5f}°</span></div>'
            f'<div class="loc-row"><span class="loc-key">Longitude</span>'
            f'<span class="loc-val">{lon:.5f}°</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander("Override coordinates"):
            nlat = st.number_input("Lat",  value=lat, format="%.5f",
                                   step=0.001, key="ov_lat")
            nlon = st.number_input("Lon",  value=lon, format="%.5f",
                                   step=0.001, key="ov_lon")
            if st.button("Apply", key="btn_apply_loc"):
                st.session_state.user_lat    = nlat
                st.session_state.user_lon    = nlon
                st.session_state.loc_acquired = True
                st.session_state.show_loc    = False
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # Map toggle
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    map_lbl = "🗺️ Hide Map" if st.session_state.show_map else "🗺️ Show Map"
    if st.button(map_lbl, use_container_width=True, key="btn_map"):
        st.session_state.show_map = not st.session_state.show_map
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # Emergency numbers (pure HTML, no nested columns)
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<span class="sb-label">Emergency Numbers</span>', unsafe_allow_html=True)
    st.markdown(
        "".join(
            f'<div class="sb-num-row">'
            f'<span class="sb-num-label">{lbl}</span>'
            f'<a href="tel:{num}" style="text-decoration:none">'
            f'<span class="sb-num-val">{num}</span></a></div>'
            for lbl, num in EMERGENCY_NUMBERS
        ),
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # Chat history
    st.markdown('<div class="sb-section">', unsafe_allow_html=True)
    st.markdown('<span class="sb-label">Recent Chats</span>', unsafe_allow_html=True)
    if not st.session_state.sidebar_sessions:
        _refresh_sessions()
    sessions = st.session_state.sidebar_sessions
    if sessions:
        items = []
        for s in sessions[:12]:
            title = (s.get("title") or "Emergency Chat")[:40]
            ts    = (s.get("last_active_at") or "")[:16].replace("T"," ")
            items.append(
                f'<div class="sb-sess-item">'
                f'<div class="sb-sess-title">{title}</div>'
                f'<div class="sb-sess-meta">{ts}</div></div>'
            )
        st.markdown("".join(items), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-size:12px;color:#444;padding:6px 0">No history yet.</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── MAIN AREA ──────────────────────────────────────────────────────────────────

# Header
st.markdown(
    '<div class="sos-header">'
    '<span class="sos-header-title">Road SOS</span>'
    '<div class="sos-live-dot"></div>'
    '</div>',
    unsafe_allow_html=True,
)

messages = st.session_state.messages

if not messages:
    st.markdown(_welcome(), unsafe_allow_html=True)

    # Quick-action pills (visual)
    qa_pill_html = (
        '<div class="chat-inner"><div class="qa-wrap">'
        + "".join(f'<span class="qa-pill">{lbl}</span>' for lbl, _ in QUICK_ACTIONS)
        + '</div></div>'
    )
    st.markdown(qa_pill_html, unsafe_allow_html=True)

    # Clickable Streamlit buttons (no nesting – top-level columns)
    qa_cols = st.columns(len(QUICK_ACTIONS))
    for i, (lbl, txt) in enumerate(QUICK_ACTIONS):
        with qa_cols[i]:
            if st.button(lbl, key=f"qa_{i}", use_container_width=True):
                st.session_state.pending_input = txt

else:
    # Render messages + services
    parts = ["<div class='chat-wrap'>"]
    for msg in messages:
        parts.append(_bubble(msg))
        if msg["role"] == "assistant" and msg.get("services"):
            parts.append(_services_html(msg["services"]))
    parts.append("</div>")
    st.markdown("\n".join(parts), unsafe_allow_html=True)

    # Quick pills still visible
    st.markdown(
        '<div class="chat-inner"><div class="qa-wrap" style="margin-top:6px">'
        + "".join(f'<span class="qa-pill">{lbl}</span>' for lbl, _ in QUICK_ACTIONS)
        + '</div></div>',
        unsafe_allow_html=True,
    )
    qa_cols = st.columns(len(QUICK_ACTIONS))
    for i, (lbl, txt) in enumerate(QUICK_ACTIONS):
        with qa_cols[i]:
            if st.button(lbl, key=f"qa_{i}", use_container_width=True):
                st.session_state.pending_input = txt

# Map panel
if st.session_state.show_map:
    st.markdown(
        '<div class="chat-inner"><div class="map-title">📍 Nearby Services Map</div></div>',
        unsafe_allow_html=True,
    )
    _, mc, _ = st.columns([1, 8, 1])
    with mc:
        _render_map()

# ── Input row: mic + chat input ────────────────────────────────────────────────
try:
    from streamlit_mic_recorder import mic_recorder
    mic_col, inp_col = st.columns([1, 11])
    with mic_col:
        audio = mic_recorder(
            start_prompt="🎙️",
            stop_prompt="⏹️",
            just_once=True,
            use_container_width=True,
            key="mic",
        )
    with inp_col:
        user_typed = st.chat_input(
            placeholder="Describe your emergency…",
            key="chat_in",
        )
    if audio and audio.get("bytes"):
        with st.spinner("Transcribing…"):
            transcript = _transcribe(audio["bytes"])
        if transcript:
            st.session_state.pending_input = transcript

except ImportError:
    user_typed = st.chat_input(
        placeholder="Describe your emergency…",
        key="chat_in_fallback",
    )

# ── Process inputs (exactly once per rerun) ────────────────────────────────────
pending = st.session_state.pending_input
if pending:
    st.session_state.pending_input = None
    send_message(pending)
    st.rerun()

if user_typed:
    send_message(user_typed)
    st.rerun()
