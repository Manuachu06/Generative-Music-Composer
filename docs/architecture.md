# Personalized Ambient BGM SaaS: End-to-End Architecture

## 1) High-Level System Architecture

```text
┌────────────────────────── Client Applications ──────────────────────────┐
│ Web App (React/Next.js) | Mobile App | Partner API                      │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │ HTTPS + JWT
                          ┌────────▼─────────┐
                          │ API Gateway/WAF │
                          └────────┬─────────┘
                                   │
           ┌───────────────────────┼────────────────────────┐
           │                       │                        │
   ┌───────▼────────┐      ┌───────▼────────┐      ┌───────▼────────┐
   │ Ingestion API  │      │ Profile API    │      │ Recommend API  │
   │ (FastAPI)      │      │ (FastAPI)      │      │ (FastAPI)      │
   └───────┬────────┘      └───────┬────────┘      └───────┬────────┘
           │                        │                       │
           │                 ┌──────▼───────┐               │
           │                 │ Metadata DB  │               │
           │                 │ (PostgreSQL) │               │
           │                 └──────────────┘               │
           │                                                │
   ┌───────▼────────┐      ┌────────────────┐      ┌────────▼────────┐
   │ Queue Broker   │◄────►│ Worker Pool     │◄────►│ Vector DB/FAISS │
   │ Redis/RabbitMQ │      │ Celery + GPUs   │      │ user/content vec│
   └───────┬────────┘      └───────┬────────┘      └─────────────────┘
           │                        │
           │                        │
   ┌───────▼────────────────────────▼───────────────────────────────────┐
   │ Model Layer: Whisper, Emotion Encoder, Text LLM, Fusion, MusicGen │
   └───────┬─────────────────────────────────────────────────────────────┘
           │
    ┌──────▼──────────────┐
    │ Object Storage (S3) │  audio inputs/outputs, features, manifests
    └─────────────────────┘
```

### Why these choices
- **FastAPI**: async I/O, typed schemas, easy OpenAPI generation.
- **Celery + Redis**: isolates long-running GPU generation from request path.
- **PostgreSQL**: transactional profile/preference data.
- **S3-compatible storage**: durable binary storage for WAV/MP3 assets.
- **FAISS / vector DB**: low-latency ANN search for personalization.
- **Kubernetes**: horizontal autoscaling + dedicated GPU node pools.

---

## 2) Microservices Breakdown

1. **API Gateway Service**
   - JWT validation, quota checks, request signing.
2. **Input Ingestion Service**
   - Receives text/audio/metadata payloads.
   - Uploads files to S3 and emits async jobs.
3. **Feature Extraction Service**
   - Text mood extraction.
   - Whisper ASR + emotion classification.
4. **Fusion Embedding Service**
   - Projects multimodal features into shared latent vector.
5. **Music Generation Service**
   - Uses AudioCraft/MusicGen conditioned on fused embedding and prompt tokens.
6. **Personalization Service**
   - Maintains user embeddings, updates after feedback.
   - Recommends prompt-conditioning priors.
7. **Recommendation Service**
   - ANN retrieval and re-ranking of generated/seed tracks.
8. **Feedback Analytics Service**
   - Consumes plays/skips/ratings stream; computes implicit signals.
9. **Monitoring/Observability Service**
   - Prometheus metrics, distributed traces, model latency dashboards.

---

## 3) Core Data Flow (Text + Audio + Metadata → Music)

```text
User Input
  ├─ Text story --------------------► Text Encoder (LLM/SentenceTransformer)
  ├─ Voice clip --------------------► Whisper ASR ─► Emotion Model
  └─ Metadata (prefs/context) ------► Metadata Featurizer

[Text Embedding] + [Audio/Speech/Emotion Embedding] + [Metadata Vector]
                               │
                               ▼
                        Fusion Network
                               │
                     Unified Conditioning Vector
                               │
              Prompt Adapter (genre, tempo, mood tags)
                               │
                               ▼
                  MusicGen / AudioCraft Inference
                               │
                    Post-process + loudness normalize
                               │
                               ▼
                  Store in S3 + register in metadata DB
```

### Real-time vs batch
- **Real-time path (<5s target)**: short generation (10–20s previews), cached embeddings, warm GPU pods.
- **Batch path**: full-length tracks (1–5 min), overnight re-ranking, user embedding retraining, A/B offline analysis.

---

## 4) Model Stack (Open Source)

