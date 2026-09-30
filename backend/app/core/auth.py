from fastapi import Header, HTTPException

from app.core.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().shodh_api_key
    if get_settings().app_env.lower() in {"production", "prod"} and not expected:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
