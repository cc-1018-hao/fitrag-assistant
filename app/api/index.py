from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.indexing.service import get_index_status

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/status")
def index_status() -> dict:
    try:
        return get_index_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Index status failed: {exc}") from exc
