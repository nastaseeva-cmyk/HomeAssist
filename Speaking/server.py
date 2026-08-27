import os
import asyncio
import uvicorn
from pathlib import Path
from logger import get_logger
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from tts import load_model, generate_speech
from fastapi import FastAPI, Request, HTTPException


log = get_logger("speaking")
load_dotenv("config.env")

AUDIO_DIR = Path(__file__).resolve().parent.parent / "SharedData/audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

model = load_model()

app = FastAPI()

class TTSRequest(BaseModel):
    text: str

@app.get("/")
async def root():
    return {"status": "ready", "endpoint": "/tts"}

@app.post("/tts")
async def tts_endpoint(request: Request, payload: TTSRequest):
    if not payload.text.strip():
        log.error("400 Bad Request: Field 'text' must be a non-empty string")
        raise HTTPException(status_code=400, detail="Field 'text' must be a non-empty string")

    resident_language = os.environ.get("RESIDENT_LANGUAGE", None)
    output_path = await asyncio.to_thread(generate_speech, payload.text, model, resident_language)

    scheme = request.url.scheme
    host_header = request.headers.get("host")
    if not host_header:
        host_header = f"{request.client.host}:{request.url.port}"
        
    audio_url = f"{scheme}://{host_header}/audio/{Path(output_path).name}"

    return {
        "status": "ok",
        "audio_url": audio_url,
        "download_url": audio_url,
        "file": str(output_path),
    }

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    audio_path = AUDIO_DIR / filename
    if audio_path.exists() and audio_path.is_file():
        return FileResponse(audio_path, media_type="audio/wav", filename=filename)
    
    log.error(f"404 Not Found: Audio file not found: {filename}")
    raise HTTPException(status_code=404, detail="Audio file not found")


if __name__ == "__main__":
    host = os.environ.get("SPEAKING_HOST", None)
    port_str = os.environ.get("SPEAKING_PORT", None)

    if not host or not port_str:
        log.error("SPEAKING_HOST and SPEAKING_PORT must be set in config.env")
        exit(1)

    port = int(port_str)

    log.info(f"Starting Speaking TTS endpoint on http://{host}:{port}/tts (FastAPI)")
    uvicorn.run(app, host=host, port=port)
