from pathlib import Path

import fitz

from app.pipeline.ingestion.chunker import PageText


def extract_pdf_pages(path: str | Path) -> list[PageText]:
    pages: list[PageText] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document):
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page=index + 1, text=text))
    return pages
