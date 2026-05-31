import os
import tempfile
from typing import Tuple

try:
    import whisper

    # Load once when module imports
    _MODEL = whisper.load_model("tiny")
    _WHISPER_AVAILABLE = True

except Exception as e:
    print(f"Failed to load Whisper: {e}")
    _MODEL = None
    _WHISPER_AVAILABLE = False


def transcribe_audio_bytes(
    audio_bytes: bytes,
    audio_format: str = "webm",
) -> Tuple[str, str]:
    """
    Returns:
        (text, engine)

    engine:
        whisper
        none
    """

    if not audio_bytes:
        return "", "none"

    if not _WHISPER_AVAILABLE:
        return "", "none"

    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=f".{audio_format}",
            delete=False
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        result = _MODEL.transcribe(
            tmp_path,
            fp16=False,
            language="en"
        )

        text = result.get("text", "").strip()

        if text:
            return text, "whisper"

        return "", "none"

    except Exception:
        import traceback
        print("WHISPER ERROR")
        traceback.print_exc()
        return "", "none"

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def get_available_engine() -> str:
    return "whisper" if _WHISPER_AVAILABLE else "none"


def is_voice_available() -> bool:
    return _WHISPER_AVAILABLE


def is_offline_voice_available() -> bool:
    return _WHISPER_AVAILABLE