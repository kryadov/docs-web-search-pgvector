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
