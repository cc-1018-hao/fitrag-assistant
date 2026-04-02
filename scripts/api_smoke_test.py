from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    client = TestClient(app)

    checks = {}

    health = client.get("/health")
    checks["health_200"] = health.status_code == 200 and health.json().get("status") == "ok"

    index_status = client.get("/index/status")
    checks["index_status_200"] = index_status.status_code == 200

    preprocess = client.post(
        "/chat/preprocess",
        json={
            "session_id": "smoke-session",
            "query": "How do I lose fat without losing strength?",
            "top_k_context_turns": 6,
        },
    )
    checks["preprocess_200"] = preprocess.status_code == 200

    chat_query = client.post(
        "/chat/query",
        json={
            "session_id": "smoke-session",
            "query": "How do I lose fat without losing strength?",
            "top_k_context_turns": 6,
            "top_k_retrieval": 5,
            "max_sub_queries": 3,
            "user_profile": {
                "age": 24,
                "sex": "male",
                "height_cm": 176,
                "weight_kg": 79,
                "activity_level": "moderate",
                "primary_goal": "fat_loss",
            },
            "constraints": {
                "days_per_week": 4,
                "session_minutes": 60,
                "equipment": ["barbell", "dumbbell"],
                "injuries": ["shoulder discomfort"],
                "diet_preference": "high protein",
            },
        },
    )
    checks["chat_query_200"] = chat_query.status_code == 200
    cq_json = chat_query.json() if chat_query.status_code == 200 else {}
    checks["chat_query_has_generated"] = bool(cq_json.get("generated_answer"))
    checks["chat_query_has_hits"] = bool(cq_json.get("hits"))
    checks["chat_query_has_weekly_plan"] = bool(cq_json.get("generated_answer", {}).get("weekly_plan"))
    checks["chat_query_has_nutrition_targets"] = bool(cq_json.get("generated_answer", {}).get("nutrition_targets"))

    output = {
        "passed": all(checks.values()),
        "checks": checks,
        "chat_query_preview": {
            "intent": cq_json.get("preprocess", {}).get("intent"),
            "strategy": cq_json.get("adaptive_plan", {}).get("strategy"),
            "confidence": cq_json.get("generated_answer", {}).get("confidence"),
            "citations": len(cq_json.get("generated_answer", {}).get("citations", [])),
            "weekly_days": len(cq_json.get("generated_answer", {}).get("weekly_plan", [])),
            "target_kcal": cq_json.get("generated_answer", {}).get("nutrition_targets", {}).get("calories_kcal"),
        }
        if cq_json
        else None,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
