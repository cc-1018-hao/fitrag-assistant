from __future__ import annotations

import re
from typing import Dict


_NUMERIC_RE = re.compile(r"\d+(\.\d+)?")


def build_adaptive_plan(intent: str, query: str, top_k: int, need_multi_hop: bool) -> Dict[str, object]:
    normalized_intent = (intent or "general_fitness").strip().lower()
    query_lower = (query or "").lower()

    vector_k = top_k
    bm25_k = top_k
    vector_weight = 1.0
    bm25_weight = 1.0
    strategy = "balanced"

    has_numeric = bool(_NUMERIC_RE.search(query))
    has_nutrition_keywords = any(k in query_lower for k in ["calorie", "protein", "carb", "fat", "macro", "g/day"])
    has_exercise_keywords = any(k in query_lower for k in ["squat", "bench", "deadlift", "sets", "reps", "rpe"])
    has_risk_keywords = any(k in query_lower for k in ["pain", "injury", "risk", "warning", "contraindication"])

    if normalized_intent in {"nutrition", "fat_loss"} or has_nutrition_keywords or has_numeric:
        strategy = "nutrition_priority"
        vector_k = max(3, top_k - 1)
        bm25_k = min(20, top_k + 3)
        vector_weight = 0.9
        bm25_weight = 1.3
    elif normalized_intent in {"strength", "muscle_gain"} or has_exercise_keywords:
        strategy = "programming_priority"
        vector_k = min(20, top_k + 3)
        bm25_k = max(3, top_k - 1)
        vector_weight = 1.35
        bm25_weight = 0.9
    elif normalized_intent in {"injury_prevention", "recovery"} or has_risk_keywords:
        strategy = "safety_balanced"
        vector_k = min(20, top_k + 1)
        bm25_k = min(20, top_k + 2)
        vector_weight = 1.1
        bm25_weight = 1.2

    if need_multi_hop:
        vector_k = min(20, vector_k + 2)
        bm25_k = min(20, bm25_k + 2)

    return {
        "strategy": strategy,
        "intent": normalized_intent,
        "vector_k": int(vector_k),
        "bm25_k": int(bm25_k),
        "top_k_final": int(top_k),
        "weights": {
            "vector": float(vector_weight),
            "bm25": float(bm25_weight),
        },
        "need_multi_hop": bool(need_multi_hop),
    }
