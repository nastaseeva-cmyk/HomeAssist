from journal import write_conversation
from calls import tts

def act(environ, filename, resident_in_picture, multiple_people, status, spoken_message):

    # SITUATION: Resident is in the picture, status is "ok", and there is only one person detected
    # ACTION: Generate a conversation with corresponding TTS and return the audio URL along with the inference results
    if resident_in_picture == "yes" and multiple_people == "no" and status == "ok":
        text_to_speak = spoken_message
        write_conversation(text_to_speak)
        audio_url = tts(environ, text_to_speak)
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
        audio_url = tts(environ, text_to_speak)
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
    