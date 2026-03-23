from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import List, Tuple

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.core.openai_http import build_http_client


def stable_document_id(doc: Document) -> str:
    payload = f"{doc.metadata.get('source', '')}|{doc.metadata.get('chunk_index', '')}|{doc.page_content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        check_embedding_ctx_length=False,
        chunk_size=10,
        http_client=build_http_client(settings),
    )


def build_chroma_index(documents: List[Document], settings: Settings, recreate: bool = False) -> int:
    persist_path = Path(settings.chroma_persist_dir)
    if recreate and persist_path.exists():
        shutil.rmtree(persist_path)

    persist_path.mkdir(parents=True, exist_ok=True)

    vectordb = Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=_get_embeddings(settings),
        persist_directory=str(persist_path),
    )

    ids = []
    for doc in documents:
        chunk_id = stable_document_id(doc)
        doc.metadata["chunk_id"] = chunk_id
        ids.append(chunk_id)
    vectordb.add_documents(documents=documents, ids=ids)
    return len(ids)


def get_chroma_vectorstore(settings: Settings) -> Chroma:
    persist_path = Path(settings.chroma_persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=_get_embeddings(settings),
        persist_directory=str(persist_path),
    )


def vector_search(settings: Settings, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
    vectordb = get_chroma_vectorstore(settings)
    return vectordb.similarity_search_with_score(query=query, k=top_k)


def get_collection_count(settings: Settings) -> int:
    persist_path = Path(settings.chroma_persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_path))
    try:
        collection = client.get_collection(settings.chroma_collection)
    except Exception:  # noqa: BLE001
        return 0
    return int(collection.count())
