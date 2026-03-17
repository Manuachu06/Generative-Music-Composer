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
### 3) Start Redis

If Redis is installed locally:

```bash
redis-server
```

Or using Docker:

```bash
docker run --name bgm-redis -p 6379:6379 redis:7
```

### 4) Start MinIO (optional local S3-compatible storage)
### 4) Start MinIO (local S3-compatible storage)

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


### 6.1) Open the front-end test UI

After starting the API server, open:

```
http://127.0.0.1:8000
```

The UI lets you test:
- generate BGM jobs,
- poll job status,
- save preferences,
- fetch recommendations,
- submit feedback.

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

> Note: current `MusicGenerator` writes placeholder audio bytes as a scaffold. Replace `app/models/music_generator.py` with AudioCraft/MusicGen inference to generate real WAV output.

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
# Generative Music Composer

Production-oriented blueprint and implementation guide for a multimodal SaaS platform that generates personalized ambient background music (BGM) from text, voice, and user metadata.

---

## Prompt 1 — End-to-End SaaS Architecture + System Design

### 1) High-Level Architecture

```text
┌───────────────────────────────────────────────────────────────────────┐
│                          Client Applications                          │
│  Web (React/Next.js) | Mobile (Flutter/React Native) | B2B API SDK  │
└───────────────┬───────────────────────────────────────────────────────┘
                │ HTTPS + JWT
┌───────────────▼───────────────────────────────────────────────────────┐
│                          API Gateway Layer                            │
│    AuthN/AuthZ | Rate Limit | Request Validation | Routing            │
└───────────────┬───────────────────────────────────────────────────────┘
                │
     ┌──────────▼──────────┐      ┌──────────────────────┐
     │   Core Backend API  │      │  Async Job Orchestr. │
     │ (FastAPI services)  │◄────►│ (Celery + Redis/RQ)  │
     └──────┬──────────────┘      └──────────┬───────────┘
            │                                 │
   ┌────────▼─────────┐               ┌───────▼──────────────────────┐
   │ Personalization  │               │   Model Inference Services    │
   │ Service          │               │ Whisper | Emotion | MusicGen   │
   └────────┬─────────┘               └──────────┬────────────────────┘
            │                                    │
┌───────────▼────────────────────────────────────▼─────────────────────┐
│                              Data Layer                               │
│ PostgreSQL (users, prefs, jobs) | Vector DB (FAISS/Milvus/pgvector)  │
│ Object Storage (S3/GCS: input + generated audio) | Redis cache       │
└───────────────────────────────────────────────────────────────────────┘
```

**Why this design**
- **FastAPI microservices**: high throughput + straightforward async Python ecosystem.
- **Async job queue**: generation tasks are GPU-heavy and long-running; queue decouples API latency from inference time.
- **Model services isolated**: independent scaling for Whisper (CPU/GPU mixed) vs MusicGen (GPU intensive).
- **Hybrid storage**: structured relational data + vector search + blob audio files.

---

### 2) Microservices Breakdown

1. **API Gateway / Edge Service**
   - JWT verification, tenant resolution, throttling, WAF integration.
   - Routes traffic to internal services.

2. **Identity & User Service**
   - User profile, OAuth2/social login, subscription tier.
   - Stores consent/privacy settings.

3. **Input Ingestion Service**
   - Accepts text/audio/metadata payloads.
   - Validates formats, creates processing jobs, stores raw payload references.

4. **Text Understanding Service**
   - LLM/transformer extraction: mood, tempo hints, scene tags, instruments.
   - Produces `text_embedding` + structured attributes.

5. **Audio Understanding Service**
   - Whisper ASR for transcript.
   - Emotion classifier from speech prosody/spectral features.
   - Produces `audio_embedding` + emotion probabilities.

6. **Fusion & Conditioning Service**
   - Combines text/audio/metadata into a unified latent representation.
   - Builds final prompt-conditioning package for generator.

