import os
from llm import load_model, process_image

model = load_model()

print("\n\n\nMODEL LOADED\n\n\n")

with open("log.txt", "w") as log_file:
    for file in os.listdir("images"):
        if file.endswith(".jpg") or file.endswith(".png"):
            image_path = os.path.join("images", file)
            result = process_image(model, image_path)
            log_file.write(f"\n\n\nProcessing {image_path}: {result}\n")  