# Generative-Music-Composer

Production-oriented starter architecture for a multimodal SaaS that generates personalized ambient BGM from:
- text narratives,
- voice/audio emotion cues,
- user metadata and behavior.

## Project structure

```text
.
├── app/
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   ├── audio_pipeline.py
│   │   ├── fusion.py
│   │   ├── music_generator.py
│   │   └── text_pipeline.py
│   ├── personalization/
│   │   └── engine.py
│   ├── services/
│   │   └── storage.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── main.py
└── docs/
    └── architecture.md
```

## What is implemented

1. **Text processing pipeline**
   - Embedding extraction via SentenceTransformers.
   - Lightweight mood/theme extraction heuristics.

2. **Audio pipeline scaffold**
   - Placeholder ASR + emotion features (replace with Whisper + SER model).

3. **Metadata ingestion**
   - API accepts context and metadata payloads.

4. **Fusion model scaffold**
   - Text/audio/metadata vectors fused into a normalized latent representation.

5. **Music generation wrapper**
   - `MusicGenerator` abstraction for plugging in AudioCraft/MusicGen inference.

6. **Personalization engine**
   - Maintains user embeddings and updates based on reward feedback.
   - Returns seed tags for adaptive prompt conditioning.

7. **FastAPI backend**
   - Generate music job submission + polling, preferences, recommendations, feedback.

8. **Async queue**
   - Celery worker job (`generate_bgm`) orchestrates full generation pipeline.

9. **S3-compatible storage**
   - Upload generated audio through `StorageService`.

10. **Observability-ready pattern**
   - Modular service boundaries that can be instrumented with metrics/traces.

## API examples

### Generate BGM

`POST /v1/music/generate`

```json
{
  "user_id": "user_123",
  "text": "A calm, warm atmosphere for studying at night.",
  "audio_uri": "s3://uploads/user_123/voice.wav",
  "context": {
    "time_of_day": "night",
    "activity": "studying",
    "mood_hint": "focused"
  },
  "metadata": {
    "preferred_instruments": ["piano", "pads"],
    "target_energy": 0.2
  },
  "duration_sec": 45
}
```

### Save preferences

`POST /v1/preferences`

```json
{
  "user_id": "user_123",
  "genres": ["ambient", "lofi"],
  "moods": ["calm", "focused"],
  "instruments": ["piano"],
  "target_bpm": 72
}
```

### Submit feedback

`POST /v1/feedback`

```json
{
  "user_id": "user_123",
  "track_id": "track_abc",
  "completion": 0.93,
  "skipped": false,
  "liked": true,
  "replayed": true
}
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Start a worker:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## Performance tips

- Batch text/audio inference on GPU worker pools.
- Keep hot models loaded in long-lived worker processes.
- Cache user embeddings and top-N recommendation candidates in Redis.
- Use shorter model variants (Whisper tiny/small, MusicGen small) for low-latency tiers.
- Route premium jobs to larger GPU nodes and batch by target duration.

See `docs/architecture.md` for full SaaS architecture, personalization math intuition, deployment, and security design.
