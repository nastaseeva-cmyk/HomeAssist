from logger import get_logger
log = get_logger("thinking")

import os
import json
import urllib.request
from pathlib import Path


def tts(environ, text_to_speak):
    audio_url = None
    tts_req_url = f"http://{os.environ.get('TTS_HOST', None)}:{os.environ.get('TTS_PORT', None)}/tts"
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
        log.error(f"Error calling TTS service: {e}")
    
    return audio_url