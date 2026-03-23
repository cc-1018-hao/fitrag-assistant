from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.query.service import preprocess_user_query  # noqa: E402


def main() -> None:
    session_id = "validate-point2"
    query = "I want to lose fat while keeping muscle. How should I set calories and protein?"
    result = preprocess_user_query(session_id=session_id, query=query, top_k_context_turns=6)

    checks = {
        "context_summary_not_empty": bool(result.context_summary.strip()),
        "rewritten_query_not_empty": bool(result.rewritten_query.strip()),
        "sub_queries_exists": bool(len(result.sub_queries) >= 1),
        "intent_not_empty": bool(result.intent.strip()),
        "structured_command_has_retrieval_query": bool(
            str(result.structured_command.get("retrieval_query", "")).strip()
        ),
        "structured_command_has_entities": isinstance(result.structured_command.get("entities", {}), dict),
    }
    payload = {
        "passed": all(checks.values()),
        "checks": checks,
        "result": result.model_dump(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
