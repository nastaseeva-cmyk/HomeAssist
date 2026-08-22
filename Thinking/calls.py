import os
import httpx
from pathlib import Path
from logger import get_logger


log = get_logger("thinking")

async def tts(client_host, text_to_speak):
    audio_url = None
    tts_req_url = f"http://{os.environ.get('TTS_HOST', None)}:{os.environ.get('TTS_PORT', None)}/tts"
    tts_payload = {"text": text_to_speak}
    tts_port = os.environ.get("TTS_PORT", None)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(tts_req_url, json=tts_payload, timeout=60.0)
            response.raise_for_status()
            tts_resp_data = response.json()
            
            if tts_resp_data.get("status") == "ok":
                audio_file_name = Path(tts_resp_data["file"]).name
                
                ip_only = client_host.split(":")[0] 
                
                audio_url = f"http://{ip_only}:{tts_port}/audio/{audio_file_name}"
    except Exception as e:
        log.error(f"Error calling TTS service: {tts_req_url} - {e}")
    
    return audio_url