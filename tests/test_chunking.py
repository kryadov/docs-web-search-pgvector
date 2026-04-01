from rag_system.services.chunking import SourcePage, chunk_pages


def test_chunk_pages_creates_overlapping_chunks() -> None:
    page = SourcePage(page_number=1, text="abcdefghij")

    chunks = chunk_pages([page], chunk_size=4, chunk_overlap=2)

    assert [chunk.content for chunk in chunks] == ["abcd", "cdef", "efgh", "ghij"]
    assert [chunk.page_number for chunk in chunks] == [1, 1, 1, 1]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]


def test_chunk_pages_skips_empty_pages() -> None:
    chunks = chunk_pages([SourcePage(page_number=1, text="   ")], chunk_size=10, chunk_overlap=2)
    assert chunks == []
