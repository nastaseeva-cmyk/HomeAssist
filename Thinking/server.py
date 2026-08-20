import os
import time
import json
from db import init_db
from cortex import act
from pathlib import Path
from logger import get_logger
from dotenv import load_dotenv
from wsgiref.simple_server import make_server
from llm import load_model, process_image, parse_json_response


log = get_logger("thinking")
load_dotenv("config.env")

IMAGE_DIR = Path(__file__).resolve().parent.parent / "SharedData/images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

init_db()
model = load_model()

# /detection - upload image for LLM context analysis
def detectionReq(environ, start_response):
    try:
        content_length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        log.error(f"Invalid CONTENT_LENGTH header")
        content_length = 0

    if content_length <= 0:
        log.error(f"400 Bad Request: Missing image data: {content_length}")
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
    start_time = time.time()
    inference_result_str = process_image(model, str(filename))
    elapsed_time = time.time() - start_time        
    log.info(f"llm_time: {elapsed_time:.2f}s")

    # Process inference result
    resident_in_picture, multiple_people, status, greeting = parse_json_response(inference_result_str)

    # Act based on the inference result
    response_payload = act(environ, filename, resident_in_picture, multiple_people, status, greeting)

    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(response_payload).encode("utf-8")]

# /stt - incoming STT
def sttReq(environ, start_response):
    try:
        content_length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        log.error(f"Invalid CONTENT_LENGTH header")
        content_length = 0

    if content_length <= 0:
        log.error("400 Bad Request: Missing request body in /stt")
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Missing request body"}).encode("utf-8")]

    request_body = environ["wsgi.input"].read(content_length)

    try:
        payload = json.loads(request_body.decode("utf-8"))        
        lang = payload.get("lang", "")
        text = payload.get("text", "")
        log.info(f"Incoming stt - lang: {lang}, text: {text}")
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        log.error(f"400 Bad Request: Invalid JSON payload - {e}")
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Invalid JSON payload"}).encode("utf-8")]
    
    response_payload = {"status": "done", "lang": lang, "text": text}
    
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(response_payload).encode("utf-8")]

def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")

    if path == "/detection" and method == "POST":
        return detectionReq(environ, start_response)
    elif path == "/stt" and method == "POST":
        return sttReq(environ, start_response)
    else:
        log.error(f"404 Not Found: Endpoint not found: {path}")
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Endpoint not found"}).encode("utf-8")]    
    

if __name__ == "__main__":
    host = os.environ.get("THINKING_HOST", None)
    port_str = os.environ.get("THINKING_PORT", None)

    if not host or not port_str:
        log.error("THINKING_HOST and THINKING_PORT must be set in config.env")
        exit(1)

    port = int(port_str)

    log.info(f"Starting Thinking image endpoint on http://{host}:{port}/detection")
    server = make_server(host, port, application)
    server.serve_forever()