7. **Music Generation Service**
   - Hosts MusicGen/AudioCraft models.
   - Generates one or multiple candidate BGM tracks.

8. **Personalization Service**
   - Maintains user embeddings from explicit/implicit signals.
   - Ranks generated candidates and prior content.

9. **Catalog & Recommendation Service**
   - ANN retrieval over content embeddings (FAISS/Milvus).
   - Returns top-N personalized tracks/prompts.

10. **Feedback & Analytics Service**
    - Captures play duration, skips, likes, repeats.
    - Feeds retraining and online preference updates.

11. **Observability Service**
    - Centralized logs, traces, metrics, model latency/cost dashboard.

---

### 3) Data Flow (Text → Embedding → Music Generation)

```text
User Input
  ├── Text story ----------------------┐
  ├── Voice sample ---- ASR + Emotion -┼─► Feature Normalization
  └── Metadata prefs ------------------┘
                        │
                        ▼
                 Multimodal Fusion
              (concat + projection MLP)
                        │
                        ▼
              Conditioning Prompt Builder
      (mood, tempo, energy, instrumentation, context)
                        │
                        ▼
                  MusicGen/AudioCraft
              (N candidate generations)
                        │
                        ▼
            Personalization Re-ranker
        (user embedding ⋅ track embedding)
                        │
                        ▼
              Store + Stream Best Track
```

---

### 4) Model Selection (Open Source)

- **Music generation**: `facebook/musicgen-small` for prototyping; `musicgen-medium/large` for premium tiers.
- **Audio/text framework**: **AudioCraft** for consistent generation stack.
- **Speech-to-text**: **Whisper** (`small`/`medium`) depending latency/quality budget.
- **Emotion detection**:
  - Option A: speech-emotion transformer (e.g., Wav2Vec2 fine-tuned on IEMOCAP/RAVDESS).
  - Option B: handcrafted audio features + lightweight classifier for low-latency.
