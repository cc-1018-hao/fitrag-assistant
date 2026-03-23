from __future__ import annotations

from typing import List

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.core.openai_http import build_http_client
from app.retrieval.schemas import RetrieveHit


def _dot(a: List[float], b: List[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _norm(a: List[float]) -> float:
    return float(sum(x * x for x in a) ** 0.5)


def _cosine(a: List[float], b: List[float]) -> float:
    na = _norm(a)
    nb = _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return _dot(a, b) / (na * nb)


def semantic_rerank(settings: Settings, query: str, hits: List[RetrieveHit], top_k: int) -> List[RetrieveHit]:
    if not hits:
        return []

    try:
        embedder = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            check_embedding_ctx_length=False,
            http_client=build_http_client(settings),
        )
        query_vec = embedder.embed_query(query)
        doc_vecs = embedder.embed_documents([h.content for h in hits])
    except Exception:  # noqa: BLE001
        # Fallback: keep RRF ranking and annotate missing semantic rerank.
        ranked = hits[:top_k]
        for idx, hit in enumerate(ranked, start=1):
            hit.rank = idx
            hit.score_details["semantic_rerank_score"] = 0.0
            hit.score_details["semantic_rerank_skipped"] = 1.0
        return ranked

    scored: List[tuple[RetrieveHit, float]] = []
    for hit, dvec in zip(hits, doc_vecs):
        sem_score = float(_cosine(query_vec, dvec))
        hit.score_details["semantic_rerank_score"] = sem_score
        hit.score += sem_score
        scored.append((hit, sem_score))

    ranked = [x[0] for x in sorted(scored, key=lambda x: x[0].score, reverse=True)[:top_k]]
    for idx, hit in enumerate(ranked, start=1):
        hit.rank = idx
    return ranked
