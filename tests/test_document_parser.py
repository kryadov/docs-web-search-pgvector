from rag_system.services.document_parser import parse_document


def test_parse_txt_uses_page_breaks() -> None:
    payload = "page1\fpage2".encode("utf-8")

    pages = parse_document(".txt", payload)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[0].text == "page1"
    assert pages[1].page_number == 2
    assert pages[1].text == "page2"


def test_parse_document_rejects_unsupported_extension() -> None:
    try:
        parse_document(".md", b"data")
    except ValueError as error:
        assert "не поддерживается" in str(error)
    else:
        raise AssertionError("Expected ValueError for unsupported format")
