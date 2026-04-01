import asyncio
from types import SimpleNamespace
import uuid

import pytest

import rag_system.api as api
from rag_system.api import _build_search_fragment


def test_build_search_fragment_uses_exact_query_match() -> None:
    chunk_text = (
        "Начало длинного текста без ключа. "
        "Здесь находится точное совпадение: FastAPI Search. "
        "Конец длинного текста."
    )

    fragment, has_match = _build_search_fragment(chunk_text, "fastapi search")

    assert has_match is True
    assert "FastAPI Search" in fragment


def test_build_search_fragment_uses_term_match_when_full_query_missing() -> None:
    chunk_text = "Система содержит модуль embeddings и векторный индекс для документов."

    fragment, has_match = _build_search_fragment(chunk_text, "semantic embeddings retrieval")

    assert has_match is True
    assert "embeddings" in fragment.lower()


def test_build_search_fragment_returns_fallback_when_nothing_matches() -> None:
    chunk_text = "Это просто текст без искомых слов в документе."

    fragment, has_match = _build_search_fragment(chunk_text, "совсемдругоеслово")

    assert has_match is False
    assert fragment == chunk_text


def test_execute_search_fills_results_from_fallback_when_matches_are_not_enough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid.uuid4()
    query_text = "api"
    top_k = 3

    chunk_match = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        page_number=1,
        content="contains-match",
    )
    chunk_fallback_1 = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        page_number=2,
        content="fallback-1",
    )
    chunk_fallback_2 = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        page_number=3,
        content="fallback-2",
    )
    chunk_fallback_3 = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        page_number=4,
        content="fallback-3",
    )

    rows = [
        (chunk_match, "doc-1.txt", 0.9),
        (chunk_fallback_1, "doc-2.txt", 0.8),
        (chunk_fallback_2, "doc-3.txt", 0.7),
        (chunk_fallback_3, "doc-4.txt", 0.6),
    ]

    class _FakeExecuteResult:
        def all(self) -> list[tuple[object, str, float]]:
            return rows

    class _FakeSession:
        async def execute(self, _query: object) -> _FakeExecuteResult:
            return _FakeExecuteResult()

    class _FakeEmbedder:
        def embed(self, _text: str) -> list[float]:
            return [0.0]

    def _fake_build_search_fragment(chunk_text: str, _query: str) -> tuple[str, bool]:
        return chunk_text, chunk_text == "contains-match"

    monkeypatch.setattr(api, "embedder", _FakeEmbedder())
    monkeypatch.setattr(api, "_build_search_fragment", _fake_build_search_fragment)

    results = asyncio.run(
        api._execute_search(
            session=_FakeSession(),
            workspace_id=workspace_id,
            query_text=query_text,
            top_k=top_k,
        )
    )

    assert len(results) == top_k
    assert [item.text for item in results] == ["contains-match", "fallback-1", "fallback-2"]
