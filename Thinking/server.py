from logger import get_logger
log = get_logger("thinking")

import os
import time
import json
from db import init_db
from cortex import act
from pathlib import Path
from dotenv import load_dotenv
from wsgiref.simple_server import make_server
from llm import load_model, process_image, parse_json_response


load_dotenv("config.env")

IMAGE_DIR = Path(__file__).resolve().parent.parent / "SharedData/images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

init_db()
model = load_model()

def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")

    if path != "/detection" or method != "POST":
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Endpoint not found"}).encode("utf-8")]    
    
    try:
        content_length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        log.error("Invalid CONTENT_LENGTH header")
        content_length = 0

    if content_length <= 0:
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Missing image data"}).encode("utf-8")]

    image_bytes = environ["wsgi.input"].read(content_length)
    content_type = environ.get("CONTENT_TYPE", "image/jpeg")
    if "png" in content_type:
        extension = "png"
    elif "jpeg" in content_type or "jpg" in content_type:
        extension = "jpg"
    else:
        extension = "bin"

    filename = IMAGE_DIR / f"capture_{int(time.time() * 1000)}.{extension}"
    filename.write_bytes(image_bytes)

    response_payload = {"status": "saved", "file": str(filename)}

    
    # Process the image with the LLM
    inference_result_str = process_image(model, str(filename))

    # Process inference result
    resident_in_picture, multiple_people, status, greeting = parse_json_response(inference_result_str)

    # Act based on the inference result
    response_payload = act(environ, filename, resident_in_picture, multiple_people, status, greeting)


    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(response_payload).encode("utf-8")]

if __name__ == "__main__":
    host = os.environ.get("THINKING_HOST", None)
    port = int(os.environ.get("THINKING_PORT", None))

    log.info(f"Starting Thinking image endpoint on http://{host}:{port}/detection")
    server = make_server(host, port, application)
    server.serve_forever()