from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RetrieveDebugRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query for retrieval.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return.")


class RetrieveHit(BaseModel):
    rank: int
    score: float
    retrieval_sources: List[str]
    score_details: Dict[str, float]
    content: str
    metadata: Dict[str, Any]


class RetrieveDebugResponse(BaseModel):
    query: str
    top_k: int
    collection: str
    hits: List[RetrieveHit]
