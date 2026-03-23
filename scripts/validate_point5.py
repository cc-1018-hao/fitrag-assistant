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
        session_id="validate-point5",
        query="How can I lose fat while keeping strength and avoiding shoulder overuse?",
        top_k_context_turns=6,
        top_k_retrieval=5,
        max_sub_queries=3,
    )
    generated = payload.generated_answer
    checks = {
        "summary_not_empty": bool(generated.summary.strip()),
        "training_plan_exists": len(generated.training_plan) > 0,
        "nutrition_plan_exists": len(generated.nutrition_plan) > 0,
        "recovery_plan_exists": len(generated.recovery_plan) > 0,
        "safety_notes_exists": len(generated.safety_notes) > 0,
        "confidence_valid": 0.0 <= float(generated.confidence) <= 1.0,
        "citations_exists": len(generated.citations) > 0,
        "markdown_not_empty": bool(generated.answer_markdown.strip()),
    }
    print(
        json.dumps(
            {
                "passed": all(checks.values()),
                "checks": checks,
                "generated_preview": generated.model_dump(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