- **Text embeddings**: `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) for fast semantic signals.
- **Fusion model**: shallow MLP projection or cross-attention module (start simple).

**Selection logic**
- Start with smaller models for p95 latency and GPU cost control.
- Introduce larger models only for paid plans or offline high-quality render mode.

---

### 5) Personalization Layer

- **User profile**
  - Explicit: favorite genres, disliked instruments, energy range.
  - Implicit: skip rate, completion rate, replay count, session context.
- **Embedding strategy**
  - `u_t = α*u_{t-1} + (1-α)*x_t`, where `x_t` is interaction-derived track/context vector.
- **Recommendation/ranking**
  - Candidate retrieval via ANN.
  - Final score: `S = w1*cos(u, c) + w2*context_match + w3*novelty - w4*skip_risk`.

---

### 6) Real-time vs Batch

- **Real-time path (sub-10s target)**
  - Lightweight prompt extraction, small MusicGen model, short clips (15–30s), top-1 output.
- **Batch path (quality mode)**
  - Rich multimodal analysis, multi-candidate generation, post-processing/mastering, top-k ranking.

Use queue priorities:
- `high`: interactive UI sessions.
- `low`: scheduled background generation or playlist precomputation.

---

### 7) Storage Strategy

- **PostgreSQL**: users, orgs, subscriptions, jobs, feedback events.
- **Vector DB (FAISS/Milvus/pgvector)**: user/content embeddings + ANN index.
- **Object storage (S3/GCS/MinIO)**: raw uploads, generated WAV/MP3, derived features.
- **Redis**: cache hot recommendations, idempotency keys, queue broker.

---

### 8) FastAPI API Design (Example)

#### `POST /v1/ingest`
Request:
```json
{
  "user_id": "u_123",
  "text": "I need calm focus music for deep work",
  "audio_url": "s3://bucket/voice.wav",
  "metadata": {"time_of_day": "morning", "activity": "coding"}
}
```
Response:
```json
{"job_id": "job_789", "status": "queued"}
```

#### `POST /v1/generate/{job_id}`
Response:
```json
{
  "job_id": "job_789",
  "status": "completed",
  "tracks": [
    {"track_id": "t1", "url": "https://cdn/.../t1.mp3", "duration_sec": 45}
  ]
}
```

#### `POST /v1/preferences`
```json
{"user_id":"u_123","likes":["lofi","piano"],"dislikes":["heavy_drums"]}
```

#### `GET /v1/recommendations?user_id=u_123&limit=10`
Returns ranked track/prompt suggestions.

---

### 9) Scalability + Deployment

- **Kubernetes**
  - Separate node pools: CPU (API/ETL) and GPU (generation).
  - HPA on queue depth + request latency.
- **GPU usage**
  - Model warm pools, mixed precision, micro-batching.
  - Dedicated inference workers by model size.
- **AWS reference**
  - EKS + ALB + ECR + S3 + RDS + ElastiCache + CloudWatch + IAM + KMS.
- **GCP reference**
  - GKE + Cloud Storage + Cloud SQL + Memorystore + Artifact Registry + Cloud Monitoring.

---

### 10) Security + Privacy

- OAuth2/JWT, RBAC for tenant isolation.
- API rate limiting (user + IP + plan tier).
- Encrypt at rest (KMS-managed) and in transit (TLS).
- PII minimization and configurable retention windows.
- Signed URLs for media access.
- Audit logs for model inputs/outputs and admin actions.

---

## Prompt 2 — Full Implementation Guide (Code + Models + APIs)

### Suggested Project Structure

```text
app/
  api/
    routes_ingest.py
    routes_generate.py
    routes_preferences.py
    routes_reco.py
  core/
    config.py
    logging.py
    security.py
  models/
    text_pipeline.py
    audio_pipeline.py
    fusion.py
    musicgen_service.py
    personalization.py
  workers/
    celery_app.py
    tasks_generation.py
  storage/
    s3_client.py
    vector_store.py
    postgres.py
  schemas/
    ingest.py
    generate.py
    preferences.py
  main.py
```

### Core Implementation Snippets

```python
# app/models/text_pipeline.py
from sentence_transformers import SentenceTransformer

class TextPipeline:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def extract(self, text: str) -> dict:
        emb = self.model.encode([text], normalize_embeddings=True)[0]
        # replace with LLM extraction in production
        tags = {"mood": "calm", "energy": 0.3, "theme": "focus"}
        return {"embedding": emb.tolist(), "tags": tags}
```

```python
# app/models/audio_pipeline.py
import whisper

class AudioPipeline:
    def __init__(self, whisper_size: str = "small"):
        self.asr = whisper.load_model(whisper_size)

    def transcribe(self, audio_path: str) -> str:
        result = self.asr.transcribe(audio_path)
        return result["text"]

    def detect_emotion(self, audio_path: str) -> dict:
        # placeholder: integrate wav2vec2 emotion classifier
        return {"calm": 0.62, "happy": 0.18, "sad": 0.12, "angry": 0.08}
```

```python
# app/models/fusion.py
import numpy as np

def fuse_embeddings(text_emb, audio_emb, meta_features):
    t = np.array(text_emb)
    a = np.array(audio_emb)
    m = np.array(meta_features)
    concat = np.concatenate([t, a, m])
    norm = concat / (np.linalg.norm(concat) + 1e-8)
    return norm.tolist()
```

```python
# app/models/musicgen_service.py
from audiocraft.models import MusicGen

class MusicGenerator:
    def __init__(self, model_name: str = "facebook/musicgen-small"):
        self.model = MusicGen.get_pretrained(model_name)

    def generate(self, prompt: str, duration: int = 30):
        self.model.set_generation_params(duration=duration)
        return self.model.generate([prompt])
