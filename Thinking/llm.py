import re
import json
import base64
from llama_cpp import Llama
from prompts import get_image_prompt  
from llama_cpp.llama_chat_format import Gemma4ChatHandler 


model_path = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
mmproj_path = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/mmproj-gemma-4-E4B-it-BF16.gguf"

chat_handler = Gemma4ChatHandler(clip_model_path=mmproj_path)

def load_model():
    return Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_gpu_layers=-1, 
        n_ctx=4096,
        verbose=False
    )

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image(llm, image_path):
    base64_image = encode_image(image_path)
    resident_base64_image = encode_image("subject/virgil.jpeg")

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
    print(f"Inference result raw: {response_str}") 

    json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
    if json_match:
        clean_json_str = json_match.group(0)
    else:
        clean_json_str = response_str

    try:
        raw_json = json.loads(clean_json_str)
        inference_json = {k: v for k, v in raw_json.items()}
    except json.JSONDecodeError:
        print("Error parsing JSON response.")
        inference_json = {}


    resident_in_picture = inference_json.get("resident_in_picture", "?")
    multiple_people = inference_json.get("multiple_people", "?")
    status = inference_json.get("status", "?")
    spoken_message = inference_json.get("spoken_message", "?")

    return resident_in_picture, multiple_people, status, spoken_message
