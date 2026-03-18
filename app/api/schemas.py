from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContextTags(BaseModel):
    time_of_day: str | None = None
    activity: str | None = None
    mood_hint: str | None = None
    use_case: str | None = None


class VoiceReferenceInput(BaseModel):
    mime_type: str = Field(default="audio/webm")
    audio_base64: str = Field(min_length=16)
    source: Literal["voice-command", "sung-reference", "uploaded-reference"] = "voice-command"
    transcript_hint: str | None = None


class GenerationPreferences(BaseModel):
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    instruments: list[str] = Field(default_factory=list)
    target_bpm: int | None = Field(default=None, ge=40, le=200)
    vocals_allowed: bool = False


class GenerateMusicRequest(BaseModel):
    user_id: str = Field(min_length=3)
    text: str = Field(min_length=3)
    duration_sec: int = Field(default=30, ge=10, le=90)
    context: ContextTags = Field(default_factory=ContextTags)
    metadata: dict[str, Any] = Field(default_factory=dict)
    preferences: GenerationPreferences = Field(default_factory=GenerationPreferences)
    voice_command_text: str | None = None
    voice_reference: VoiceReferenceInput | None = None
    retain_output: bool = False


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    eta_sec: int
    mode: Literal["async", "local-sync"]


class GeneratedTrackResponse(BaseModel):
    track_id: str
    title: str
    summary: str
    prompt_tags: list[str]
    mood: str
    theme: str
    duration_sec: int
    audio_data_uri: str
    storage_mode: Literal["ephemeral", "external"] = "ephemeral"
    external_audio_uri: str | None = None
    waveform_peaks: list[float] = Field(default_factory=list)
    voice_insights: dict[str, Any] = Field(default_factory=dict)


class SavePreferenceRequest(GenerationPreferences):
    user_id: str


class RecommendationItem(BaseModel):
    track_id: str
    score: float
    title: str
    rationale: str
    prompt: str
    tags: list[str]


class RecommendationsResponse(BaseModel):
    user_id: str
    items: list[RecommendationItem]


class FeedbackRequest(BaseModel):
    user_id: str
    track_id: str
    completion: float = Field(ge=0, le=1)
    skipped: bool = False
    liked: bool = False
    replayed: bool = False


class ProductOverviewResponse(BaseModel):
    product_name: str
    supports_voice_commands: bool
    supports_singing_reference: bool
    stores_music_locally: bool
    generation_modes: list[str]
    recommended_flow: list[str]