```

```python
# app/workers/tasks_generation.py
from celery import shared_task

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_bgm_task(self, job_id: str):
    # 1) load job payload
    # 2) run text/audio pipelines
    # 3) fuse multimodal features
    # 4) construct conditioning prompt
    # 5) generate tracks
    # 6) upload to S3 + persist metadata
    return {"job_id": job_id, "status": "completed"}
```

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(title="Multimodal BGM API", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Performance Tips
- Keep ASR and MusicGen in separate worker pools.
- Use FP16/autocast for GPU inference.
- Cache repeated embeddings/prompts.
- Batch recommendation scoring.
- Precompute profile embeddings nightly.

### Monitoring
- **Logs**: structured JSON with job/user correlation IDs.
- **Metrics**: queue depth, generation latency, GPU utilization, cost per minute audio.
- **Tracing**: OpenTelemetry across API → queue → model services.

---

## Prompt 3 — Personalization + Adaptive Music Intelligence

### Personalization Microservice Architecture

```text
Feedback Events ─► Feature Store ─► User Embedding Updater ─► Vector Index
       ▲                    │                    │                  │
       │                    ▼                    ▼                  ▼
   Player SDK         Context Signals       Ranker Service     Candidate Store
```

### Signals
- **Explicit**: likes/dislikes, ratings, chosen moods.
- **Implicit**: skip after X sec, completion ratio, repeats, session length.
- **Context**: hour/day, activity, device, locale.

### Mathematical Intuition
- Represent user `u` and content `c` as vectors.
- Affinity via cosine similarity:
  \[
  sim(u,c)=\frac{u\cdot c}{\|u\|\|c\|}
  \]
- Contextual score:
  \[
  score(u,c,ctx)=\alpha\,sim(u,c)+\beta\,g(ctx,c)+\gamma\,novelty(c)-\delta\,risk_{skip}(u,c)
  \]
- Online user update:
  \[
  u_{t+1}=\lambda u_t + (1-\lambda)\,\phi(interaction_t)
  \]

### Feedback Loop / RL-lite
1. Generate candidates.
2. Rank + serve top track.
3. Collect reward signal (listen depth, like, save).
4. Update user embedding and rerank policy weights.
5. Periodically retrain reward model offline.

### Cold Start Strategy
- Ask 3–5 onboarding questions (genre, energy, instruments).
- Bootstrap with demographic/context priors.
- Use exploration bonus (multi-armed bandit) to diversify early sessions.

### Adaptive Prompt Engineering for MusicGen
Construct prompt template from profile + context:

```text
"ambient {mood} background music, {energy} energy, {instrumentation},
for {activity} during {time_of_day}, smooth loop, minimal vocals"
```

### A/B Testing Plan
- **Unit of randomization**: user-level.
- **Primary metric**: 7-day retained listening minutes.
- **Secondary**: skip rate, like rate, generation acceptance.
- **Guardrails**: latency p95, GPU cost/user, failure rate.

### Pseudocode (Ranking + Update)

```python
def rank_tracks(user_vec, candidates, context):
    scored = []
    for c in candidates:
        s = 0.6 * cosine(user_vec, c.vec)
        s += 0.2 * context_match(context, c.tags)
        s += 0.1 * novelty(c)
        s -= 0.1 * skip_risk(user_vec, c)
        scored.append((c.id, s))
    return sorted(scored, key=lambda x: x[1], reverse=True)


def update_user_embedding(user_vec, consumed_track_vec, reward, lam=0.9):
    interaction_vec = reward * consumed_track_vec
    return normalize(lam * user_vec + (1 - lam) * interaction_vec)
```

---

## Recommended Delivery Roadmap

1. **MVP (4–6 weeks)**: text + metadata pipeline, MusicGen-small, basic preferences.
2. **Phase 2**: voice emotion, ANN recommendations, feedback capture.
3. **Phase 3**: adaptive ranking, contextual policies, premium high-quality render lane.
4. **Phase 4**: enterprise controls, audit, multi-tenant SLAs, cost governance.
