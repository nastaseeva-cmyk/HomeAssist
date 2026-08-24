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
    
    cortex_response = await cortex(lang, text)

    response = {
        "status": "ok",
        "text": text,
        "language": lang,
        "model": "large-v3",
    }
    
    if cortex_response and "audio_url" in cortex_response and cortex_response["audio_url"]:
        original_url = cortex_response["audio_url"]
        # Rewrite the URL host to match the external host that the mobile app used
        client_host = request.headers.get("host", "127.0.0.1")
        ip_only = client_host.split(":")[0]
        # Assuming the tts service is at the same IP, port 9001 (based on thinking/calls.py)
        # Parse the port from the original URL if needed, but it's usually 9001
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(original_url)
            rewritten_url = parsed._replace(netloc=f"{ip_only}:{parsed.port}").geturl()
            response["audio_url"] = rewritten_url
        except Exception:
            response["audio_url"] = original_url

    return response

if __name__ == "__main__":
    host = os.environ.get("HEARING_HOST", None)
    port_str = os.environ.get("HEARING_PORT", None)

    if not host or not port_str:
        log.error("HEARING_HOST and HEARING_PORT must be set in config.env")
        exit(1)
        
    port = int(port_str)

    log.info(f"Starting Hearing endpoint on http://{host}:{port}/stt (FastAPI)")
    uvicorn.run(app, host=host, port=port)
