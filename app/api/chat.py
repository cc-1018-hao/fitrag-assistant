from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.query.schemas import ChatPreprocessRequest, ChatPreprocessResponse, ChatQueryRequest, ChatQueryResponse
from app.query.service import preprocess_user_query, process_user_query_with_retrieval

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/preprocess", response_model=ChatPreprocessResponse)
def chat_preprocess(payload: ChatPreprocessRequest) -> ChatPreprocessResponse:
    try:
        return preprocess_user_query(
            session_id=payload.session_id,
            query=payload.query,
            top_k_context_turns=payload.top_k_context_turns,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat preprocess failed: {exc}") from exc


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(payload: ChatQueryRequest) -> ChatQueryResponse:
    try:
        return process_user_query_with_retrieval(
            session_id=payload.session_id,
            query=payload.query,
            top_k_context_turns=payload.top_k_context_turns,
            top_k_retrieval=payload.top_k_retrieval,
            max_sub_queries=payload.max_sub_queries,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat query failed: {exc}") from exc
