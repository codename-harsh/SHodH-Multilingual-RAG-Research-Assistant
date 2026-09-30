import asyncio
import json
import logging
import os
from pathlib import Path
import sys

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_api_key
from app.core.config import get_settings

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["evaluation"])
logger = logging.getLogger(__name__)


def _evaluation_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "evaluation"
        if (candidate / "run_eval.py").is_file():
            return candidate
    raise HTTPException(status_code=503, detail="Evaluation files are not installed")


def _validate_evaluation_inputs(evaluation_dir: Path) -> None:
    golden_path = evaluation_dir / "golden_dataset" / "questions.json"
    try:
        entries = json.loads(golden_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Golden evaluation dataset is unavailable or invalid") from exc
    if not isinstance(entries, list) or not entries:
        raise HTTPException(status_code=409, detail="Golden evaluation dataset is empty")
    if any("REPLACE_WITH" in json.dumps(entry).upper() for entry in entries):
        raise HTTPException(
            status_code=409,
            detail="Golden dataset still contains placeholders; add real document IDs, answers, and chunk IDs first",
        )
    settings = get_settings()
    missing = [name for name, value in (
        ("COHERE_API_KEY", settings.cohere_api_key),
        ("GEMINI_API_KEY", settings.gemini_api_key),
    ) if not value]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Evaluation requires configured provider credentials: {', '.join(missing)}",
        )


@router.post("/evaluate")
async def evaluate():
    evaluation_dir = _evaluation_dir()
    _validate_evaluation_inputs(evaluation_dir)
    settings = get_settings()
    environment = os.environ.copy()
    environment.update({
        "COHERE_API_KEY": settings.cohere_api_key,
        "GEMINI_API_KEY": settings.gemini_api_key,
        "SHODH_API_KEY": settings.shodh_api_key,
        "SHODH_API_URL": settings.shodh_api_url,
        "GEMINI_EVAL_MODEL": settings.gemini_eval_model,
        "GEMINI_EVAL_EMBED_MODEL": settings.gemini_eval_embed_model,
    })
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(evaluation_dir / "run_eval.py"),
            cwd=str(evaluation_dir.parent),
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=900)
        except TimeoutError as exc:
            proc.kill()
            await proc.communicate()
            raise HTTPException(status_code=504, detail="Evaluation timed out after 15 minutes") from exc
        if proc.returncode != 0:
            logger.error("Evaluation process failed: %s", stderr.decode(errors="replace")[-4000:])
            raise HTTPException(status_code=502, detail="Evaluation failed; inspect backend logs for details")
        report = evaluation_dir / "reports" / "latest.json"
        return json.loads(report.read_text(encoding="utf-8"))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not run evaluation")
        raise HTTPException(status_code=500, detail="Could not run evaluation; inspect backend logs") from exc
