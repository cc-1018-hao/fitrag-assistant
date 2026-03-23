from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.indexing.service import get_index_status  # noqa: E402


def main() -> None:
    status = get_index_status()
    validation = {
        "passed": bool(status.get("chroma_count", 0) > 0 and status.get("bm25_count", 0) > 0),
        "checks": {
            "chroma_count_gt_0": bool(status.get("chroma_count", 0) > 0),
            "bm25_count_gt_0": bool(status.get("bm25_count", 0) > 0),
            "bm25_file_exists": bool(status.get("bm25_exists", False)),
        },
        "status": status,
    }
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
