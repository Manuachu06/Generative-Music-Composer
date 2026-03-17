from collections import defaultdict


class PersonalizationEngine:
    def __init__(self) -> None:
        self.user_embeddings: dict[str, list[float]] = defaultdict(lambda: [0.0] * 16)

    def update_user_embedding(self, user_id: str, content_embedding: list[float], reward: float) -> list[float]:
        prior = self.user_embeddings[user_id]
        if len(content_embedding) < len(prior):
            content_embedding = content_embedding + [0.0] * (len(prior) - len(content_embedding))
        alpha = 0.85
        updated = [
            alpha * prior[i] + (1 - alpha) * reward * content_embedding[i]
            for i in range(len(prior))
        ]
        self.user_embeddings[user_id] = updated
        return updated

    def recommend_seed_tags(self, user_id: str) -> list[str]:
        embedding = self.user_embeddings[user_id]
        intensity = sum(embedding)
        return ["calm", "lofi"] if intensity >= 0 else ["cinematic", "drone"]
