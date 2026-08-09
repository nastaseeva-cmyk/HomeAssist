import base64
from llama_cpp import Llama
from prompts import IMAGE_PROMPT  
from llama_cpp.llama_chat_format import Gemma4ChatHandler 


model_path = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
mmproj_path = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/mmproj-gemma-4-E4B-it-BF16.gguf"
REFERENCE_IMAGE_PATH = "subject/virgil.jpeg"

chat_handler = Gemma4ChatHandler(clip_model_path=mmproj_path)

def load_model():
    return Llama(
        model_path=model_path,
        chat_handler=chat_handler,
        n_gpu_layers=-1, 
        n_ctx=2096,
        verbose=False
    )

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def process_image(llm, image_path, json_response=True):
    base64_image = encode_image(image_path)
    base64_ref_image = encode_image(REFERENCE_IMAGE_PATH)

    if not json_response:
        response_format = None
    else:
        response_format = {
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["OK", "DANGER", "NOT_DETECTED"],
                        "description": "The status of the person based on the image analysis."
                    },                    
                    "resident_in_picture": {
                        "type": "string",
                        "enum": ["YES", "NO"],
                        "description": "Person in the image resembles the reference image."
                    },                    
                    "greeting": {
                        "type": "string",
                        "description": "A greeting message for the person in the image."
                    },                    
                    "description": {
                        "type": "string",
                        "description": "A concise description of the situation based on the image analysis."        
                    }          
                },     
                "required": ["status", "resident_in_picture", "greeting", "description"]
            }
        }

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Reference image:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_ref_image}"}},
                    {"type": "text", "text": "Target image (Camera):"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    {"type": "text", "text": IMAGE_PROMPT}                ]
            }
        ],
        temperature=0.7,
        # max_tokens=256,
        response_format=response_format        
    )

    return response["choices"][0]["message"]["content"]
