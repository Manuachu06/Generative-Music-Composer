from __future__ import annotations

from pathlib import Path

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

    voice_reference = payload.get("voice_reference") or {}
    audio_features = audio_pipeline.extract(
        voice_command_text=payload.get("voice_command_text"),
        voice_reference_base64=voice_reference.get("audio_base64"),
        transcript_hint=voice_reference.get("transcript_hint"),
    )

    preferences = payload.get("preferences") or {}
    context = payload.get("context") or {}
    metadata = payload.get("metadata") or {}

    metadata_embedding = [
        float(len(metadata)),
        float(payload.get("duration_sec", 30)) / 90.0,
        float(bool(context.get("activity"))),
        float(bool(context.get("time_of_day"))),
        float(len(preferences.get("genres", []))),
        float(len(preferences.get("moods", []))),
        float(len(preferences.get("instruments", []))),
        float(preferences.get("target_bpm") or 0) / 200.0,
    ]
    user_tags = personalization_engine.recommend_seed_tags(payload["user_id"])
    voice_tags = [audio_features.emotion, audio_features.pitch_signature, audio_features.performance_type]

    fused = fusion_model.fuse(
        text_embedding=text_features.embedding,
        audio_embedding=audio_features.embedding,
        metadata_embedding=metadata_embedding,
        mood=text_features.mood,
        theme=text_features.theme,
        directives=text_features.directives,
        user_tags=user_tags,
        voice_tags=voice_tags,
    )

    result = music_generator.generate(
        prompt_tags=fused.prompt_tags,
        duration_sec=payload.get("duration_sec", 30),
    )

    external_audio_uri = None
    storage_mode = "ephemeral"
    if payload.get("retain_output"):
        object_key = f"generated/{payload['user_id']}/{Path(result.local_path).name}"
        external_audio_uri = storage_service.upload_generated_audio(result.local_path, object_key)
        storage_mode = "external" if external_audio_uri else "ephemeral"

    audio_data_uri = music_generator.encode_data_uri(result.local_path)
    storage_service.cleanup_temp_file(result.local_path)

    return {
        "track_id": result.track_id,
        "title": result.title,
        "summary": fused.summary,
        "prompt_tags": fused.prompt_tags,
        "mood": text_features.mood,
        "theme": text_features.theme,
        "duration_sec": payload.get("duration_sec", 30),
        "audio_data_uri": audio_data_uri,
        "storage_mode": storage_mode,
        "external_audio_uri": external_audio_uri,
        "waveform_peaks": result.waveform_peaks,
        "voice_insights": {
            "transcript": audio_features.transcript,
            "emotion": audio_features.emotion,
            "performance_type": audio_features.performance_type,
            "energy": audio_features.energy,
            "pitch_signature": audio_features.pitch_signature,
        },
    }
