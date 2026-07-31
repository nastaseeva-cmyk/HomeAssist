import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import json
from pathlib import Path
from tts import load_model, generate_speech
from wsgiref.simple_server import make_server

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

model = load_model()

def application(environ, start_response):
    global model

    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")

    if path == "/":
        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps({"status": "ready", "endpoint": "/tts"}).encode("utf-8")]

    if path == "/tts" and method == "POST":
        try:
            content_length = int(environ.get("CONTENT_LENGTH", "0"))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [json.dumps({"error": "Missing request body"}).encode("utf-8")]

        request_body = environ["wsgi.input"].read(content_length).decode("utf-8")
        try:
            payload = json.loads(request_body)
        except json.JSONDecodeError:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [json.dumps({"error": "Request body must be valid JSON"}).encode("utf-8")]

        text = payload.get("text", "")
        if not isinstance(text, str) or not text.strip():
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [json.dumps({"error": "Field 'text' must be a non-empty string"}).encode("utf-8")]

        output_path = generate_speech(text, model)
        scheme = environ.get("wsgi.url_scheme", "http")
        host = environ.get("HTTP_HOST") or f"{environ.get('SERVER_NAME', '127.0.0.1')}:{environ.get('SERVER_PORT', '8000')}"
        audio_url = f"{scheme}://{host}/audio/{Path(output_path).name}"

        start_response("200 OK", [("Content-Type", "application/json")])
        return [
            json.dumps(
                {
                    "status": "ok",
                    "audio_url": audio_url,
                    "download_url": audio_url,
                    "file": output_path,
                }
            ).encode("utf-8")
        ]

    if path.startswith("/audio/") and method == "GET":
        filename = path.split("/", 2)[-1]
        audio_path = AUDIO_DIR / filename
        if audio_path.exists() and audio_path.is_file():
            with audio_path.open("rb") as handle:
                audio_bytes = handle.read()
            start_response("200 OK", [("Content-Type", "audio/wav"), ("Content-Disposition", f"attachment; filename={filename}")])
            return [audio_bytes]

        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Audio file not found"}).encode("utf-8")]

    start_response("404 Not Found", [("Content-Type", "application/json")])
    return [json.dumps({"error": "Endpoint not found"}).encode("utf-8")]


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 9000
    print(f"Starting Speaking TTS endpoint on http://{host}:{port}/tts")
    server = make_server(host, port, application)
    server.serve_forever()
