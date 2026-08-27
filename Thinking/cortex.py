import os
import time
import asyncio
from calls import tts
from pathlib import Path
from logger import get_logger
from llm import process_inactive_sequence, process_routine_analysis
from db import get_seconds_since_last_conversation, write_routine_log, write_event, write_conversation, get_all_historical_timestamps, get_hours_since_resident_last_seen, get_distinct_locations, get_hours_since_resident_last_seen_at, get_all_historical_timestamps_for, update_current_status


log = get_logger("thinking")

IMAGE_DIR = Path(__file__).resolve().parent.parent / "SharedData/images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

async def analyze_inactive_posture(model, location="Unknown"):
    interval = int(os.environ.get("INACTIVITY_INTERVAL_SECONDS", 7200))
    
    location_dir = IMAGE_DIR / location
    if not location_dir.exists():
        return
    
    images = sorted(location_dir.glob("capture_*.jpg"), key=os.path.getmtime, reverse=True)
    
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
            log.info(f"Starting inactive posture inference for '{location}' across {interval} seconds...")
            start_time = time.time()
            result = await asyncio.to_thread(process_inactive_sequence, model, [str(img) for img in selected_images])
            elapsed_time = time.time() - start_time
            
            log.info(f"inactive_posture_inference_time: {elapsed_time:.2f}s (location: {location})")
            log.info(f"inactive_posture_result: {result}")
            
            if "RESULT: YES" in result.upper():
                write_event("INACTIVE_POSTURE_DETECTED", f"Detected at '{location}' across {selected_images[0].name}, {selected_images[1].name}, {selected_images[2].name}")
                update_current_status(location, "danger", "inactive_posture", "Dangerous inactive posture detected")
            else:
                update_current_status(location, "ok", "inactive_posture", "Posture check passed")

async def act(client_host, filename, resident_in_picture, multiple_people, status, greeting, location="Unknown"):
    log.info(f"Resident: {resident_in_picture}, Multiple: {multiple_people}, Status: {status}")
    write_routine_log(resident_in_picture, multiple_people, status, location)
    update_current_status(location, status, "detection", greeting)

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

        text_to_speak = greeting
        write_conversation(text_to_speak)
        audio_url = await tts(client_host, text_to_speak)

        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
                "spoken_message": greeting,
            },
            "audio_url": audio_url
        }


    # SITUATION: Danger detected (status is "danger")
    # ACTION: Generate a conversation with corresponding TTS and return the audio URL along with the inference results
    elif status == "danger":
        text_to_speak = greeting
        write_conversation(text_to_speak)
        audio_url = await tts(client_host, text_to_speak)

        return {
            "status": "saved", 
            "file": str(filename),
            "inference": {
                "resident_in_picture": resident_in_picture,
                "multiple_people": multiple_people,
                "status": status,
                "spoken_message": greeting,
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

async def check_routine_anomaly_for(model, location):
    import asyncio
    import datetime
    from anomaly_model import predict_anomaly
    
    now = datetime.datetime.now()
    current_hour = now.hour
    
    if current_hour >= 23 or current_hour < 7:
        return
        
    hours_missing = get_hours_since_resident_last_seen_at(location)
    
    if hours_missing < 0:
        log.info(f"Resident never seen at '{location}'. Skipping anomaly check.")
        return
        
    if hours_missing < 2.0:
        log.info(f"Resident missing from '{location}' for {hours_missing:.1f}h. Below 2h threshold.")
        update_current_status(location, "ok", "routine_anomaly", "Resident seen recently")
        return
        
    historical_datetimes = get_all_historical_timestamps_for(location)
    
    is_anomaly = False
    
    if historical_datetimes:
        first_seen = min(historical_datetimes)
        days_of_data = (now - first_seen).total_seconds() / (3600 * 24)
        
        if days_of_data >= 3.0:
            is_anomaly = predict_anomaly(historical_datetimes, now, hours_missing)
        else:
            if hours_missing > 8.0:
                is_anomaly = True
                
    if not is_anomaly:
        update_current_status(location, "ok", "routine_anomaly", "No anomaly detected")
        return
        
    log.info(f"ANOMALY TRIGGERED for '{location}'. Generating TTS message via LLM...")
    start_time = time.time()
    spoken_message = await asyncio.to_thread(process_routine_analysis, model, hours_missing, location)
    elapsed_time = time.time() - start_time
    
    log.info(f"TTS_generation_time: {elapsed_time:.2f}s, location: {location}, message: {spoken_message}")
    
    if spoken_message:
        write_event("ROUTINE_ANOMALY_DETECTED", f"Resident missing from '{location}' for {hours_missing:.1f}h. Message: {spoken_message}")
        write_conversation(spoken_message)
        client_host = os.environ.get("THINKING_HOST", "127.0.0.1")
        audio_url = await tts(client_host, spoken_message)
        update_current_status(location, "danger", "routine_anomaly",
                              f"Missing for {hours_missing:.1f}h", audio_url)

async def check_routine_anomaly(model):
    import datetime
    
    log.info("Starting per-location routine anomaly check...")
    
    now = datetime.datetime.now()
    current_hour = now.hour
    
    if current_hour >= 23 or current_hour < 7:
        log.info("Night time active. Ignoring routine checks.")
        return
    
    locations = get_distinct_locations()
    
    if not locations:
        log.info("No known locations yet. Skipping anomaly check.")
        return
    
    log.info(f"Checking anomaly for {len(locations)} location(s): {locations}")
    
    for location in locations:
        try:
            await check_routine_anomaly_for(model, location)
        except Exception as e:
            log.error(f"Error in routine anomaly check for '{location}': {e}")