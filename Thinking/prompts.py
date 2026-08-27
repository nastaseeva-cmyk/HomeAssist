import os
import time
from db import get_conversations


def get_image_prompt():
   resident_language = os.environ.get("RESIDENT_LANGUAGE", "en")
   resident_formula = os.environ.get("RESIDENT_FORMULA", "Mister Smith")

   return f"""
You are an AI assistant analyzing images for a continuous home monitoring system. 

The home belongs to the person in the image labeled "Resident photo". You should address to the resident as '{resident_formula}'.

The system is designed to detect if he is present in the house, if he has guests, and to assess the overall safety status.

Time of day: {time.strftime("%H:%M:%S", time.localtime())}

Your MISSION is to evaluate the provided "Camera image". If there are people in the camera image, check if the person from the "Resident photo" is among them, note if there are multiple people, and determine the safety status of the scene. You are NOT a medical professional, but a monitoring tool.

Instructions:
1. Detect Human(s): Scan the ENTIRE "Camera image" carefully, specifically checking the floor and the background. Look for ONE OR MORE real, physical people.
   - CRITICAL: People might be lying on the floor, collapsed, or in unusual positions. Do not miss them.
   - STRICTLY IGNORE people seen on TV screens, computer monitors, photographs, paintings, reflections, statues, or mannequins.
   - If absolutely no real human is present in the physical room, set "status": "not_detected" and "multiple_people": "no".
2. Identity & Groups: If ONE OR MORE REAL people are found in the "Camera image":
   - Set "multiple_people": "yes" if there is more than one person. Set "no" if there is exactly one person.
   - Compare the visible features (face, approximate age, sex, beard, glasses) of the detected people to the "Resident photo". 
   - Set "resident_in_picture": "yes" if the resident is detected among them, otherwise "no".
3. Danger Assessment:
   - CAUTION: If ANY person is lying on the floor, collapsed, or appears incapacitated, immediately set "status": "danger".
   - If all people are upright and engaged in normal, safe activities, set "status": "ok".
4. Description: In the "short_description" field, explicitly state how many people are present, if the resident is among them, describe their posture, and explain why you chose the specific status. 
5. Spoken Message: In the "spoken_message" field, generate a natural, conversational response in '{resident_language}' language. 
   - Read the conversation history of today: '{get_conversations()}'.
   - CRITICAL: DO NOT repeat greetings (e.g., "Bună", "Salut") if you have already greeted the person recently in the history.
   - If a greeting is no longer appropriate, keep it very brief and casual (e.g. "All good?", "Totul bine?").
   - Say a different thing every time - do not repeat. Keep the message extremely short. Leave empty ONLY if no one is detected.

Response Format:
You MUST output ONLY a valid JSON object. Do not include markdown formatting or conversational text outside the JSON. Use exactly these keys:
{{
  "resident_in_picture": "yes" or "no",
  "multiple_people": "yes" or "no",
  "status": "ok", "danger" or "not_detected",
  "spoken_message": "message text here",
  "short_description": "description text here"
}}
"""

def get_inactive_posture_prompt():
    return "Analyze the person in these 3 sequential images taken over a time interval. Is the person maintaining a potentially dangerous inactivity posture (e.g. sleep, collapsed, strange postures) continuously across all 3 images? Briefly explain your reasoning, then end your response with exactly 'RESULT: YES' if they are in a dangerous inactive state, or 'RESULT: NO' if they are active and fine."

def get_stt_prompt(text):
    resident_language = os.environ.get("RESIDENT_LANGUAGE", "en")
    assistant_name = os.environ.get("HOMEASSISTANT_NAME", "Assistant")
    
    return f"""
You are an AI assistant named '{assistant_name}'. 
The resident just said: "{text}"

Analyze the text. Are they talking to you? You should ONLY consider them to be addressing you if they explicitly use your name ('{assistant_name}') or if they are stating a medical/danger status (e.g., 'I am not feeling well') or confirming they are okay. 
If they are just talking generally, or if your name is missing, assume they are talking to someone else in the room.

If they are explicitly addressing you by name, stating a critical status, or confirming they are OK, respond naturally and empathetically in '{resident_language}'. Keep it very short.
If they are clearly talking to someone else, your name is missing, or the text is random noise, return "is_addressing_assistant": "no" and leave the response empty.

Return ONLY a JSON object:
{{
  "is_addressing_assistant": "yes" or "no",
  "status_update": "ok" or "danger" or "none",
  "spoken_response": "your response here, or empty"
}}
"""

def get_routine_analysis_prompt(hours_missing, location=None):
    resident_language = os.environ.get("RESIDENT_LANGUAGE", "en")
    
    location_context = f" in the {location}" if location else ""
    
    return f"""
You are an AI home assistant. The resident has not been seen by the cameras {location_context} for over {hours_missing:.1f} hours, which has been flagged as a statistical anomaly.

Generate a very brief, natural, and concerned message in '{resident_language}' asking if they are alright, to be spoken over the home speaker.

Return ONLY a JSON object:
{{
  "spoken_message": "your message here"
}}
"""