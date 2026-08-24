from calls import tts
from logger import get_logger
from db import write_conversation, get_seconds_since_last_conversation
import datetime

log = get_logger("thinking")

async def act(client_host, filename, resident_in_picture, multiple_people, status, spoken_message, person_x=None, person_y=None, face_x=None, face_y=None, person_w=None, person_h=None):
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

        log.error(f"DONE ACTING 1 {filename}")

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

        log.error(f"DONE ACTING 2 {filename}")

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
        log.error(f"DONE ACTING 3 {filename}")

        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
            },
        }

    