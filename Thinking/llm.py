import re
import os
import json
import base64
import threading
from pathlib import Path
from llama_cpp import Llama
from logger import get_logger

llm_lock = threading.Lock()
from prompts import get_image_prompt, get_inactive_posture_prompt, get_stt_prompt
from llama_cpp.llama_chat_format import Gemma4ChatHandler 


log = get_logger("thinking")

def load_model():
    clip_model_path = os.environ.get("LLM_MMPROJ_PATH", None)
    model_path = os.environ.get("LLM_MODEL_PATH", None)

    if not clip_model_path or not model_path:
        log.error("LLM model paths are not set in environment variables.")
        raise ValueError("LLM model paths are not set in environment variables.")

    chat_handler = Gemma4ChatHandler(clip_model_path=clip_model_path) 
    return Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        # n_gpu_layers=25, 
        n_gpu_layers=-1, 
        n_ctx=4096,
        verbose=False
    )

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image(llm, image_path):
    base64_image = encode_image(image_path)

    resident_image_path = os.environ.get("RESIDENT_IMAGE_PICTURE", None)
    if not resident_image_path:
        log.error("Resident image path is not set in environment variables.")
        raise ValueError("Resident image path is not set in environment variables.")
    
    resident_base64_image = encode_image(Path(__file__).resolve().parent.parent / resident_image_path)

    with llm_lock:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Resident photo:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{resident_base64_image}"}},
                        {"type": "text", "text": "Camera Image:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                        {"type": "text", "text": get_image_prompt()}                ]
                }
            ],
            temperature=0.1,
            response_format=None
        )

    return response["choices"][0]["message"]["content"]

# Initially tested json enforcement but it worked slow and results were halucinated (strange enough...). Reverted to old-school regex extraction and json parsing.
def parse_json_response(response_str):
    log.info(f"Inference result raw: {response_str}") 

    json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
    if json_match:
        clean_json_str = json_match.group(0)
    else:
        clean_json_str = response_str

    try:
        raw_json = json.loads(clean_json_str)
        inference_json = {k: v for k, v in raw_json.items()}
    except json.JSONDecodeError:
        log.error(f"Error parsing JSON response")
        inference_json = {}


    resident_in_picture = inference_json.get("resident_in_picture", "?")
    multiple_people = inference_json.get("multiple_people", "?")
    status = inference_json.get("status", "?")
    spoken_message = inference_json.get("spoken_message", "?")

    return resident_in_picture, multiple_people, status, spoken_message

def process_inactive_sequence(llm, image_paths):
    content = []

    log.info(f"Inactivity check on: {image_paths}")
    
    for i, path in enumerate(image_paths):
        base64_image = encode_image(path)
        content.append({"type": "text", "text": f"Image {i+1}:"})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

    content.append({
        "type": "text", 
        "text": get_inactive_posture_prompt()
        })

    with llm_lock:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            temperature=0.1,
            response_format=None
        )

    return response["choices"][0]["message"]["content"]

def process_stt_text(llm, text):
    prompt = get_stt_prompt(text)
    
    with llm_lock:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            response_format=None
        )
    
    response_str = response["choices"][0]["message"]["content"]
    
    log.info(f"STT Inference raw: {response_str}") 

    json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
    if json_match:
        clean_json_str = json_match.group(0)
    else:
        clean_json_str = response_str

    try:
        raw_json = json.loads(clean_json_str)
        inference_json = {k: v for k, v in raw_json.items()}
    except json.JSONDecodeError:
        log.error(f"Error parsing STT JSON response")
        inference_json = {}

    is_addressing = inference_json.get("is_addressing_assistant", "no")
    status_update = inference_json.get("status_update", "none")
    spoken_response = inference_json.get("spoken_response", "")

    return is_addressing, status_update, spoken_response
