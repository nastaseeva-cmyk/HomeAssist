import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import json
from wsgiref.simple_server import make_server
from stt import load_model, extract_audio_bytes, transcribe_audio

model = load_model()

def application(environ, start_response):
    global model

    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "")


    if path != "/stt" or method != "POST":
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [json.dumps({"error": "Endpoint not found"}).encode("utf-8")]    


    try:
        content_length = int(environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        content_length = 0

    if content_length <= 0:
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

    try:
        audio_bytes = extract_audio_bytes(payload=payload, body=request_body, content_type=content_type)
    except ValueError as exc:
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": str(exc)}).encode("utf-8")]

    text, language = transcribe_audio(audio_bytes, model=model)

    start_response("200 OK", [("Content-Type", "application/json")])
    return [
        json.dumps(
            {
                "status": "ok",
                "text": text,
                "language": language,
                "model": "large-v3",
            }
        ).encode("utf-8")
    ]


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    print(f"Starting Hearing STT endpoint on http://{host}:{port}/stt")
    server = make_server(host, port, application)
    server.serve_forever()
