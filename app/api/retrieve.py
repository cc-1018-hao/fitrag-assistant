from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.retrieval.schemas import RetrieveDebugRequest, RetrieveDebugResponse
from app.retrieval.service import run_hybrid_retrieve_debug

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


@router.post("/debug", response_model=RetrieveDebugResponse)
def retrieve_debug(payload: RetrieveDebugRequest) -> RetrieveDebugResponse:
    try:
        return run_hybrid_retrieve_debug(query=payload.query, top_k=payload.top_k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Retrieve failed: {exc}") from exc
