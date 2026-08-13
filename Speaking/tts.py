import os
import torch
import hashlib
import soundfile as sf
from pathlib import Path
from logger import get_logger
from omnivoice import OmniVoice
from typing import Optional, Union


log = get_logger("speaking")

AUDIO_DIR = Path(__file__).resolve().parent.parent / "SharedData/audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VOICES_DIR = Path(__file__).resolve().parent.parent / "SharedData/voices"
VOICES_DIR.mkdir(parents=True, exist_ok=True)

def load_model():
    model_path = os.environ.get("TTS_MODEL_PATH", None)
    if not model_path:
        log.error(f"TTS model not found: {model_path}")

    return OmniVoice.from_pretrained(
        model_path,
        device_map = "cuda:0",
        dtype = torch.float16,
    )

def generate_speech(text, model, lang):
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Text cannot be empty")

    token = hashlib.sha1(cleaned_text.encode("utf-8")).hexdigest()
    output_path = AUDIO_DIR / f"{token}.wav"

    try:
        with open(f"{VOICES_DIR}/{lang}.txt", "r") as f:
            ref_text = f.readlines()
    except Exception as e:
        ref_text = None
        log.error(f"Referrence text file not found {e}")

    if os.path.exists(f"{VOICES_DIR}/{lang}.wav"):
        ref_audio = f"{VOICES_DIR}/{lang}.wav"
    else:
        ref_audio = None
        log.error(f"Referrence audio file not found {lang}")

    if ref_text and ref_audio:
        audio = model.generate(
            text = cleaned_text,
            ref_audio = ref_audio,
            ref_text = ref_text
        )
        log.info(f"Generating speech for text: {cleaned_text} -> {output_path}")
        sf.write(str(output_path), audio[0], 24000)
    else:
        output_path = "error"

    return str(output_path)
