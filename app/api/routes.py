import uuid
from threading import Lock

from fastapi import APIRouter
from kombu.exceptions import OperationalError

from fastapi import APIRouter

from app.api.schemas import (
    FeedbackRequest,
    GenerateMusicRequest,
    JobCreatedResponse,
    RecommendationItem,
    RecommendationsResponse,
    RecommendationsResponse,
    RecommendationItem,
    SavePreferenceRequest,
)
from app.personalization.engine import PersonalizationEngine
from app.workers.tasks import generate_bgm_job

router = APIRouter(prefix="/v1")
personalization_engine = PersonalizationEngine()

_local_jobs: dict[str, dict] = {}
_local_jobs_lock = Lock()


@router.post("/music/generate", response_model=JobCreatedResponse)
def generate_music(request: GenerateMusicRequest) -> JobCreatedResponse:
    payload = request.model_dump()
    try:
        task = generate_bgm_job.delay(payload)
        return JobCreatedResponse(job_id=task.id, status="queued", eta_sec=15)
    except OperationalError:
        # Fallback mode for local dev when Redis/Celery are not running.
        result = generate_bgm_job.apply(args=[payload])
        job_id = f"local_{uuid.uuid4().hex[:10]}"
        with _local_jobs_lock:
            _local_jobs[job_id] = {
                "job_id": job_id,
                "status": "SUCCESS" if result.successful() else "FAILURE",
                "result": result.result,
                "backend": "local-sync-fallback",
            }
        return JobCreatedResponse(job_id=job_id, status="completed_local", eta_sec=0)

@router.post("/music/generate", response_model=JobCreatedResponse)
def generate_music(request: GenerateMusicRequest) -> JobCreatedResponse:
    task = generate_bgm_job.delay(request.model_dump())
    return JobCreatedResponse(job_id=task.id, status="queued", eta_sec=15)


@router.get("/music/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if job_id.startswith("local_"):
        with _local_jobs_lock:
            return _local_jobs.get(job_id, {"job_id": job_id, "status": "NOT_FOUND"})

    result = generate_bgm_job.AsyncResult(job_id)
    payload = {"job_id": job_id, "status": result.status}
    if result.successful():
        payload["result"] = result.result
    return payload


@router.post("/preferences")
def save_preferences(request: SavePreferenceRequest) -> dict:
    return {"status": "saved", "user_id": request.user_id, "preferences": request.model_dump()}


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(user_id: str) -> RecommendationsResponse:
    seed_tags = personalization_engine.recommend_seed_tags(user_id)
    items = [
        RecommendationItem(
            track_id=f"seed_{uuid.uuid4().hex[:8]}",
            score=0.89,
            audio_uri="s3://bgm-assets/demo/demo.wav",
            tags=seed_tags,
        )
    ]
    return RecommendationsResponse(user_id=user_id, items=items)


@router.post("/feedback")
def post_feedback(request: FeedbackRequest) -> dict:
    reward = 0.4 * request.completion + 0.3 * float(request.liked) + 0.2 * float(request.replayed) - 0.3 * float(request.skipped)
    updated = personalization_engine.update_user_embedding(request.user_id, [0.1] * 16, reward)
    return {"status": "ok", "user_id": request.user_id, "reward": reward, "embedding_head": updated[:4]}
