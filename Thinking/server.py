import os
import time
import json
import urllib.request
from pathlib import Path
from wsgiref.simple_server import make_server
from llm import load_model, process_image

IMAGE_DIR = Path(__file__).resolve().parent / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

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
    inference_result_str = process_image(model, str(filename))

    print(f"Inference result: {inference_result_str}")

    try:
        inference_json = json.loads(inference_result_str)
    except json.JSONDecodeError:
        print("Eroare: LLM-ul nu a returnat un JSON valid.")
        inference_json = {}

    audio_url = None



    # if inference_json.get("status") == "OK":
    text_to_speak = "Status " + inference_json.get("status", "Error getting status!")
    text_to_speak += "Resident is in the picture: " + inference_json.get("resident_in_picture", "Error getting resident info!") 
    text_to_speak += "Description: " + inference_json.get("description", "Error getting the description!")

    if  inference_json.get("resident_in_picture", "Error getting resident info!") == "YES":
        text_to_speak = inference_json.get("greeting", "Error getting the greeting!")
        
    # text_to_speak = "Totul este în regulă bosulică? Ce poate eu să face pentru tine? Ha! Fraierică! Glumeam, totul e ok, nu te speria!"
    
    tts_req_url = "http://127.0.0.1:9000/tts"
    tts_payload = json.dumps({"text": text_to_speak}).encode("utf-8")
    req = urllib.request.Request(tts_req_url, data=tts_payload, headers={'Content-Type': 'application/json'})

    
    try:
        with urllib.request.urlopen(req) as response:
            tts_resp_data = json.loads(response.read().decode("utf-8"))
            
            if tts_resp_data.get("status") == "ok":
                audio_file_name = Path(tts_resp_data["file"]).name
                
                client_host = environ.get("HTTP_HOST", "127.0.0.1") 
                ip_only = client_host.split(":")[0] 
                
                audio_url = f"http://{ip_only}:9000/audio/{audio_file_name}"
    except Exception as e:
        print(f"Error calling TTS service: {e}")

    response_payload = {
        "status": "saved", 
        "file": str(filename),
        "inference": inference_result_str 
    }
    
    if audio_url:
        response_payload["audio_url"] = audio_url




    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(response_payload).encode("utf-8")]


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "7000"))
    print(f"Starting Thinking image endpoint on http://{host}:{port}/detection")
    server = make_server(host, port, application)
    server.serve_forever()
