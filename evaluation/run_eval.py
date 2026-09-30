"""Run the Shodh golden-set evaluation against the live API."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

import requests
from jinja2 import Template

GOLDEN_PATH = Path(__file__).parent / "golden_dataset" / "questions.json"
REPORT_DIR = Path(__file__).parent / "reports"
API_URL = os.getenv("SHODH_API_URL", "http://localhost:8000")
API_HEADERS = {"X-API-Key": os.environ["SHODH_API_KEY"]} if os.getenv("SHODH_API_KEY") else {}


def load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def validate(entries: list[dict]) -> None:
    placeholders = [entry for entry in entries if "REPLACE_WITH" in json.dumps(entry)]
    if placeholders:
        raise ValueError(f"Golden dataset still contains {len(placeholders)} placeholder entries")


def run_queries(entries: list[dict]) -> list[dict]:
    rows = []
    for entry in entries:
        response = requests.post(
            f"{API_URL}/query",
            json={"question": entry["question"], "doc_id": entry["doc_id"]},
            timeout=180,
            headers=API_HEADERS,
        )
        response.raise_for_status()
        result = response.json()
        rows.append({**entry, "prediction": result})
    return rows


def ragas_scores(rows: list[dict]) -> list[dict]:
    from datasets import Dataset
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

    evaluator_llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_EVAL_MODEL", "gemini-2.0-flash"),
            google_api_key=os.environ["GEMINI_API_KEY"],
            temperature=0.0,
        )
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        GoogleGenerativeAIEmbeddings(
            model=os.getenv("GEMINI_EVAL_EMBED_MODEL", "models/text-embedding-004"),
            google_api_key=os.environ["GEMINI_API_KEY"],
        )
    )
    dataset = Dataset.from_list(
        [
            {
                "question": row["question"],
                "answer": row["prediction"]["answer"],
                "contexts": [c["text"] for c in row["prediction"].get("retrieved_context", [])],
                "ground_truth": row["expected_answer"],
            }
            for row in rows
        ]
    )
    result = evaluate(
        dataset,
        metrics=[Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    values = result.to_pandas().to_dict(orient="records")
    keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    for row, score in zip(rows, values, strict=True):
        row["scores"] = {key: float(score.get(key, 0.0) or 0.0) for key in keys}
    return rows


def aggregate(rows: list[dict]) -> dict:
    def mean(items, key):
        values = [item["scores"][key] for item in items]
        return sum(values) / len(values) if values else 0.0

    languages = defaultdict(list)
    doc_types = defaultdict(list)
    for row in rows:
        languages[row["language"]].append(row)
        doc_types[row.get("document_type", "unspecified")].append(row)

    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    return {
        "overall": {metric: mean(rows, metric) for metric in metrics},
        "by_language": {lang: {metric: mean(items, metric) for metric in metrics} for lang, items in languages.items()},
        "by_document_type": {kind: {metric: mean(items, metric) for metric in metrics} for kind, items in doc_types.items()},
        "rows": rows,
    }


def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    template = Template("""
<!doctype html><html><head><meta charset="utf-8"><title>Shodh Evaluation</title>
<style>body{font:14px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ddd;padding:10px;text-align:left}th{background:#f5f5f5}</style>
</head><body><h1>Shodh Evaluation</h1><table><tr><th>Language</th><th>Faithfulness</th><th>Answer relevancy</th><th>Context precision</th><th>Context recall</th></tr>
{% for lang, scores in by_language.items() %}<tr><td>{{ lang }}</td>{% for key in metrics %}<td>{{ '%.3f'|format(scores[key]) }}</td>{% endfor %}</tr>{% endfor %}</table></body></html>
""")
    (REPORT_DIR / "latest.html").write_text(template.render(by_language=report["by_language"], metrics=["faithfulness", "answer_relevancy", "context_precision", "context_recall"]), encoding="utf-8")


def main() -> None:
    entries = load_golden()
    validate(entries)
    rows = ragas_scores(run_queries(entries))
    report = aggregate(rows)
    write_report(report)
    print(json.dumps(report["by_language"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
