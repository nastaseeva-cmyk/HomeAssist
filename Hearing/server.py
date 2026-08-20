import os
import time
import json
from pathlib import Path
from calls import cortex
from logger import get_logger
from dotenv import load_dotenv
from wsgiref.simple_server import make_server
from stt import load_model, extract_audio_bytes, transcribe_audio


log = get_logger("hearing")
load_dotenv("config.env")

AUDIO_DIR = Path(__file__).resolve().parent.parent / "SharedData/audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

model = load_model()

def application(environ, start_response):
    global model

    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")

    if path != "/stt" or method != "POST":
        log.error(f"404 Not Found: Endpoint not found: {path}")
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Endpoint not found"}).encode("utf-8")]    

    try:
        content_length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        log.error("Invalid CONTENT_LENGTH header")
        content_length = 0

    if content_length <= 0:
        log.error(f"400 Bad Request: Missing image data: {content_length}")
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Missing request body"}).encode("utf-8")]


    request_body = environ["wsgi.input"].read(content_length)
    if not request_body:
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Missing request body"}).encode("utf-8")]

    content_type = environ.get("CONTENT_TYPE", "application/json").split(";")[0]

    payload = None
    if content_type == "application/json":
        try:
            payload = json.loads(request_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None

    if "wav" in content_type:
        extension = "wav"
    else:
        log.error(f"Invalid content type: {content_type}")
        extension = "bin"

    try:
        audio_bytes = extract_audio_bytes(payload=payload, body=request_body, content_type=content_type)
    except ValueError as exc:
        log.error(f"Error extracting audio bytes: {exc}")
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": str(exc)}).encode("utf-8")]

    file_path = AUDIO_DIR / f"stt_audio_{int(time.time() * 1000)}.{extension}"
    file_path.write_bytes(audio_bytes)

    start_time = time.time()
    text, lang = transcribe_audio(audio_bytes, model=model)
    elapsed_time = time.time() - start_time
    log.info(f"stt_time: {elapsed_time:.2f}s / {lang}:{text}")
    cortex(environ, lang, text)

    start_response("200 OK", [("Content-Type", "application/json")])
    return [
        json.dumps(
            {
                "status": "ok",
                "text": text,
                "language": lang,
                "model": "large-v3",
            }
        ).encode("utf-8")
    ]


if __name__ == "__main__":
    host = os.environ.get("HEARING_HOST", None)
    port = int(os.environ.get("HEARING_PORT", None))

    log.info(f"Starting Hearing endpoint on http://{host}:{port}/detection")
    server = make_server(host, port, application)
    server.serve_forever()
