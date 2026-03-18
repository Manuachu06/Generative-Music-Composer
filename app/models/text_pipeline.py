from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math


@dataclass
class TextFeatures:
    embedding: list[float]
    mood: str
    theme: str
    directives: list[str]


class TextPipeline:
    """Lightweight text understanding pipeline.

    It uses deterministic hashed features so the product can run locally without
    downloading large embedding models, while still keeping a clean interface for
    swapping in a real text encoder later.
    """

    def extract(self, text: str) -> TextFeatures:
        lower_text = text.lower()
        mood = self._infer_mood(lower_text)
        theme = self._infer_theme(lower_text)
        directives = self._extract_directives(lower_text)
        embedding = self._hash_embedding(lower_text)
        return TextFeatures(embedding=embedding, mood=mood, theme=theme, directives=directives)

    def _hash_embedding(self, text: str, size: int = 16) -> list[float]:
        values: list[float] = []
        for index in range(size):
            digest = hashlib.sha256(f"{index}:{text}".encode("utf-8")).digest()
            raw = int.from_bytes(digest[:4], "little", signed=False)
            values.append((raw / 2**32) * 2 - 1)

        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    def _infer_mood(self, text: str) -> str:
        if any(token in text for token in ["focus", "study", "calm", "soft", "gentle"]):
            return "calm"
        if any(token in text for token in ["epic", "trailer", "cinematic", "heroic"]):
            return "cinematic"
        if any(token in text for token in ["club", "dance", "hype", "energetic"]):
            return "energetic"
        if any(token in text for token in ["dream", "meditation", "sleep", "floating"]):
            return "ethereal"
        return "balanced"

    def _infer_theme(self, text: str) -> str:
        if any(token in text for token in ["lofi", "study", "bedroom"]):
            return "lofi"
        if any(token in text for token in ["ambient", "drone", "texture"]):
            return "ambient"
        if any(token in text for token in ["orchestra", "cinematic", "trailer"]):
            return "cinematic"
        if any(token in text for token in ["game", "level", "boss"]):
            return "game-score"
        return "hybrid"

    def _extract_directives(self, text: str) -> list[str]:
        directives: list[str] = []
        if "piano" in text:
            directives.append("piano-led")
        if "guitar" in text:
            directives.append("guitar-texture")
        if "vocal" in text or "hum" in text:
            directives.append("vocal-motif")
        if "slow" in text:
            directives.append("slow-build")
        if "loop" in text:
            directives.append("seamless-loop")
        return directives
