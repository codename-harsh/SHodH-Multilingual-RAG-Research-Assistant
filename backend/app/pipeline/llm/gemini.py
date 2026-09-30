from google import genai
from google.genai import types

from app.core.config import get_settings
from app.pipeline.llm.citations import remove_unverified_citations

SYSTEM_PROMPT = """You are Shodh, a grounded research assistant.
Answer ONLY from the provided context.
Cite sources inline as [page X, chunk Y].
If the answer is not in the context, say so explicitly.
Answer in the same language the user asked in.
Do not invent citations or facts that are absent from the context.
"""


class GeminiGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def generate(self, question: str, chunks: list[dict]) -> str:
        context = "\n\n".join(
            f"[page {chunk['page']}, chunk {chunk['chunk_id']}]\n{chunk['text']}"
            for chunk in chunks
        )
        prompt = f"RETRIEVED CONTEXT:\n{context}\n\nUSER QUESTION:\n{question}"
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )
        answer = response.text or "The answer is not present in the provided context."
        return remove_unverified_citations(answer, chunks)
