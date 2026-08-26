import os
import httpx
from logger import get_logger


log = get_logger("hearing")

async def cortex(lang, text, location="Unknown"):
    cortex_req_url = f"http://{os.environ.get('CORTEX_STT_HOST', None)}:{os.environ.get('CORTEX_STT_PORT', None)}/stt"

    cortex_payload = {
        "lang": lang,
        "text": text,
        "location": location
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(cortex_req_url, json=cortex_payload, timeout=60.0)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        log.error(f"Error sending stt to the cortex: {e}")
        return None