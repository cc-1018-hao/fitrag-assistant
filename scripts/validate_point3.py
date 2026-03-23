from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.query.service import process_user_query_with_retrieval  # noqa: E402


def main() -> None:
    payload = process_user_query_with_retrieval(
        session_id="validate-point3",
        query="I want to improve squat strength without gaining too much fat. How should I train?",
        top_k_context_turns=6,
        top_k_retrieval=5,
        max_sub_queries=3,
    )
    plan = payload.adaptive_plan
    checks = {
        "adaptive_plan_exists": isinstance(plan, dict) and bool(plan),
        "adaptive_has_strategy": bool(str(plan.get("strategy", "")).strip()),
        "adaptive_has_vector_k": int(plan.get("vector_k", 0)) > 0,
        "adaptive_has_bm25_k": int(plan.get("bm25_k", 0)) > 0,
        "adaptive_has_weights": isinstance(plan.get("weights", {}), dict),
        "retrieval_hits_exists": len(payload.hits) > 0,
        "hit_contains_score_details": bool(payload.hits and payload.hits[0].score_details),
    }
    print(
        json.dumps(
            {
                "passed": all(checks.values()),
                "checks": checks,
                "adaptive_plan": plan,
                "top_hit_preview": payload.hits[0].model_dump() if payload.hits else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
