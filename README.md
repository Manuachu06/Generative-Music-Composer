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
   - Generate music job submission + polling, preferences, recommendations, feedback, and browser playback-ready output URLs.

8. **Async queue**
   - Celery worker job (`generate_bgm`) orchestrates full generation pipeline.

9. **S3-compatible storage**
   - Upload generated audio through `StorageService`.

10. **Observability-ready pattern**
   - Modular service boundaries that can be instrumented with metrics/traces.

## Run on local system

### 1) Prerequisites
- Python 3.10+
- `pip`
- Redis (for Celery broker/backend)
- S3-compatible storage (MinIO recommended for local dev)

### 2) Create virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Start Redis (optional but recommended)

If Redis is installed locally:

```bash
redis-server
```

Or using Docker:

```bash
docker run --name bgm-redis -p 6379:6379 redis:7
```

### 4) Start MinIO (optional local S3-compatible storage)

```bash
docker run --name bgm-minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minio \
  -e MINIO_ROOT_PASSWORD=minio123 \
  minio/minio server /data --console-address ":9001"
```

Create the default bucket (`bgm-assets`) once MinIO is running:

```bash
python - <<'PY'
import boto3
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minio",
    aws_secret_access_key="minio123",
)
bucket = "bgm-assets"
existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
if bucket not in existing:
    s3.create_bucket(Bucket=bucket)
print("bucket ready:", bucket)
PY
```

### 5) Configure environment variables (optional)

Defaults are already in `app/core/config.py`. If needed, create a `.env` file:

```env
APP_NAME="Generative Music Composer API"
ENVIRONMENT="dev"
REDIS_URL="redis://localhost:6379/0"
S3_BUCKET="bgm-assets"
S3_ENDPOINT_URL="http://localhost:9000"
AWS_ACCESS_KEY_ID="minio"
AWS_SECRET_ACCESS_KEY="minio123"
```

### 6) Run API server

```bash
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```


### 6.1) Open the product UI

After starting the API server, open:

```
http://127.0.0.1:8000
```

The UI provides a product-like experience with:
- prompt-based generation,
- auto polling until complete,
- playable audio output in an embedded player,
- generated track history list,
- preference and feedback actions.

### 7) Run Celery worker (new terminal)

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### Redis connection error fix (WinError 10061)

If you see `Error 10061 connecting to localhost:6379`, Redis is not running.
You now have **two options**:

1. Start Redis (recommended for real async queue behavior), or
2. Keep Redis off and use built-in local fallback mode. In fallback mode, `/v1/music/generate` runs synchronously and returns `status: "completed_local"`.

This means the API and UI can still be tested without Redis/Celery running.

If MinIO/S3 is not available, generated output URI falls back to `file://...` for local testing.

### 8) Test generation flow

Submit a generation job:

```bash
curl -X POST http://127.0.0.1:8000/v1/music/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "text": "A calm, warm atmosphere for studying at night.",
    "duration_sec": 30,
    "metadata": {"target_energy": 0.2}
  }'
```

Poll job status:

```bash
curl http://127.0.0.1:8000/v1/music/jobs/<JOB_ID>
```

> Note: current `MusicGenerator` generates a synthetic preview tone WAV so the product UI can play audio end-to-end. Replace `app/models/music_generator.py` with AudioCraft/MusicGen inference for true AI-generated music.

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

## Performance tips

- Batch text/audio inference on GPU worker pools.
- Keep hot models loaded in long-lived worker processes.
- Cache user embeddings and top-N recommendation candidates in Redis.
- Use shorter model variants (Whisper tiny/small, MusicGen small) for low-latency tiers.
- Route premium jobs to larger GPU nodes and batch by target duration.

See `docs/architecture.md` for full SaaS architecture, personalization math intuition, deployment, and security design.
