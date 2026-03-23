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
        session_id="validate-point4",
        query="My shoulder hurts during bench press. How can I adjust training safely and recover?",
        top_k_context_turns=6,
        top_k_retrieval=5,
        max_sub_queries=3,
    )
    plan = payload.adaptive_plan
    post = dict(plan.get("postprocess", {}))
    top_hit = payload.hits[0].model_dump() if payload.hits else {}
    checks = {
        "self_rag_enabled": bool(post.get("self_rag_enabled", False)),
        "semantic_rerank_enabled": bool(post.get("semantic_rerank_enabled", False)),
        "round_count_valid": int(post.get("round_count", 0)) >= 1,
        "evidence_eval_exists": isinstance(post.get("evidence_eval", {}), dict),
        "hits_exists": len(payload.hits) > 0,
        "top_hit_has_semantic_score": bool(top_hit and "semantic_rerank_score" in top_hit.get("score_details", {})),
    }

    print(
        json.dumps(
            {
                "passed": all(checks.values()),
                "checks": checks,
                "postprocess": post,
                "top_hit_preview": top_hit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
