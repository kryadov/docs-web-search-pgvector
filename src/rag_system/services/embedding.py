import hashlib
import math


class HashEmbeddingService:
    def __init__(self, embedding_dim: int) -> None:
        self.embedding_dim = embedding_dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.embedding_dim
        tokens = [token for token in text.lower().split() if token]

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            for step in range(0, len(digest), 2):
                bucket = digest[step] % self.embedding_dim
                sign = -1.0 if digest[step + 1] % 2 else 1.0
                vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
