from __future__ import annotations

import json
import re
from typing import Dict, List

from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.core.openai_http import build_http_client


INTENT_CANDIDATES = {
    "fat_loss",
    "muscle_gain",
    "strength",
    "nutrition",
    "recovery",
    "injury_prevention",
    "general_fitness",
}


def _build_context_text(messages: List[dict]) -> str:
    if not messages:
        return "(no_history)"
    lines: List[str] = []
    for m in messages:
        role = str(m.get("role", "user")).strip() or "user"
        content = str(m.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(no_history)"


def _detect_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["calorie", "protein", "carb", "fat", "macro", "diet", "nutrition"]):
        return "nutrition"
    if any(k in q for k in ["fat loss", "cut", "lose weight", "deficit"]):
        return "fat_loss"
    if any(k in q for k in ["muscle gain", "hypertrophy", "bulk"]):
        return "muscle_gain"
    if any(k in q for k in ["strength", "1rm", "squat", "deadlift", "bench"]):
        return "strength"
    if any(k in q for k in ["recovery", "sleep", "deload", "soreness"]):
        return "recovery"
    if any(k in q for k in ["injury", "pain", "warmup", "mobility", "safe"]):
        return "injury_prevention"
    return "general_fitness"


def _fallback_rewrite(query: str, context_summary: str) -> Dict[str, object]:
    return {
        "context_summary": context_summary[:500] if context_summary else "No prior context.",
        "rewritten_query": query.strip(),
        "sub_queries": [query.strip()],
        "intent": _detect_intent(query),
        "entities": {
            "goal": [],
            "muscle_group": [],
            "food": [],
            "equipment": [],
            "limitation": [],
        },
    }


def _extract_json_from_text(text: str) -> Dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass

    left = cleaned.find("{")
    right = cleaned.rfind("}")
    if left >= 0 and right > left:
        maybe_json = cleaned[left : right + 1]
        data = json.loads(maybe_json)
        if isinstance(data, dict):
            return data
    raise ValueError("Cannot parse planner JSON output")


def rewrite_query_with_context(settings: Settings, query: str, recent_messages: List[dict]) -> Dict[str, object]:
    context_text = _build_context_text(recent_messages)
    prompt = (
        "You are a fitness and sports-nutrition RAG query planner.\n"
        "Given conversation history and current question, compress context and produce a retrieval-ready query plan.\n"
        "Return ONLY a JSON object with keys:\n"
        "context_summary: string (1-3 concise sentences)\n"
        "rewritten_query: string (clear and retrieval-friendly)\n"
        "sub_queries: string[] (1-4 executable sub-questions)\n"
        "intent: one of fat_loss/muscle_gain/strength/nutrition/recovery/injury_prevention/general_fitness\n"
        "entities: {goal:string[], muscle_group:string[], food:string[], equipment:string[], limitation:string[]}\n\n"
        f"history:\n{context_text}\n\n"
        f"current_question:\n{query}\n"
    )

    llm = ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=0,
        http_client=build_http_client(settings),
    )

    try:
        raw = llm.invoke(prompt).content
        data = _extract_json_from_text(str(raw))

        rewritten_query = str(data.get("rewritten_query", "")).strip() or query.strip()
        sub_queries = [str(x).strip() for x in data.get("sub_queries", []) if str(x).strip()] or [rewritten_query]
        intent = str(data.get("intent", _detect_intent(query))).strip().lower()
        if intent not in INTENT_CANDIDATES:
            intent = _detect_intent(query)

        entities = data.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}
        normalized_entities = {
            "goal": [str(x).strip() for x in entities.get("goal", []) if str(x).strip()],
            "muscle_group": [str(x).strip() for x in entities.get("muscle_group", []) if str(x).strip()],
            "food": [str(x).strip() for x in entities.get("food", []) if str(x).strip()],
            "equipment": [str(x).strip() for x in entities.get("equipment", []) if str(x).strip()],
            "limitation": [str(x).strip() for x in entities.get("limitation", []) if str(x).strip()],
        }

        return {
            "context_summary": str(data.get("context_summary", "")).strip() or "No prior context.",
            "rewritten_query": rewritten_query,
            "sub_queries": sub_queries[:4],
            "intent": intent,
            "entities": normalized_entities,
        }
    except Exception:  # noqa: BLE001
        return _fallback_rewrite(query=query, context_summary=context_text)
