import os
import json
import urllib.request
from pathlib import Path
from logger import get_logger


log = get_logger("hearing")

def cortex(environ, lang, text):
    cortex_req_url = f"http://{os.environ.get('CORTEX_STT_HOST', None)}:{os.environ.get('CORTEX_STT_PORT', None)}/stt"

    print(cortex_req_url)

    cortex_payload = json.dumps(
        {
            "lang": lang,
            "text": text,
        }
    ).encode("utf-8")
    req = urllib.request.Request(cortex_req_url, data=cortex_payload, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode("utf-8")
            return json.loads(response_data)
    except urllib.error.URLError as e:
        log.error(f"Error sending stt to the cortex: {e}")
        return None

    return req