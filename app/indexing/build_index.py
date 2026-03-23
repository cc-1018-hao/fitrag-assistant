from __future__ import annotations

from app.core.config import get_settings
from app.ingest.chunker import chunk_documents
from app.ingest.loaders import load_documents
from app.indexing.bm25_store import write_bm25_corpus
from app.indexing.chroma_indexer import build_chroma_index


def run_build_index(data_dir: str, recreate: bool = False) -> dict:
    settings = get_settings()
    documents = load_documents(data_dir=data_dir)
    if not documents:
        return {
            "status": "empty",
            "loaded_documents": 0,
            "chunk_count": 0,
            "indexed_count": 0,
        }

    chunks = chunk_documents(
        documents=documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    indexed_count = build_chroma_index(documents=chunks, settings=settings, recreate=recreate)
    bm25_count = write_bm25_corpus(documents=chunks, settings=settings)
    return {
        "status": "ok",
        "loaded_documents": len(documents),
        "chunk_count": len(chunks),
        "indexed_count": indexed_count,
        "bm25_count": bm25_count,
        "collection": settings.chroma_collection,
        "persist_dir": settings.chroma_persist_dir,
        "bm25_corpus_path": settings.bm25_corpus_path,
        "embedding_model": settings.embedding_model,
    }
