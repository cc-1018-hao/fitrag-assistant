from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field

from app.retrieval.schemas import RetrieveHit


class ChatPreprocessRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Conversation session id.")
    query: str = Field(..., min_length=1, description="Original user query.")
    top_k_context_turns: int = Field(default=6, ge=2, le=20, description="How many recent turns to keep.")


class ChatPreprocessResponse(BaseModel):
    session_id: str
    original_query: str
    context_summary: str
    rewritten_query: str
    sub_queries: List[str]
    intent: str
    structured_command: Dict[str, object]


class ChatQueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Conversation session id.")
    query: str = Field(..., min_length=1, description="Original user query.")
    top_k_context_turns: int = Field(default=6, ge=2, le=20, description="How many recent turns to keep.")
    top_k_retrieval: int = Field(default=5, ge=1, le=20, description="How many retrieval results to return.")
    max_sub_queries: int = Field(default=3, ge=1, le=6, description="Maximum sub queries for retrieval.")


class CitationItem(BaseModel):
    id: int
    title: str
    section: str
    publish_date: str
    url: str
    source_type: str
    authors: str
    venue: str
    doi: str
    source: str
    snippet: str


class GeneratedAnswer(BaseModel):
    summary: str
    training_plan: List[str]
    nutrition_plan: List[str]
    recovery_plan: List[str]
    safety_notes: List[str]
    confidence: float
    citations: List[CitationItem]
    answer_markdown: str


class ChatQueryResponse(BaseModel):
    preprocess: ChatPreprocessResponse
    retrieval_query: str
    adaptive_plan: Dict[str, object]
    hits: List[RetrieveHit]
    generated_answer: GeneratedAnswer
