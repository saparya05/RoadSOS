# 🚨 RoadSOS – AI Emergency Assistant (Fully Offline)

> A complete AI-powered road emergency assistant that works **100% without internet**.
> Detects emergencies, finds nearby services, shows an offline map, and supports voice input.

---

## ✅ What Works Offline

| Feature | Status | Notes |
|---|---|---|
| Emergency detection (NLP) | ✅ Offline | Pure keyword classifier |
| Nearby service lookup | ✅ Offline | 19 cities, 142+ services in JSON |
| National helplines | ✅ Offline | Always available |
| Chat history (SQLite) | ✅ Offline | Local DB, no cloud |
| Interactive map | ✅ Offline | Pure SVG, no tile server |
| Voice input (Whisper) | ✅ Offline* | *39 MB model download once |
| Voice input (Vosk) | ✅ Offline* | *Separate model download |
| Navigation links | ✅ Offline | Opens OSM in browser |
| Call buttons | ✅ Offline | `tel:` links work without internet |
| FastAPI backend | ✅ Offline | All endpoints use local data |

---

## 🏗️ Project Structure

```
RoadSOS/
├── backend/
│   ├── __init__.py
│   ├── chatbot.py              ← conversation engine (offline)
│   ├── database.py             ← SQLite persistence (offline)
│   ├── emergency_classifier.py ← NLP classifier (offline)
│   ├── main.py                 ← FastAPI server (offline)
│   ├── offline_services.py     ← JSON service lookup (offline)
│   ├── service_finder.py       ← service search – offline only
│   └── voice_input.py          ← STT: Whisper → Vosk → Sphinx
│
├── frontend/
│   ├── app.py                  ← Streamlit UI (offline)
│   └── map_view.py             ← Pure SVG map (offline, no tiles)
│
├── data/
│   ├── offline_services.json   ← 19 cities, 142+ services
│   └── roadsos.db              ← SQLite (auto-created)
│
├── requirements.txt
├── run.sh                      ← Linux/Mac launcher
├── run.bat                     ← Windows launcher
└── README.md
```

---

## ⚙️ Installation

### Step 1 – Clone / unzip

```bash
cd RoadSOS
```

### Step 2 – Install dependencies

```bash
# Linux / Mac
bash run.sh install

# Windows
run.bat install

# Or manually:
pip install -r requirements.txt
```

### Step 3 – Download offline STT model (optional but recommended)

For voice input to work **without internet**:

```bash
# Linux / Mac
bash run.sh download-stt

# Windows
run.bat download-stt

# Or manually (downloads ~39 MB Whisper tiny model):
python -c "import whisper; whisper.load_model('tiny')"
```

> **Without this step**, voice input falls back to Google Speech API (needs internet).
> Text input works perfectly without any model download.

---

## 🚀 Running the App

### Option A – Streamlit only (recommended, no API needed)

```bash
bash run.sh          # Linux/Mac
run.bat              # Windows
streamlit run frontend/app.py   # Direct
```

Open: **http://localhost:8501**

### Option B – Full stack (FastAPI + Streamlit)

```bash
bash run.sh full
```

- Frontend: http://localhost:8501
- API docs:  http://localhost:8000/docs

---

## 🗣️ Voice Input

The app uses **streamlit-mic-recorder** for browser-based microphone access.

1. Click the **🎙️** button next to the chat input
2. Speak your emergency
3. Click **⏹️** to stop
4. Your speech is transcribed and sent automatically

**STT Engine priority** (all offline except the last):
1. **Whisper** (recommended) – run `bash run.sh download-stt` once
2. **Vosk** – download model from https://alphacephei.com/vosk/models → extract to `data/vosk-model-small-en-in-0.4/`
3. **Sphinx** – install `pocketsphinx`
4. **Google** – online fallback only

---

## 🗺️ Offline Map

The map is built with **pure Python SVG math** – no tile server, no Leaflet CDN, no internet.

- Mercator projection computed locally
- Grid lines, range circles, service markers all rendered as SVG
- Click any service marker for name, phone, and navigation link
- Navigation opens **OpenStreetMap** in browser (works without app internet)

---

## 📴 Offline Service Coverage

**19 cities with full service data:**
Delhi · Mumbai · Bangalore · Chennai · Hyderabad · Kolkata · Pune · Ahmedabad ·
Jaipur · Lucknow · Surat · Patna · Bhopal · Indore · Nagpur · Visakhapatnam ·
Kochi · Chandigarh · Guwahati

**Always available (national helplines):**

| Service | Number |
|---|---|
| National Emergency | 112 |
| Ambulance (EMRI) | 108 |
| Police | 100 |
| Fire Brigade | 101 |
| Highway Helpline | 1033 |
| NDRF / Disaster | 1078 |
| Women Helpline | 1091 |
| Child Helpline | 1098 |

**Outside covered cities:** Generic services with national helpline numbers are shown.

---

## 🔌 API Reference

All endpoints work offline (no external calls):

### `POST /chat`
```json
{
  "text": "My car met with an accident",
  "lat": 28.6139,
  "lon": 77.2090
}
```

### `GET /services/all?lat=28.6139&lon=77.2090`

### `POST /voice`
Upload audio file → returns `{ "text": "...", "engine": "whisper", "offline": true }`

### `GET /helplines`

### `GET /stats`

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| Voice not working | Run `bash run.sh download-stt` to cache Whisper model |
| Location shows Delhi | Allow browser GPS permission, or override in sidebar |
| No services found | Your city may not be in offline database – national helplines always shown |
| Map looks plain | Expected – SVG map, no satellite tiles (offline mode) |
| API not responding | App works without API (embedded mode) – ignore this |

---

*Built for road safety. In any emergency, call **112** first.*
