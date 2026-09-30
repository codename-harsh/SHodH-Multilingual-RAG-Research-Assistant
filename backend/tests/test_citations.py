from app.pipeline.llm.citations import remove_unverified_citations


def test_unverified_inline_citations_are_removed():
    chunks = [{"page": 2, "chunk_id": "p2-c0"}]
    answer = "Supported [page 2, chunk p2-c0]; invented [page 99, chunk p99-c7]."

    assert remove_unverified_citations(answer, chunks) == "Supported [page 2, chunk p2-c0]; invented ."


def test_empty_context_removes_all_inline_citations():
    assert remove_unverified_citations("Claim [page 1, chunk p1-c0].", []) == "Claim ."


def test_citation_validation_ignores_spacing_and_case():
    chunks = [{"page": 3, "chunk_id": "p3-c1"}]

    assert remove_unverified_citations("[ PAGE 3 , CHUNK p3-c1 ]", chunks) == "[ PAGE 3 , CHUNK p3-c1 ]"
