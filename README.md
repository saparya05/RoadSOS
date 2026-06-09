# RoadSOS – AI-Powered Offline Emergency Assistant

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red)
![SQLite](https://img.shields.io/badge/SQLite-Offline%20Database-lightgrey)
![Offline First](https://img.shields.io/badge/Offline-First-success)

An AI-powered road emergency assistant designed to operate entirely offline. RoadSOS helps users identify emergencies, locate nearby services, access emergency helplines, and interact through voice commands without relying on cloud services or an active internet connection.

---

## Demo

[Demo Video.webm](https://github.com/user-attachments/assets/0c35fcab-3435-425d-8188-5e0bc5a2bd23)

---

## Key Features

### Emergency Detection

* Offline NLP-based emergency classification
* Instant identification of road accidents and critical situations
* No internet dependency

### Nearby Service Discovery

* Search nearby hospitals, police stations, towing services, and fuel stations
* Uses locally stored service database
* Supports 19 major Indian cities

### Offline Interactive Map

* Pure SVG-based rendering
* No external map providers
* Local Mercator projection implementation

### Voice Assistance

* Offline speech-to-text support
* Whisper Tiny
* Vosk
* PocketSphinx
* Automatic fallback mechanism

### Emergency Helplines

* National emergency contacts available at all times
* Accessible even without network connectivity

### Local Data Storage

* SQLite-based chat history
* No cloud storage
* Privacy-focused architecture

---

## Offline Capability Matrix

| Feature                    | Offline Support |
| -------------------------- | --------------- |
| Emergency Detection        | ✅               |
| Service Discovery          | ✅               |
| Emergency Helplines        | ✅               |
| SQLite Storage             | ✅               |
| Interactive Map            | ✅               |
| Voice Input (Whisper/Vosk) | ✅               |
| Navigation Links           | ✅               |
| FastAPI Backend            | ✅               |

---

## System Architecture

```text
User
 │
 ▼
Streamlit Frontend
 │
 ├── Voice Input
 ├── Offline Map
 ├── Chat Interface
 │
 ▼
FastAPI Backend
 │
 ├── Emergency Classifier
 ├── Service Finder
 ├── Offline Services Database
 ├── SQLite Storage
 └── Voice Processing Engine
```

---

## Project Structure

```text
RoadSOS/
├── backend/
│   ├── chatbot.py
│   ├── database.py
│   ├── emergency_classifier.py
│   ├── main.py
│   ├── offline_services.py
│   ├── service_finder.py
│   └── voice_input.py
│
├── frontend/
│   ├── app.py
│   └── map_view.py
│
├── data/
│   ├── offline_services.json
│   └── roadsos.db
│
├── requirements.txt
├── run.sh
├── run.bat
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd RoadSOS
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or use helper scripts:

```bash
bash run.sh install
```

```cmd
run.bat install
```

---

## Optional: Enable Offline Voice Recognition

Download the Whisper Tiny model:

```bash
python -c "import whisper; whisper.load_model('tiny')"
```

Without this setup, the application falls back to online speech recognition services.

---

## Running the Application

### Streamlit Mode

```bash
streamlit run frontend/app.py
```

Open:

```text
http://localhost:8501
```

### Full Stack Mode

```bash
bash run.sh full
```

Services:

* Frontend → `http://localhost:8501`
* API Docs → `http://localhost:8000/docs`

---

## Supported Cities

RoadSOS currently provides offline service coverage for:

Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Kolkata, Pune, Ahmedabad, Jaipur, Lucknow, Surat, Patna, Bhopal, Indore, Nagpur, Visakhapatnam, Kochi, Chandigarh, and Guwahati.

For unsupported locations, national emergency helplines remain available.

---

## Emergency Helplines

| Service            | Number |
| ------------------ | ------ |
| National Emergency | 112    |
| Ambulance          | 108    |
| Police             | 100    |
| Fire Brigade       | 101    |
| Highway Helpline   | 1033   |
| Disaster Response  | 1078   |
| Women Helpline     | 1091   |
| Child Helpline     | 1098   |

---

## API Endpoints

### Chat

```http
POST /chat
```

```json
{
  "text": "My car met with an accident",
  "lat": 28.6139,
  "lon": 77.2090
}
```

### Services

```http
GET /services/all
```

### Voice Processing

```http
POST /voice
```

### Helplines

```http
GET /helplines
```

### Statistics

```http
GET /stats
```

---

## Technology Stack

* Python
* FastAPI
* Streamlit
* SQLite
* Whisper
* Vosk
* PocketSphinx
* SVG Rendering

---

## Future Enhancements

* Multilingual emergency support
* Offline route guidance
* AI-powered incident severity prediction
* SMS-based emergency alerts
* Expanded city coverage

---

## License

This project is intended for educational, research, and road-safety applications.

---

**Important:** In any real emergency, immediately contact **112** or your local emergency services.
