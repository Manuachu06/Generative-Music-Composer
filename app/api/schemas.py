from typing import Any

from pydantic import BaseModel, Field


class ContextTags(BaseModel):
    time_of_day: str | None = None
    activity: str | None = None
    mood_hint: str | None = None


class GenerateMusicRequest(BaseModel):
    user_id: str
    text: str = Field(min_length=3)
    audio_uri: str | None = None
    context: ContextTags = Field(default_factory=ContextTags)
    metadata: dict[str, Any] = Field(default_factory=dict)
    duration_sec: int = Field(default=30, ge=10, le=180)


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    eta_sec: int


class SavePreferenceRequest(BaseModel):
    user_id: str
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    instruments: list[str] = Field(default_factory=list)
    target_bpm: int | None = Field(default=None, ge=40, le=200)


class RecommendationItem(BaseModel):
    track_id: str
    score: float
    audio_uri: str
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
