import math

from rag_system.services.embedding import HashEmbeddingService


def test_embedding_dimension_and_norm() -> None:
    service = HashEmbeddingService(embedding_dim=16)
    vector = service.embed("hello world hello")

    assert len(vector) == 16
    norm = math.sqrt(sum(value * value for value in vector))
    assert norm == 1.0


def test_embedding_empty_text_returns_zero_vector() -> None:
    service = HashEmbeddingService(embedding_dim=8)
    vector = service.embed("   ")

    assert vector == [0.0] * 8
