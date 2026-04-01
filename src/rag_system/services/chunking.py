from dataclasses import dataclass


@dataclass(slots=True)
class SourcePage:
    page_number: int
    text: str


@dataclass(slots=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str


def chunk_pages(pages: list[SourcePage], chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        normalized = " ".join(page.text.split())
        if not normalized:
            continue

        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            piece = normalized[start:end].strip()
            if piece:
                chunks.append(
                    TextChunk(
                        page_number=page.page_number,
                        chunk_index=global_index,
                        content=piece,
                    )
                )
                global_index += 1

            if end >= len(normalized):
                break

            next_start = end - chunk_overlap
            if next_start <= start:
                next_start = end
            start = next_start

    return chunks
