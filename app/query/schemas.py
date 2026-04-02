from __future__ import annotations

from typing import Dict, List, Optional

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


class UserProfile(BaseModel):
    age: Optional[int] = Field(default=None, ge=10, le=90)
    sex: Optional[str] = Field(default=None, description="male/female/unknown")
    height_cm: Optional[float] = Field(default=None, ge=120, le=230)
    weight_kg: Optional[float] = Field(default=None, ge=30, le=250)
    activity_level: Optional[str] = Field(default=None, description="sedentary/light/moderate/high/athlete")
    primary_goal: Optional[str] = Field(default=None)
    training_experience: Optional[str] = Field(default=None, description="beginner/intermediate/advanced")


class PlanConstraints(BaseModel):
    days_per_week: Optional[int] = Field(default=None, ge=1, le=7)
    session_minutes: Optional[int] = Field(default=None, ge=15, le=180)
    equipment: List[str] = Field(default_factory=list)
    injuries: List[str] = Field(default_factory=list)
    diet_preference: Optional[str] = Field(default=None)


class PlanAdjustment(BaseModel):
    adjustment_type: str = Field(default="none", description="none/limited_time/pain/no_equipment/plateau/travel")
    note: str = Field(default="")


class ChatQueryRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Conversation session id.")
    query: str = Field(..., min_length=1, description="Original user query.")
    top_k_context_turns: int = Field(default=6, ge=2, le=20, description="How many recent turns to keep.")
    top_k_retrieval: int = Field(default=5, ge=1, le=20, description="How many retrieval results to return.")
    max_sub_queries: int = Field(default=3, ge=1, le=6, description="Maximum sub queries for retrieval.")
    user_profile: Optional[UserProfile] = Field(default=None, description="Optional user profile for personalization.")
    constraints: Optional[PlanConstraints] = Field(default=None, description="Optional constraints for executable plans.")
    adjustment: Optional[PlanAdjustment] = Field(default=None, description="Optional one-shot adjustment instruction.")


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
    quality_score: float = 0.0
    freshness_level: str = "unknown"
    evidence_note: str = ""


class ActionItem(BaseModel):
    domain: str
    title: str
    detail: str
    citation_ids: List[int] = Field(default_factory=list)
    priority: str = "medium"


class WeeklySession(BaseModel):
    day: str
    focus: str
    duration_minutes: int
    plan: List[str] = Field(default_factory=list)
    nutrition_focus: List[str] = Field(default_factory=list)
    citation_ids: List[int] = Field(default_factory=list)


class NutritionTargets(BaseModel):
    calories_kcal: int = 0
    protein_g: int = 0
    carbs_g: int = 0
    fat_g: int = 0
    hydration_ml: int = 0
    note: str = ""


class SafetyAlert(BaseModel):
    risk_level: str = "low"
    message: str
    action: str


class GeneratedAnswer(BaseModel):
    summary: str
    training_plan: List[str]
    nutrition_plan: List[str]
    recovery_plan: List[str]
    safety_notes: List[str]
    confidence: float
    citations: List[CitationItem]
    answer_markdown: str
    action_items: List[ActionItem] = Field(default_factory=list)
    weekly_plan: List[WeeklySession] = Field(default_factory=list)
    nutrition_targets: NutritionTargets = Field(default_factory=NutritionTargets)
    safety_alerts: List[SafetyAlert] = Field(default_factory=list)
    progress_tracking_tips: List[str] = Field(default_factory=list)


class ChatQueryResponse(BaseModel):
    preprocess: ChatPreprocessResponse
    retrieval_query: str
    adaptive_plan: Dict[str, object]
    hits: List[RetrieveHit]
    generated_answer: GeneratedAnswer
