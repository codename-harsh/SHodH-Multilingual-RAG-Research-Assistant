import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import evaluate as evaluate_api

EVALUATION_SCRIPT = Path(__file__).resolve().parents[2] / "evaluation" / "run_eval.py"
SPEC = importlib.util.spec_from_file_location("shodh_run_eval", EVALUATION_SCRIPT)
run_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_eval)


def test_checked_in_golden_dataset_is_not_mistaken_for_real_evaluation_data():
    entries = run_eval.load_golden()

    with pytest.raises(ValueError, match="placeholder"):
        run_eval.validate(entries)


def test_evaluation_credentials_fail_fast_without_calling_any_provider(monkeypatch):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="COHERE_API_KEY, GEMINI_API_KEY"):
        run_eval.validate_credentials()


def test_evaluation_endpoint_explains_placeholder_dataset_without_starting_subprocess():
    with pytest.raises(HTTPException) as error:
        import asyncio

        asyncio.run(evaluate_api.evaluate())

    assert error.value.status_code == 409
    assert "placeholders" in error.value.detail


def test_evaluation_aggregation_keeps_scores_grouped_without_inventing_values():
    report = run_eval.aggregate([
        {
            "language": "es",
            "document_type": "paper",
            "scores": {
                "faithfulness": 0.8,
                "answer_relevancy": 0.7,
                "context_precision": 0.6,
                "context_recall": 0.5,
            },
        }
    ])

    assert report["overall"]["faithfulness"] == 0.8
    assert report["by_language"]["es"]["context_recall"] == 0.5
    assert report["by_document_type"]["paper"]["answer_relevancy"] == 0.7
