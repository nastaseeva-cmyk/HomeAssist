import asyncio
import os
import time
import uvicorn
from calls import tts
from pathlib import Path
from logger import get_logger
from dotenv import load_dotenv
from pydantic import BaseModel
from cortex import act, analyze_inactive_posture, check_routine_anomaly
from db import init_db, write_event, write_conversation, write_routine_log
from llm import load_model, process_image, parse_json_response, process_stt_text
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, BackgroundTasks, Form


log = get_logger("thinking")
load_dotenv("config.env")

IMAGE_DIR = Path(__file__).resolve().parent.parent / "SharedData/images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

init_db()
model = load_model()

app = FastAPI()

class STTRequest(BaseModel):
    lang: str
    text: str
    location: str = "Unknown"


@app.post("/detection")
async def detection_req(
    request: Request,
    background_tasks: BackgroundTasks, 
    location: str = Form("Unknown"),
    file: UploadFile = File(...)
):
    image_bytes = await file.read()
    
    if not image_bytes:
        log.error("400 Bad Request: Missing image data")
        raise HTTPException(status_code=400, detail="Missing image data")

    content_type = file.content_type or "image/jpeg"
    if "png" in content_type:
        extension = "png"
    elif "jpeg" in content_type or "jpg" in content_type:
        extension = "jpg"
    else:
        extension = "bin"

    location_dir = IMAGE_DIR / location
    location_dir.mkdir(parents=True, exist_ok=True)
    filename = location_dir / f"capture_{int(time.time() * 1000)}.{extension}"
    filename.write_bytes(image_bytes)


    # Process the image with the LLM
    start_time = time.time()
    inference_result_str = process_image(model, str(filename))
    elapsed_time = time.time() - start_time        
    log.info(f"llm_time: {elapsed_time:.2f}s")


    # Process inference result
    resident_in_picture, multiple_people, status, greeting = parse_json_response(inference_result_str)


    # Act based on the inference result
    client_host = request.headers.get("host", "127.0.0.1")
    write_routine_log(resident_in_picture, multiple_people, status, location)
    response_payload = await act(client_host, filename, resident_in_picture, multiple_people, status, greeting, location)

    background_tasks.add_task(analyze_inactive_posture, model, location)

    return response_payload

@app.post("/stt")
async def stt_req(payload: STTRequest, request: Request):
    log.info(f"Incoming stt - lang: {payload.lang}, text: {payload.text}")
    
    resident_language = os.environ.get("RESIDENT_LANGUAGE", "en")
    
    # 20 characters minimum length
    if payload.lang == resident_language and len(payload.text.strip()) >= 20:
        is_addressing, status_update, spoken_response = process_stt_text(model, payload.text)
        
        if is_addressing.lower() == "yes" and spoken_response:
            client_host = request.headers.get("host", "127.0.0.1")
            audio_url = await tts(client_host, spoken_response)
            write_conversation(spoken_response)
            
            if status_update.lower() == "danger":
                write_event("STT_DANGER_DETECTED", f"Resident reported danger: {payload.text}")
                
            return {
                "status": "done", 
                "lang": payload.lang, 
                "text": payload.text,
                "audio_url": audio_url
            }

    return {"status": "done", "lang": payload.lang, "text": payload.text}

async def routine_analyzer_loop():
    await asyncio.sleep(60)
    while True:
        try:
            await check_routine_anomaly(model)
        except Exception as e:
            log.error(f"Error in routine analyzer loop: {e}")
        await asyncio.sleep(30*60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(routine_analyzer_loop())

if __name__ == "__main__":
    host = os.environ.get("THINKING_HOST", None)
    port_str = os.environ.get("THINKING_PORT", None)

    if not host or not port_str:
        log.error("THINKING_HOST and THINKING_PORT must be set in config.env")
        exit(1)

    port = int(port_str)

    log.info(f"Starting Thinking image endpoint on http://{host}:{port}/detection (FastAPI)")
    uvicorn.run(app, host=host, port=port)