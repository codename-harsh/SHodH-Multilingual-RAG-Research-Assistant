import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["evaluation"])


@router.post("/evaluate")
async def evaluate():
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "evaluation/run_eval.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode()[-4000:])
        report = Path("evaluation/reports/latest.json")
        return json.loads(report.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
