from app.models.audio_pipeline import AudioPipeline
from app.models.fusion import FusionModel
from app.models.music_generator import MusicGenerator
from app.models.text_pipeline import TextPipeline
from app.personalization.engine import PersonalizationEngine
from app.services.storage import StorageService
from app.workers.celery_app import celery_app

text_pipeline = TextPipeline()
audio_pipeline = AudioPipeline()
fusion_model = FusionModel()
music_generator = MusicGenerator()
storage_service = StorageService()
personalization_engine = PersonalizationEngine()


@celery_app.task(name="generate_bgm")
def generate_bgm_job(payload: dict) -> dict:
    text_features = text_pipeline.extract(payload["text"])
    audio_features = audio_pipeline.extract(payload.get("audio_uri"))

    metadata_embedding = [float(len(payload.get("metadata", {})))] * 8
    user_tags = personalization_engine.recommend_seed_tags(payload["user_id"])
    fused = fusion_model.fuse(
        text_embedding=text_features.embedding,
        audio_embedding=audio_features.embedding,
        metadata_embedding=metadata_embedding,
        mood=text_features.mood,
    )

    result = music_generator.generate(
        prompt_tags=fused.prompt_tags + user_tags,
        duration_sec=payload.get("duration_sec", 30),
    )

    object_key = f"generated/{payload['user_id']}/{result.track_id}.wav"
    audio_uri = storage_service.upload_generated_audio(result.local_path, object_key)

    return {
        "track_id": result.track_id,
        "audio_uri": audio_uri,
        "mood": text_features.mood,
        "theme": text_features.theme,
    }
