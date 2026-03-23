from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.indexing.bm25_store import read_bm25_corpus
from app.indexing.chroma_indexer import get_collection_count


def get_index_status() -> dict:
    settings = get_settings(require_api_key=False)
    chroma_count = get_collection_count(settings)
    bm25_records = read_bm25_corpus(settings.bm25_corpus_path)
    return {
        "status": "ok",
        "collection": settings.chroma_collection,
        "chroma_count": chroma_count,
        "bm25_count": len(bm25_records),
        "chroma_persist_dir": settings.chroma_persist_dir,
        "bm25_corpus_path": settings.bm25_corpus_path,
        "bm25_exists": Path(settings.bm25_corpus_path).exists(),
    }
