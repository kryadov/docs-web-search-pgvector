from io import BytesIO

from docx import Document as DocxDocument
from pypdf import PdfReader

from rag_system.services.chunking import SourcePage


def parse_document(file_extension: str, payload: bytes) -> list[SourcePage]:
    if file_extension == ".pdf":
        return _parse_pdf(payload)
    if file_extension == ".docx":
        return _parse_docx(payload)
    if file_extension == ".txt":
        return _parse_txt(payload)
    raise ValueError(f"Формат {file_extension} не поддерживается")


def _parse_pdf(payload: bytes) -> list[SourcePage]:
    reader = PdfReader(BytesIO(payload))
    pages: list[SourcePage] = []

    for index, page in enumerate(reader.pages, start=1):
        pages.append(SourcePage(page_number=index, text=page.extract_text() or ""))

    return pages


def _parse_docx(payload: bytes, logical_page_size: int = 3_500) -> list[SourcePage]:
    document = DocxDocument(BytesIO(payload))
    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return _split_logical_pages(full_text, logical_page_size)


def _parse_txt(payload: bytes, logical_page_size: int = 3_500) -> list[SourcePage]:
    text = payload.decode("utf-8", errors="ignore")
    if "\f" in text:
        raw_pages = text.split("\f")
        return [SourcePage(page_number=index, text=page) for index, page in enumerate(raw_pages, start=1)]
    return _split_logical_pages(text, logical_page_size)


def _split_logical_pages(text: str, logical_page_size: int) -> list[SourcePage]:
    cleaned = text.strip()
    if not cleaned:
        return [SourcePage(page_number=1, text="")]

    pages: list[SourcePage] = []
    cursor = 0
    page_number = 1

    while cursor < len(cleaned):
        window = cleaned[cursor : cursor + logical_page_size]
        pages.append(SourcePage(page_number=page_number, text=window))
        cursor += logical_page_size
        page_number += 1

    return pages
