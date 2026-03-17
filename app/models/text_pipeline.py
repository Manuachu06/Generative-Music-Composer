from dataclasses import dataclass

from sentence_transformers import SentenceTransformer


@dataclass
class TextFeatures:
    embedding: list[float]
    mood: str
    theme: str


class TextPipeline:
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> None:
        self.embedder = SentenceTransformer(model_name)

    def extract(self, text: str) -> TextFeatures:
        embedding = self.embedder.encode(text, normalize_embeddings=True).tolist()
        lower_text = text.lower()
        mood = "calm" if any(token in lower_text for token in ["calm", "relax", "focus"]) else "neutral"
        theme = "ambient" if "ambient" in lower_text else "cinematic"
        return TextFeatures(embedding=embedding, mood=mood, theme=theme)
