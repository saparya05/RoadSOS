"""
RoadSOS – Voice Input  (offline-first)

Priority order:
  1. openai-whisper  – fully offline after tiny model is downloaded once (~39 MB)
  2. vosk            – fully offline (requires model download separately)
  3. SpeechRecognition w/ sphinx – offline (requires pocketsphinx)
  4. SpeechRecognition w/ Google – online fallback (only if internet available)

Never crashes – every path is guarded.
"""

import io
import os
import tempfile
from typing import Tuple


# ── Whisper (preferred offline engine) ───────────────────────────────────────

def _transcribe_whisper(audio_bytes: bytes, suffix: str = ".webm") -> str:
    """
    Transcribe using OpenAI Whisper (runs locally – no API key needed).
    Downloads the 'tiny' model (~39 MB) on first use; fully offline thereafter.
    """
    try:
        import whisper
        import numpy as np

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            model  = whisper.load_model("tiny")        # smallest, fastest
            result = model.transcribe(tmp_path, fp16=False)
            return result.get("text", "").strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError:
        return ""
    except Exception:
        return ""


# ── Vosk (offline, needs model folder) ────────────────────────────────────────

def _transcribe_vosk(audio_bytes: bytes) -> str:
    """
    Transcribe using Vosk (fully offline).
    Requires:  pip install vosk
    And a model folder at  data/vosk-model-small-en-in-0.4/
    Download:  https://alphacephei.com/vosk/models
    """
    try:
        import vosk
        import wave
        import json as _json

        model_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "vosk-model-small-en-in-0.4"
        )
        if not os.path.exists(model_dir):
            return ""

        model = vosk.Model(model_dir)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with wave.open(tmp_path, "rb") as wf:
                rec = vosk.KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)
                results = []
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    if rec.AcceptWaveform(data):
                        r = _json.loads(rec.Result())
                        results.append(r.get("text", ""))
                final = _json.loads(rec.FinalResult())
                results.append(final.get("text", ""))
            return " ".join(r for r in results if r).strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError:
        return ""
    except Exception:
        return ""


# ── SpeechRecognition – offline sphinx ───────────────────────────────────────

def _transcribe_sphinx(audio_bytes: bytes) -> str:
    """
    Transcribe using CMU Sphinx via SpeechRecognition (offline).
    Requires:  pip install SpeechRecognition pocketsphinx
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_sphinx(audio)
    except ImportError:
        return ""
    except Exception:
        return ""


# ── SpeechRecognition – Google (online fallback only) ────────────────────────

def _transcribe_google_online(audio_bytes: bytes, language: str = "en-IN") -> str:
    """
    Online fallback using Google Web Speech API.
    Only used when all offline methods fail AND internet is available.
    """
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language=language)
    except ImportError:
        return ""
    except Exception:
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

def transcribe_audio_bytes(
    audio_bytes: bytes,
    language: str = "en-IN",
    audio_format: str = "webm",
) -> Tuple[str, str]:
    """
    Transcribe audio bytes to text.
    Returns (transcribed_text, engine_used).
    Tries offline engines first; falls back to Google only if all else fails.
    """
    if not audio_bytes:
        return "", "none"

    # 1. Whisper (offline after first model download)
    text = _transcribe_whisper(audio_bytes, suffix=f".{audio_format}")
    if text:
        return text, "whisper"

    # 2. Vosk (fully offline, model must be present)
    text = _transcribe_vosk(audio_bytes)
    if text:
        return text, "vosk"

    # 3. Sphinx (fully offline, pocketsphinx must be installed)
    text = _transcribe_sphinx(audio_bytes)
    if text:
        return text, "sphinx"

    # 4. Google online (last resort)
    text = _transcribe_google_online(audio_bytes, language)
    if text:
        return text, "google_online"

    return "", "none"


def get_available_engine() -> str:
    """Return name of the best available STT engine."""
    try:
        import whisper
        return "whisper"
    except ImportError:
        pass
    vosk_model = os.path.join(
        os.path.dirname(__file__), "..", "data", "vosk-model-small-en-in-0.4"
    )
    if os.path.exists(vosk_model):
        try:
            import vosk
            return "vosk"
        except ImportError:
            pass
    try:
        import speech_recognition  # noqa: F401
        try:
            import pocketsphinx  # noqa: F401
            return "sphinx"
        except ImportError:
            return "google_online"
    except ImportError:
        pass
    return "none"


def is_voice_available() -> bool:
    return get_available_engine() != "none"


def is_offline_voice_available() -> bool:
    return get_available_engine() not in ("google_online", "none")
