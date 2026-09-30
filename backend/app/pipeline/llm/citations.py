import re


_CITATION = re.compile(r"\[\s*page\s+(\d+)\s*,\s*chunk\s+([^\]]+)\]", re.IGNORECASE)


def remove_unverified_citations(answer: str, chunks: list[dict]) -> str:
    """Remove inline page/chunk references absent from the supplied context."""
    allowed = {(int(chunk["page"]), str(chunk["chunk_id"])) for chunk in chunks}

    def keep_if_verified(match: re.Match[str]) -> str:
        page = int(match.group(1))
        chunk_id = match.group(2).strip()
        return match.group(0) if (page, chunk_id) in allowed else ""

    return _CITATION.sub(keep_if_verified, answer)
