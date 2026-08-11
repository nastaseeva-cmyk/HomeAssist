# Adaptive home assistant for people in need (sick, post-op, elder etc.)

An adaptive, AI based home assistant that monitors people in need living alone. Capabilities:
- complex camera image context analysis (move beyond basic computer vision object detection / image classification)
- voice interaction - speak/listen to the subject
- daily routine analysis and tracking 
- complex alerting in case of pottential danger, providing context
- uses small offline models to ensure cost-effectiveness and confidentiality

## Overview
This research project provides a digitalization framework for managing growing vulnerable populations. The work aligns with my involvement in CiTyInnoHub 2.0, an initiative dedicated to advancing digital transformation, AI education, and technology coaching for startups and state institutions.

The project introduces an adaptive home assistant for vulnerable people living alone, utilizing a phone or tablet. Multiple devices can be deployed within the same household for comprehensive coverage. The software dynamically adjusts its monitoring based on the subject's daily routine to accurately detect anomalies. A microservices-based backend, utilizing exclusively offline models, ensures cost-effectiveness, low latency, and strict data confidentiality.

The Proof of Concept (POC) backend is designed to run on a laptop equipped with an RTX 4080 GPU (12GB VRAM).

## Architecture & Repository Structure
This is a mono-repo containing all required components:

* **`Mobile`**
  Models: MLKit FaceDetection & efficientdet.tflite (person)
  A Kotlin application for Android devices. 
  Executes edge-level object detection models on real-time video to filter for relevant frames. 
  Draws a dynamic basic friendly face - eyes are following face or person, mouth simulate speaking.
  Validated frames are transmitted to the Thinking endpoint for advanced, multimodal context analysis. 
  Thinking endpoint analyse the picture and decide - either calls TTS and retrieves url of resulting audio or just replies conclusions.
* **`Speaking`**
  Port: 9000
  Model: k2-fsa/OmniVoice
  A Python microservice running a Text-to-Speech (TTS) model. It exposes a REST endpoint that receives text strings, generates synthesized audio, and streams it back to the caller for immediate playback.
* **`Thinking`**
  Port: 7000
  Model: lmstudio/gemma-4-E4B-it-Q4_K_M.gguf (quantized Google Gemma 4)
  A Python microservice running a multimodal LLM, acting as the system's central processing unit. It exposes a REST endpoint called by the peripheral services (Hearing, ClientApp). It synthesizes context, triggers alerts, and commands the Speaking service.
* **`Hearing`** 
  Port: 8000
  Model: openai/whisper-large-v3 (via fast-whisper library)
  A Python microservice running a Speech-to-Text (STT) model. It ingests an audio stream via WebSocket and outputs transcribed text and language identification back to the Thinking service.
