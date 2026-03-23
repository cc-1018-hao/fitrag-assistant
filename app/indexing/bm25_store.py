from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from langchain_core.documents import Document

from app.core.config import Settings
from app.indexing.chroma_indexer import stable_document_id


def write_bm25_corpus(documents: List[Document], settings: Settings) -> int:
    target_path = Path(settings.bm25_corpus_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as f:
        for doc in documents:
            chunk_id = str(doc.metadata.get("chunk_id") or stable_document_id(doc))
            record: Dict[str, object] = {
                "chunk_id": chunk_id,
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(documents)


def read_bm25_corpus(corpus_path: str) -> List[Dict[str, object]]:
    path = Path(corpus_path)
    if not path.exists():
        return []

    records: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records
