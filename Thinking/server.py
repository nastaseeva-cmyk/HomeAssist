import os
import time
import uvicorn
from db import init_db, write_event, write_conversation
from cortex import act
from pathlib import Path
from logger import get_logger
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, BackgroundTasks
from llm import load_model, process_image, parse_json_response, process_inactive_sequence, process_stt_text
from calls import tts


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

def analyze_inactive_posture():
    interval = int(os.environ.get("INACTIVITY_INTERVAL_SECONDS", 7200))
    images = sorted(IMAGE_DIR.glob("capture_*.jpg"), key=os.path.getmtime, reverse=True)
    
    if len(images) >= 3:
        newest = images[0]
        newest_time = os.path.getmtime(newest)

        target_mid = newest_time - (interval / 2)
        target_old = newest_time - interval

        def get_closest(target_time, img_list):
            return min(img_list, key=lambda x: abs(os.path.getmtime(x) - target_time))

        oldest = get_closest(target_old, images)
        mid = get_closest(target_mid, images)
        
        selected_images = [oldest, mid, newest]
        
        # Ensure they are distinct images to prevent checking the same image 3 times
        if len(set(selected_images)) == 3:
            log.info(f"Starting inactive posture inference across {interval} seconds...")
            start_time = time.time()
            result = process_inactive_sequence(model, [str(img) for img in selected_images])
            elapsed_time = time.time() - start_time
            
            log.info(f"inactive_posture_inference_time: {elapsed_time:.2f}s")
            log.info(f"inactive_posture_result: {result}")
            
            if "RESULT: YES" in result.upper():
                write_event("INACTIVE_POSTURE_DETECTED", f"Detected across {selected_images[0].name}, {selected_images[1].name}, {selected_images[2].name}")

@app.post("/detection")
async def detection_req(
    request: Request,
    background_tasks: BackgroundTasks, 
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

    filename = IMAGE_DIR / f"capture_{int(time.time() * 1000)}.{extension}"
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
    response_payload = await act(client_host, filename, resident_in_picture, multiple_people, status, greeting)

    background_tasks.add_task(analyze_inactive_posture)

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

if __name__ == "__main__":
    host = os.environ.get("THINKING_HOST", None)
    port_str = os.environ.get("THINKING_PORT", None)

    if not host or not port_str:
        log.error("THINKING_HOST and THINKING_PORT must be set in config.env")
        exit(1)

    port = int(port_str)

    log.info(f"Starting Thinking image endpoint on http://{host}:{port}/detection (FastAPI)")
    uvicorn.run(app, host=host, port=port)