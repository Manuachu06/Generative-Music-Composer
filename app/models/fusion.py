from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FusedEmbedding:
    vector: list[float]
    prompt_tags: list[str]
    summary: str


class FusionModel:
    def fuse(
        self,
        text_embedding: list[float],
        audio_embedding: list[float],
        metadata_embedding: list[float],
        mood: str,
        theme: str,
        directives: list[str],
        user_tags: list[str],
        voice_tags: list[str],
    ) -> FusedEmbedding:
        merged = text_embedding + audio_embedding + metadata_embedding
        norm = max(sum(abs(value) for value in merged), 1e-6)
        vector = [value / norm for value in merged]

        prompt_tags: list[str] = []
        for tag in [mood, theme, *directives, *user_tags, *voice_tags, "instrumental"]:
            if tag and tag not in prompt_tags:
                prompt_tags.append(tag)

        summary = f"{mood} {theme} soundtrack shaped by {', '.join(prompt_tags[:4])}"
        return FusedEmbedding(vector=vector, prompt_tags=prompt_tags, summary=summary)
