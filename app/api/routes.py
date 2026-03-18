from __future__ import annotations

import uuid
from threading import Lock

from fastapi import APIRouter
from kombu.exceptions import OperationalError

from app.api.schemas import (
    FeedbackRequest,
    GenerateMusicRequest,
    GeneratedTrackResponse,
    JobCreatedResponse,
    ProductOverviewResponse,
    RecommendationItem,
    RecommendationsResponse,
    SavePreferenceRequest,
)
from app.personalization.engine import PersonalizationEngine
from app.workers.tasks import generate_bgm_job

router = APIRouter(prefix="/v1")
personalization_engine = PersonalizationEngine()

_local_jobs: dict[str, dict] = {}
_local_jobs_lock = Lock()
_user_preferences: dict[str, dict] = {}


@router.get("/product/overview", response_model=ProductOverviewResponse)
def get_product_overview() -> ProductOverviewResponse:
    return ProductOverviewResponse(
        product_name="Auralis Studio",
        supports_voice_commands=True,
        supports_singing_reference=True,
        stores_music_locally=False,
        generation_modes=["text-to-music", "voice-command-guided", "sung-reference-conditioned"],
        recommended_flow=[
            "Describe the scene or outcome you want.",
            "Optionally dictate a voice command or record a sung motif.",
            "Generate an instrumental draft and refine it with feedback.",
        ],
    )


@router.post("/music/generate", response_model=JobCreatedResponse)
def generate_music(request: GenerateMusicRequest) -> JobCreatedResponse:
    payload = request.model_dump()
    try:
        task = generate_bgm_job.delay(payload)
        return JobCreatedResponse(job_id=task.id, status="queued", eta_sec=12, mode="async")
    except OperationalError:
        result = generate_bgm_job.apply(args=[payload])
        job_id = f"local_{uuid.uuid4().hex[:10]}"
        with _local_jobs_lock:
            _local_jobs[job_id] = {
                "job_id": job_id,
                "status": "SUCCESS" if result.successful() else "FAILURE",
                "result": result.result,
                "backend": "local-sync-fallback",
            }
        return JobCreatedResponse(job_id=job_id, status="completed_local", eta_sec=0, mode="local-sync")


@router.get("/music/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if job_id.startswith("local_"):
        with _local_jobs_lock:
            return _local_jobs.get(job_id, {"job_id": job_id, "status": "NOT_FOUND"})

    result = generate_bgm_job.AsyncResult(job_id)
    payload = {"job_id": job_id, "status": result.status}
    if result.successful():
        payload["result"] = GeneratedTrackResponse.model_validate(result.result).model_dump()
    return payload


@router.post("/preferences")
def save_preferences(request: SavePreferenceRequest) -> dict:
    _user_preferences[request.user_id] = request.model_dump()
    return {"status": "saved", "user_id": request.user_id, "preferences": _user_preferences[request.user_id]}


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(user_id: str) -> RecommendationsResponse:
    prefs = _user_preferences.get(user_id, {})
    seed_tags = personalization_engine.recommend_seed_tags(user_id)
    items = [
        RecommendationItem(
            track_id=f"idea_{uuid.uuid4().hex[:8]}",
            score=0.93,
            title="Late Night Focus Pulse",
            rationale="Balances the user profile with a low-distraction arrangement and voice-friendly melodic space.",
            prompt="Warm lofi piano with soft pulse, subtle pad movement, and space for optional humming motifs.",
            tags=[*seed_tags, *prefs.get("genres", [])][:6],
        ),
        RecommendationItem(
            track_id=f"idea_{uuid.uuid4().hex[:8]}",
            score=0.88,
            title="Cinematic Breathline",
            rationale="Good fit when the user provides sung phrases and wants a broader emotional arc.",
            prompt="Slow-building cinematic ambient bed with breathy textures and gentle rhythmic lift.",
            tags=[*seed_tags, *prefs.get("moods", [])][:6],
        ),
    ]
    return RecommendationsResponse(user_id=user_id, items=items)


@router.post("/feedback")
def post_feedback(request: FeedbackRequest) -> dict:
    reward = (
        0.4 * request.completion
        + 0.3 * float(request.liked)
        + 0.2 * float(request.replayed)
        - 0.3 * float(request.skipped)
    )
    updated = personalization_engine.update_user_embedding(request.user_id, [0.1] * 16, reward)
    return {
        "status": "ok",
        "user_id": request.user_id,
        "reward": round(reward, 3),
        "embedding_head": [round(value, 4) for value in updated[:4]],
    }
