import base64
from llama_cpp import Llama
from prompts import IMAGE_PROMPT  
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

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Image:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    {"type": "text", "text": IMAGE_PROMPT}                ]
            }
        ],
        temperature=0.1,
        response_format=None
    )

    return response["choices"][0]["message"]["content"]