- **Text pipeline**: `sentence-transformers/all-mpnet-base-v2` for semantic embedding, optional LLM mood extraction.
- **ASR**: `openai/whisper-small` or `faster-whisper` for latency-sensitive deployment.
- **Emotion recognition**: wav2vec2-based SER model (e.g., speech-emotion-recognition checkpoints).
- **Music generation**: `facebook/musicgen-small` for low latency, `musicgen-medium/large` for premium tiers.
- **Fusion model**: PyTorch MLP/Transformer that aligns modalities to fixed-size latent space.

---

## 5) Personalization and Adaptive Intelligence

### User profile signals
- **Explicit**: favorite moods, genres, instruments, BPM range.
- **Implicit**: completion ratio, skips, replay count, session time, save/share events.

### Embedding strategy
- User embedding `u_t` updated with exponential smoothing:

\[
 u_t = \alpha u_{t-1} + (1-\alpha)\sum_i w_i c_i
\]

Where `c_i` is consumed-content embedding and `w_i` is confidence from behavior.

### Retrieval and ranking
1. Candidate retrieval via FAISS ANN (cosine similarity).
2. Re-rank with context features (time, activity, mood).
3. Diversity penalty to avoid repetitive output.

### Feedback loop
- Reward signal: `r = 0.4 * completion + 0.3 * like + 0.2 * replay - 0.3 * skip`.
- Online policy updates adapt prompt weights and generation params (tempo, texture density).

### Cold start
- Onboarding quiz + demographic priors.
- Contextual bandits for exploration across mood clusters.
- Content-based similarity until sufficient user history is available.

---

## 6) API Design (FastAPI)

### Core endpoints
- `POST /v1/input/upload` (multipart text/audio/metadata)
- `POST /v1/music/generate` (job submission)
- `GET /v1/music/jobs/{job_id}` (status)
- `POST /v1/preferences` (save user preferences)
- `GET /v1/recommendations` (personalized tracks)
- `POST /v1/feedback` (rating/skip/completion)

### Example request/response contract

```json
POST /v1/music/generate
{
  "user_id": "u_123",
  "text": "I need calm piano ambience for late-night reading",
  "context": {"time_of_day": "night", "activity": "reading"},
  "audio_uri": "s3://bucket/uploads/u_123_voice.wav",
  "duration_sec": 45
}
```

```json
{
  "job_id": "job_9f8a",
  "status": "queued",
  "eta_sec": 12
}
```

---

## 7) Storage Strategy

- **PostgreSQL**: users, subscriptions, jobs, feedback, experiment assignments.
- **S3**: raw audio uploads, generated tracks, model artifacts, waveform previews.
- **Vector store (FAISS/Qdrant/Weaviate)**: user and track embeddings.
- **Redis**: hot cache (feature vectors, recent recommendations), queue backend.

Data retention policy:
- PII minimized and encrypted at rest.
- Audio clips optionally auto-deleted after feature extraction based on user consent tier.

---

## 8) Scalability and Deployment

### Kubernetes layout
- `api-cpu` deployment (HPA on CPU/RPS)
- `worker-gpu` deployment (node selector `gpu=true`, autoscale on queue depth + GPU util)
- `feature-worker-cpu` deployment for ASR/emotion when using CPU models
- `redis`, `postgres`, `vector-db` via managed services recommended

### AWS reference
- **EKS** for orchestration
- **S3** for media
- **RDS Postgres** for metadata
- **ElastiCache Redis** for cache/queue
- **ECR** for containers
- **CloudWatch + Prometheus/Grafana** for observability

### GCP equivalent
- GKE, Cloud Storage, Cloud SQL, Memorystore, Artifact Registry, Cloud Monitoring.

---

## 9) Security and Compliance

- OAuth2/JWT (short-lived access tokens + refresh flow).
- Per-tenant API keys and rate limiting at gateway.
- mTLS/service mesh for east-west traffic.
- Encryption in transit (TLS 1.2+) and at rest (KMS-managed keys).
- Signed S3 URLs for upload/download.
- Audit logs for model access and user-data operations.
- Data governance: consent tracking, deletion workflows (GDPR/CCPA-style).

---

## 10) A/B Testing Plan

- Randomize users into recommendation-policy cohorts.
- Primary metrics: session length, skip rate, completion rate, NPS-like rating.
- Guardrails: latency p95, generation failure rate, cost per generation.
- Sequential testing or Bayesian updating for faster decisions.

