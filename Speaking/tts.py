import os
import time
import hashlib
import soundfile as sf
from pathlib import Path
from logger import get_logger
from omnivoice import OmniVoice

log = get_logger("speaking")

AUDIO_DIR = Path(__file__).resolve().parent.parent / "SharedData/audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def load_model():
    model_path = os.environ.get("TTS_MODEL_PATH", None)
    if not model_path:
        log.error("TTS model path not found in environment variables.")
        raise ValueError("TTS_MODEL_PATH is missing")

    log.info(f"Loading OmniVoice model from {model_path}")
    return OmniVoice.from_pretrained(
        model_path,
        device_map="auto",
    )

def generate_speech(text, model, lang):
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Text cannot be empty")

    token = hashlib.sha1(cleaned_text.encode("utf-8")).hexdigest()
    output_path = AUDIO_DIR / f"{token}.wav"

    start_time = time.time()

    try:
        voice_instruct = os.environ.get("TTS_VOICE_INSTRUCT", None)
        if voice_instruct:
            audio = model.generate(text=cleaned_text, instruct=f"{voice_instruct}")
        else:
            audio = model.generate(text=cleaned_text)
        
        sf.write(str(output_path), audio[0], 24000)

        elapsed_time = time.time() - start_time        
        log.info(f"Generated speech -> {output_path} (tts_time: {elapsed_time:.2f}s)")        
    
    except Exception as e:
        log.error(f"Error generating speech: {e}")
        return "error"

    return str(output_path)