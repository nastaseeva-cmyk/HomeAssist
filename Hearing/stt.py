import os
import base64
import tempfile
from pathlib import Path
from typing import Optional
from logger import get_logger
from faster_whisper import WhisperModel


log = get_logger("hearing")

def load_model():
    return WhisperModel(
        os.environ.get("STT_MODEL_PATH", None), 
        device="auto",
        compute_type="int8_float16"
    )

def extract_audio_bytes(payload=None, body=b"", content_type: str = "application/json") -> bytes:
    if payload is not None:
        if isinstance(payload, dict):
            audio_field = payload.get("audio")
            if isinstance(audio_field, str) and audio_field.strip():
                try:
                    return base64.b64decode(audio_field, validate=True)
                except Exception as exc:
                    raise ValueError("Field 'audio' must be valid base64-encoded bytes") from exc
            if isinstance(audio_field, (bytes, bytearray)):
                return bytes(audio_field)
        if isinstance(payload, str):
            return payload.encode("utf-8")

    if isinstance(body, str):
        return body.encode("utf-8")

    if body:
        return body

    raise ValueError("No audio bytes found in request")


def transcribe_audio(audio_bytes, model, language: Optional[str] = None):
    suffix = ".wav"
    if isinstance(audio_bytes, (bytes, bytearray)):
        suffix = ".wav"

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(audio_bytes)
            temp_file = handle.name

        if not hasattr(model, "transcribe"):
            raise RuntimeError("Loaded model does not expose a transcribe() method")

        segments, info = model.transcribe(temp_file, language=language, beam_size=5)
        text = "".join([segment.text for segment in segments]).strip()        
        lang = info.language or "unknown"
        
        return text, lang
    finally:
        if temp_file is not None:
            Path(temp_file).unlink(missing_ok=True)