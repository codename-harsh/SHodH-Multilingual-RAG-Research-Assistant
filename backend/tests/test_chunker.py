from app.pipeline.ingestion.chunker import PageText, chunk_pages, token_length


def test_chunks_respect_page_boundaries():
    pages = [PageText(page=1, text="alpha " * 300), PageText(page=2, text="beta " * 300)]
    chunks = chunk_pages(pages, chunk_size=50, chunk_overlap=10)

    assert chunks
    assert {chunk.page for chunk in chunks} == {1, 2}
    assert all(token_length(chunk.text) <= 50 for chunk in chunks)


def test_chunk_ids_are_page_scoped():
    pages = [PageText(page=3, text="hello world " * 20)]
    chunks = chunk_pages(pages, chunk_size=20, chunk_overlap=4)

    assert chunks
    assert all(chunk.chunk_id.startswith("p3-c") for chunk in chunks)
