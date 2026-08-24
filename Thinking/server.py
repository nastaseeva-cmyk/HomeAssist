import os
import time
import uvicorn
from db import init_db
from cortex import act
from pathlib import Path
from logger import get_logger
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from llm import load_model, process_image, parse_json_response


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

@app.post("/detection")
async def detection_req(
    request: Request, 
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

    log.error(f"IMAGE RECEIVED:{filename}")

    # Process the image with the LLM
    start_time = time.time()
    inference_result_str = process_image(model, str(filename))
    elapsed_time = time.time() - start_time        
    log.info(f"llm_time: {elapsed_time:.2f}s")

    log.error(f"IMAGE PROCESSED BY LLM:{filename}")

    # Process inference result
    resident_in_picture, multiple_people, status, greeting = parse_json_response(inference_result_str)

    log.error(f"JSON PARSED:{filename}")

    # Act based on the inference result
    client_host = request.headers.get("host", "127.0.0.1")
    response_payload = await act(client_host, filename, resident_in_picture, multiple_people, status, greeting)


    return response_payload

@app.post("/stt")
async def stt_req(payload: STTRequest):
    log.info(f"Incoming stt - lang: {payload.lang}, text: {payload.text}")
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