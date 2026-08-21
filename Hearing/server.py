import os
import time
import uvicorn
from pathlib import Path
from calls import cortex
from logger import get_logger
from dotenv import load_dotenv
from stt import load_model, transcribe_audio
from fastapi import FastAPI, Request, HTTPException, UploadFile, File


log = get_logger("hearing")
load_dotenv("config.env")

AUDIO_DIR = Path(__file__).resolve().parent.parent / "SharedData/audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

model = load_model()

app = FastAPI()

@app.post("/stt")
async def stt_endpoint(request: Request, file: UploadFile = File(...)):
    audio_bytes = await file.read()
    
    if not audio_bytes:
        log.error("400 Bad Request: Missing request body")
        raise HTTPException(status_code=400, detail="Missing request body")

    content_type = file.content_type or "audio/wav"

    if "wav" in content_type:
        extension = "wav"
    else:
        extension = "bin"

    file_path = AUDIO_DIR / f"stt_audio_{int(time.time() * 1000)}.{extension}"
    file_path.write_bytes(audio_bytes)

    start_time = time.time()
    text, lang = transcribe_audio(audio_bytes, model=model)
    elapsed_time = time.time() - start_time
    log.info(f"stt_time: {elapsed_time:.2f}s / {lang}:{text}")
    
    environ = {}
    cortex(environ, lang, text)

    return {
        "status": "ok",
        "text": text,
        "language": lang,
        "model": "large-v3",
    }

if __name__ == "__main__":
    host = os.environ.get("HEARING_HOST", None)
    port_str = os.environ.get("HEARING_PORT", None)

    if not host or not port_str:
        log.error("HEARING_HOST and HEARING_PORT must be set in config.env")
        exit(1)
        
    port = int(port_str)

    log.info(f"Starting Hearing endpoint on http://{host}:{port}/stt (FastAPI)")
    uvicorn.run(app, host=host, port=port)
