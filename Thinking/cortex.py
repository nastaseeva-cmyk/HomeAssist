import os
import time
from calls import tts
from pathlib import Path
from logger import get_logger
from llm import process_inactive_sequence
from db import write_conversation, get_seconds_since_last_conversation, write_routine_log, write_event, write_conversation


log = get_logger("thinking")

IMAGE_DIR = Path(__file__).resolve().parent.parent / "SharedData/images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

def analyze_inactive_posture():
    interval = int(os.environ.get("INACTIVITY_INTERVAL_SECONDS", 7200))
    images = sorted(IMAGE_DIR.glob("capture_*.jpg"), key=os.path.getmtime, reverse=True)
    
    if len(images) >= 3:
        newest = images[0]
        newest_time = os.path.getmtime(newest)

        target_mid = newest_time - (interval / 2)
        target_old = newest_time - interval

        def get_closest(target_time, img_list):
            return min(img_list, key=lambda x: abs(os.path.getmtime(x) - target_time))

        oldest = get_closest(target_old, images)
        mid = get_closest(target_mid, images)
        
        selected_images = [oldest, mid, newest]
        
        # Ensure they are distinct images to prevent checking the same image 3 times
        if len(set(selected_images)) == 3:
            log.info(f"Starting inactive posture inference across {interval} seconds...")
            start_time = time.time()
            result = process_inactive_sequence(model, [str(img) for img in selected_images])
            elapsed_time = time.time() - start_time
            
            log.info(f"inactive_posture_inference_time: {elapsed_time:.2f}s")
            log.info(f"inactive_posture_result: {result}")
            
            if "RESULT: YES" in result.upper():
                write_event("INACTIVE_POSTURE_DETECTED", f"Detected across {selected_images[0].name}, {selected_images[1].name}, {selected_images[2].name}")

async def act(client_host, filename, resident_in_picture, multiple_people, status, spoken_message):
    write_routine_log(resident_in_picture, multiple_people, status)

    # SITUATION: Resident is in the picture, status is "ok", and there is only one person detected
    # ACTION: Generate a conversation with corresponding TTS and return the audio URL along with the inference results
    if resident_in_picture == "yes" and multiple_people == "no" and status == "ok":
        seconds_passed = get_seconds_since_last_conversation()
        
        # Only speak if it has been more than 1 hour (3600 seconds) since the last interaction
        if seconds_passed < 3600:
            return {
                "status": "saved", 
                "file": str(filename),
                "inference": {
                    "resident_in_picture": resident_in_picture,
                    "multiple_people": multiple_people,
                    "status": status,
                    "spoken_message": "Skipped TTS (1 hour cooldown active)",
                },
            }

        text_to_speak = spoken_message
        write_conversation(text_to_speak)
        audio_url = await tts(client_host, text_to_speak)

        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
                "spoken_message": spoken_message,
            },
            "audio_url": audio_url
        }


    # SITUATION: Danger detected (status is "danger")
    # ACTION: Generate a conversation with corresponding TTS and return the audio URL along with the inference results
    elif status == "danger":
        text_to_speak = spoken_message
        write_conversation(text_to_speak)
        audio_url = await tts(client_host, text_to_speak)

        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
                "spoken_message": spoken_message,
            },
            "audio_url": audio_url
            
        }
    
    # SITUATION: No danger detected, resident not in picture, or multiple people detected
    # ACTION: Return the inference results without generating TTS
    else:
        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
            },
        }

    