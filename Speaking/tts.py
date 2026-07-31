import hashlib
from pathlib import Path
from typing import Optional, Union
import torch
import soundfile as sf
from omnivoice import OmniVoice

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

def load_model():
    return OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map = "cuda:0",
        dtype = torch.float16,
    )

def generate_speech(text, model):
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Text cannot be empty")

    token = hashlib.sha1(cleaned_text.encode("utf-8")).hexdigest()
    output_path = AUDIO_DIR / f"{token}.wav"

    audio = model.generate(
        text = cleaned_text,
        ref_audio="voices/quest.wav",
        # ref_audio="voices/toma.wav",
        ref_text="First came here in the mid mid-nineteen-nineties. I brought my mother, to Malaysia and the one thing that stood out from that very first visit, was that you could take the luggage trolleys on the escalators. Don't ask me why, but I always seem to remember in the airpoirt being able to do that. But since then I've been once or twice"
        # ref_text="Să luăm, de pildă, acest plic Delikat. Conține etelize sito. Cum se întrebuințează? Foarte simplu, scoatem plicul și citim:"
    )
    print(f"Generating speech for text: {cleaned_text} -> {output_path}")
    sf.write(str(output_path), audio[0], 24000)

    return str(output_path)
