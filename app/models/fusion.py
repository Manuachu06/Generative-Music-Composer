from dataclasses import dataclass


@dataclass
class FusedEmbedding:
    vector: list[float]
    prompt_tags: list[str]


class FusionModel:
    def fuse(
        self,
        text_embedding: list[float],
        audio_embedding: list[float],
        metadata_embedding: list[float],
        mood: str,
    ) -> FusedEmbedding:
        merged = text_embedding[:64] + audio_embedding + metadata_embedding
        if not merged:
            merged = [0.0]
        norm = max(sum(abs(x) for x in merged), 1e-6)
        vector = [x / norm for x in merged]
        prompt_tags = [mood, "ambient", "instrumental"]
        return FusedEmbedding(vector=vector, prompt_tags=prompt_tags)
