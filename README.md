# Auralis Studio

Auralis Studio is a full-stack product MVP for AI-assisted music ideation. It gives users a single experience for:

- describing a soundtrack in text,
- dictating voice commands,
- recording or uploading a sung motif/reference,
- generating an instrumental draft without storing the generated music locally,
- reviewing playback, recommendations, and feedback from one product UI.

## What changed from the original starter

This repo is no longer just a thin FastAPI scaffold with a test form. It now includes:

- a product-style dashboard UI,
- a richer generation API contract,
- in-memory voice/singing analysis,
- ephemeral audio delivery using `data:` URIs instead of local media persistence,
- preference saving, recommendations, and feedback loops that support iterative music creation.

## Product capabilities

### Frontend
- Guided composer workflow with context fields, production controls, and creator profile management.
- Speech-to-text button for browser-supported voice command capture.
- In-browser microphone recording for sung references via `MediaRecorder`.
- Embedded playback, waveform preview, result history, recommendation cards, and feedback forms.

### Backend
- FastAPI routes for product overview, generation jobs, preferences, recommendations, and feedback.
- Local synchronous fallback when Redis/Celery is not available.
- Text, audio, and metadata fusion pipeline for prompt conditioning.
- Deterministic synth generator that returns playable WAV audio as an ephemeral data URI.
- Optional external upload path only when `retain_output=true` and S3-compatible storage is configured.

## Architecture notes

- **No local music storage by default:** generated tracks are synthesized to a temp file, converted to a `data:` URI, then deleted.
- **Voice-aware generation:** voice commands and sung references are analyzed in memory to infer transcript cues, energy, emotion, and pitch signature.
- **Replaceable generation core:** the `MusicGenerator` class can later be swapped for MusicGen, AudioCraft, or another model without changing the API contract.

## Local development

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Start the app

```bash
uvicorn app.main:app --reload
```

Open the product at:

```text
http://127.0.0.1:8000
```

### 3. Optional async worker infrastructure

If you want background jobs instead of the built-in fallback mode:

```bash
redis-server
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

If Redis is unavailable, the API automatically falls back to local synchronous generation and still returns a usable result.

## Example generation request

```bash
curl -X POST http://127.0.0.1:8000/v1/music/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "creator_001",
    "text": "Build a premium focus soundtrack with gentle piano and pulse.",
    "duration_sec": 30,
    "voice_command_text": "keep it calm and modern",
    "context": {
      "time_of_day": "late night",
      "activity": "deep work",
      "mood_hint": "calm but premium",
      "use_case": "focus mode"
    },
    "preferences": {
      "genres": ["ambient", "lofi"],
      "moods": ["focused", "calm"],
      "instruments": ["piano", "pads"],
      "target_bpm": 84,
      "vocals_allowed": false
    },
    "retain_output": false
  }'
```

## Current limitations

- Browser speech recognition depends on `SpeechRecognition` / `webkitSpeechRecognition` support.
- The generator is a deterministic synth-based stand-in, not a large generative model.
- Preferences and job history are in-memory for MVP simplicity.
