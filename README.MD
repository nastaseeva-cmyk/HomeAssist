# Adaptive home assistant for people in need (sick, post-op, elder etc.)

An adaptive, AI-based home assistant that monitors people in need living alone. Capabilities:
- complex camera image context analysis (moving beyond basic computer vision object detection / image classification)
- voice interaction - speak/listen to the subject
- daily routine analysis and tracking using a custom model
- complex alerting in case of potential danger, providing context
- intended to be used on EDGE devices, uses quantized, local models, no internet connection required, full confidentiality

## Overview
This research project provides a digitalization framework for managing growing vulnerable populations. The work aligns with my involvement in CiTyInnoHub 2.0, an initiative dedicated to advancing digital transformation, AI education, and technology coaching for startups and state institutions.

The project introduces an adaptive home assistant for vulnerable people living alone, utilizing a phone or tablet. Multiple devices can be deployed within the same household for comprehensive coverage. The software dynamically adjusts its monitoring based on the subject's daily routine to accurately detect anomalies. A microservices-based backend, utilizing exclusively offline models, ensures cost-effectiveness, low latency, and strict data confidentiality.

The Proof of Concept (POC) backend is designed to run on a laptop equipped with an RTX 4080 GPU (12GB VRAM).

## Architecture & Repository Structure
This is a mono-repo containing all required components:

* **`Mobile`**<br>
  Models: MLKit FaceDetection + efficientdet.tflite (person detection) / Silero VAD for voice detection using microphone<br>
  Kotlin application for Android devices. 
  Executes edge-level object detection models on real-time video to filter for relevant frames. 
  Detects voice and sends it to Hearing service for TTS.
  Draws a dynamic basic friendly face - eyes are following the face or person, mouth simulates speaking.
  Validated frames are transmitted to the Thinking endpoint for advanced, multimodal context analysis. 
  The Thinking endpoint analyzes the picture and decides: it either calls the TTS service to retrieve the generated audio URL, or directly replies with its analytical conclusions.
  
* **`Speaking`**<br>
  Model: k2-fsa/OmniVoice<br>
  A Python microservice running a Text-to-Speech (TTS) model. It exposes a REST endpoint that receives text strings, generates synthesized audio, and streams it back to the caller for immediate playback.
  
* **`Thinking`**<br>
  Model: unsloth/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q3_K_S.gguf (quantized Google Gemma 4)<br>
  A Python microservice running a multimodal LLM, acting as the system's central processing unit. It exposes a REST endpoint called by the peripheral services (Hearing, ClientApp). It synthesizes context, triggers alerts, and commands the Speaking service.
  
* **`Hearing`**<br>
  Model: fast-whisper/whisper-large-v3<br>
  A Python microservice running a Speech-to-Text (STT) model. Gets voice audio from Mobile and calls Thinking service with detected language and text for further processing.

---

## Configuration

Create the configuration files in their respective directories before starting the containers.

**`Thinking/config.env`**
```env
THINKING_HOST = "0.0.0.0"
THINKING_PORT = 7000
LLM_MODEL_PATH = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
LLM_MMPROJ_PATH = "/etc/models/lmstudio-community/gemma-4-E4B-it-GGUF/mmproj-gemma-4-E4B-it-BF16.gguf"
RESIDENT_IMAGE_PICTURE = "SharedData/resident/yourresidentpic.jpeg"
TTS_HOST = "speaking-service"
TTS_PORT = 9001
THINKING_DB = "SharedData/db/thinking.db"
RESIDENT_LANGUAGE = "en"
INACTIVITY_INTERVAL_SECONDS = 7200
HOMEASSISTANT_NAME = "Assistant"
```

**`Speaking/config.env`**
```env
SPEAKING_HOST = "0.0.0.0"
SPEAKING_PORT = 9001
TTS_MODEL_PATH = "/etc/models/omnivoice"
RESIDENT_LANGUAGE = "en"
```

**`Hearing/config.env`**
```env
HEARING_HOST = "0.0.0.0"
HEARING_PORT = 8000
THINKING_STT_HOST = "thinking-service"
THINKING_STT_PORT = 7000
```

---

## Build & Run

To ensure the containers can communicate with each other (e.g., Thinking reaching Speaking via the `TTS_HOST` name, Hearing reaching Thinking via the `THINKING_STT_HOST`) a dedicated Docker network will be used.
If you plan using docker-compose - put all the configs into a single config.env in the SharedData folder. If you run locally - you can go for dedicated files.

### Run docker compose from the root directory of the repository (`HomeAssist`)
```bash
docker compose up --build
```
At this point, the application backend should be up and running locally. You can install the mobile app and start testing.
