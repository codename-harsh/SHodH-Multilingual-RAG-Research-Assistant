from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass(frozen=True)
class Chunk:
    page: int
    chunk_id: str
    text: str


_encoding = tiktoken.get_encoding("cl100k_base")


def token_length(text: str) -> int:
    return len(_encoding.encode(text))


def chunk_pages(pages: list[PageText], chunk_size: int = 512, chunk_overlap: int = 128) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=token_length,
        separators=["\n\n", "\n", ". ", " ", ""],
        strip_whitespace=True,
    )

    chunks: list[Chunk] = []
    for page in pages:
        for index, text in enumerate(splitter.split_text(page.text)):
            if not text.strip():
                continue
            chunks.append(Chunk(page=page.page, chunk_id=f"p{page.page}-c{index}", text=text))
    return chunks
