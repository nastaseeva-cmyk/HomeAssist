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

* **`Mobile`**
  Models: MLKit FaceDetection & efficientdet.tflite (person detection)
  A Kotlin application for Android devices. 
  Executes edge-level object detection models on real-time video to filter for relevant frames. 
  Draws a dynamic basic friendly face - eyes are following the face or person, mouth simulates speaking.
  Validated frames are transmitted to the Thinking endpoint for advanced, multimodal context analysis. 
  The Thinking endpoint analyzes the picture and decides: it either calls the TTS service to retrieve the generated audio URL, or directly replies with its analytical conclusions.
  
* **`Speaking`**
  Port: 9001
  Model: k2-fsa/OmniVoice
  A Python microservice running a Text-to-Speech (TTS) model. It exposes a REST endpoint that receives text strings, generates synthesized audio, and streams it back to the caller for immediate playback.
  
* **`Thinking`**
  Port: 7000
  Model: lmstudio/gemma-4-E4B-it-Q4_K_M.gguf (quantized Google Gemma 4)
  A Python microservice running a multimodal LLM, acting as the system's central processing unit. It exposes a REST endpoint called by the peripheral services (Hearing, ClientApp). It synthesizes context, triggers alerts, and commands the Speaking service.
  
* **`Hearing` (Work in Progress)** 
  Port: 8000
  Model: openai/whisper-large-v3 (via fast-whisper library)
  A Python microservice running a Speech-to-Text (STT) model. It ingests an audio stream via WebSocket and outputs transcribed text and language identification back to the Thinking service.

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
RESIDENT_LANGUAGE = "English"
```

**`Speaking/config.env`**
```env
SPEAKING_HOST = "0.0.0.0"
SPEAKING_PORT = 9001
TTS_MODEL_PATH = "/etc/models/omnivoice"
RESIDENT_LANGUAGE = "en"
```

---

## Build & Run

To ensure the containers can communicate with each other (e.g., Thinking reaching Speaking via the `TTS_HOST` name), create a dedicated Docker network first.

Run these commands from the root directory of the repository (`HomeAssist`):

### 1. Create Docker Network
```bash
docker network create homeassist-net
```

### 2. Thinking Service
```bash
docker build -t homeassist-thinking ./Thinking

docker run --name thinking-service \
  --network homeassist-net \
  --gpus all \
  -p 7000:7000 \
  -v /etc/models:/etc/models \
  -v $(pwd)/SharedData:/app/SharedData \
  -v $(pwd)/Thinking/config.env:/app/Thinking/config.env \
  -d homeassist-thinking
```

### 3. Speaking Service
```bash
docker build -t homeassist-speaking ./Speaking

docker run --name speaking-service \
  --network homeassist-net \
  --gpus all \
  -p 9001:9001 \
  -v /etc/models:/etc/models \
  -v $(pwd)/SharedData:/app/SharedData \
  -v $(pwd)/Speaking/config.env:/app/Speaking/config.env \
  -d homeassist-speaking
```

At this point, the application backend should be up and running locally. You can install the mobile app and start testing.
