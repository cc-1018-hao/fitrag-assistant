from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.indexing.build_index import run_build_index  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline Chroma index for RAG.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(ROOT / "data" / "raw"),
        help="Directory containing source files (.txt/.md/.json).",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete existing Chroma persistent data before indexing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_build_index(data_dir=args.data_dir, recreate=args.recreate)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
