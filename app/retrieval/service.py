from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

from app.core.config import get_settings
from app.indexing.bm25_store import read_bm25_corpus
from app.indexing.chroma_indexer import vector_search
from app.retrieval.adaptive_router import build_adaptive_plan
from app.retrieval.hybrid import bm25_search, rrf_fuse
from app.retrieval.postprocess import semantic_rerank
from app.retrieval.schemas import RetrieveDebugResponse, RetrieveHit


def _fallback_chunk_id(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _run_hybrid_retrieve_with_plan(query: str, top_k: int, plan: Dict[str, object]) -> list[RetrieveHit]:
    settings = get_settings()
    vector_k = int(plan.get("vector_k", top_k))
    bm25_k = int(plan.get("bm25_k", top_k))
    weights = dict(plan.get("weights", {}))

    # Be resilient to temporary embedding API/network issues:
    # retrieval can still proceed with BM25 fallback.
    try:
        vector_results = vector_search(settings=settings, query=query, top_k=vector_k)
    except Exception:  # noqa: BLE001
        vector_results = []
    bm25_records = read_bm25_corpus(settings.bm25_corpus_path)
    bm25_results = bm25_search(records=bm25_records, query=query, top_k=bm25_k)

    vector_rank_map: Dict[str, int] = {}
    vector_meta_map: Dict[str, Tuple[str, dict, float]] = {}
    for rank, (doc, score) in enumerate(vector_results, start=1):
        chunk_id = str(doc.metadata.get("chunk_id", "")).strip() or _fallback_chunk_id(doc.page_content)
        vector_rank_map[chunk_id] = rank
        vector_meta_map[chunk_id] = (doc.page_content, doc.metadata, float(score))

    bm25_rank_map: Dict[str, int] = {}
    bm25_meta_map: Dict[str, Tuple[str, dict, float]] = {}
    for hit in bm25_results:
        chunk_id = hit.chunk_id.strip() or _fallback_chunk_id(hit.content)
        bm25_rank_map[chunk_id] = hit.rank
        bm25_meta_map[chunk_id] = (hit.content, hit.metadata, float(hit.score))

    fused_scores = rrf_fuse({"vector": vector_rank_map, "bm25": bm25_rank_map}, weights=weights)
    ranked_chunk_ids = [chunk_id for chunk_id, _ in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]]

    hits: List[RetrieveHit] = []
    for i, chunk_id in enumerate(ranked_chunk_ids, start=1):
        vector_info = vector_meta_map.get(chunk_id)
        bm25_info = bm25_meta_map.get(chunk_id)
        content = (vector_info or bm25_info or ("", {}, 0.0))[0]
        metadata = (vector_info or bm25_info or ("", {}, 0.0))[1]

        sources: List[str] = []
        details: Dict[str, float] = {"rrf": float(fused_scores.get(chunk_id, 0.0))}
        if vector_info is not None:
            sources.append("vector")
            details["vector_distance"] = vector_info[2]
            details["vector_weight"] = float(weights.get("vector", 1.0))
        if bm25_info is not None:
            sources.append("bm25")
            details["bm25_score"] = bm25_info[2]
            details["bm25_weight"] = float(weights.get("bm25", 1.0))
        details["vector_k"] = float(vector_k)
        details["bm25_k"] = float(bm25_k)

        hits.append(
            RetrieveHit(
                rank=i,
                score=float(fused_scores.get(chunk_id, 0.0)),
                retrieval_sources=sources,
                score_details=details,
                content=content,
                metadata=metadata,
            )
        )

    return hits


def _assess_evidence(query: str, hits: List[RetrieveHit]) -> tuple[bool, Dict[str, object]]:
    if not hits:
        return False, {"reason": "no_hits", "top_score": 0.0}

    top_score = float(hits[0].score)
    hit_with_dual_source = any(len(h.retrieval_sources) >= 2 for h in hits[:3])
    token_overlap = 0
    query_tokens = [x for x in query.lower().split() if x]
    if query_tokens:
        top_text = hits[0].content.lower()
        token_overlap = sum(1 for t in query_tokens if t in top_text)
    overlap_ratio = float(token_overlap / max(1, len(query_tokens)))

    sufficient = bool(top_score >= 0.02 and (hit_with_dual_source or overlap_ratio >= 0.2))
    return sufficient, {
        "reason": "score_and_coverage_check",
        "top_score": top_score,
        "dual_source_top3": hit_with_dual_source,
        "overlap_ratio": overlap_ratio,
    }


def _expand_query_for_self_rag(query: str, intent: str) -> str:
    if intent == "fat_loss":
        return f"{query} calorie deficit protein target satiety weekly adjustment"
    if intent == "muscle_gain":
        return f"{query} hypertrophy volume progression recovery protein surplus"
    if intent == "strength":
        return f"{query} strength progression sets reps intensity periodization"
    if intent == "nutrition":
        return f"{query} macros calories meal timing evidence guideline"
    if intent == "recovery":
        return f"{query} sleep stress deload soreness management"
    if intent == "injury_prevention":
        return f"{query} warmup technique load management contraindication"
    return f"{query} training nutrition guideline evidence"


def run_hybrid_retrieve_debug(query: str, top_k: int) -> RetrieveDebugResponse:
    settings = get_settings()
    plan = build_adaptive_plan(intent="general_fitness", query=query, top_k=top_k, need_multi_hop=False)
    hits = _run_hybrid_retrieve_with_plan(query=query, top_k=top_k, plan=plan)
    return RetrieveDebugResponse(
        query=query,
        top_k=top_k,
        collection=settings.chroma_collection,
        hits=hits,
    )


def run_hybrid_retrieve(query: str, top_k: int) -> list[RetrieveHit]:
    plan = build_adaptive_plan(intent="general_fitness", query=query, top_k=top_k, need_multi_hop=False)
    return _run_hybrid_retrieve_with_plan(query=query, top_k=top_k, plan=plan)


def run_adaptive_hybrid_retrieve(
    query: str,
    intent: str,
    top_k: int,
    need_multi_hop: bool,
) -> tuple[list[RetrieveHit], Dict[str, object]]:
    plan = build_adaptive_plan(intent=intent, query=query, top_k=top_k, need_multi_hop=need_multi_hop)
    hits = _run_hybrid_retrieve_with_plan(query=query, top_k=top_k, plan=plan)
    return hits, plan


def run_self_rag_retrieve(
    query: str,
    intent: str,
    top_k: int,
    need_multi_hop: bool,
) -> tuple[list[RetrieveHit], Dict[str, object]]:
    settings = get_settings()
    plan = build_adaptive_plan(intent=intent, query=query, top_k=top_k, need_multi_hop=need_multi_hop)
    first_hits = _run_hybrid_retrieve_with_plan(query=query, top_k=top_k, plan=plan)
    is_sufficient, evidence_eval = _assess_evidence(query=query, hits=first_hits)

    all_hits = list(first_hits)
    round_count = 1
    expanded_query = ""
    if not is_sufficient:
        round_count = 2
        expanded_query = _expand_query_for_self_rag(query=query, intent=intent)
        second_plan = build_adaptive_plan(
            intent=intent,
            query=expanded_query,
            top_k=min(20, top_k + 2),
            need_multi_hop=True,
        )
        second_hits = _run_hybrid_retrieve_with_plan(
            query=expanded_query,
            top_k=min(20, top_k + 2),
            plan=second_plan,
        )
        all_hits.extend(second_hits)

    dedup: Dict[str, RetrieveHit] = {}
    for hit in all_hits:
        key = hit.metadata.get("chunk_id", "") or _fallback_chunk_id(hit.content)
        key = str(key)
        if key not in dedup or dedup[key].score < hit.score:
            dedup[key] = hit

    merged = sorted(dedup.values(), key=lambda x: x.score, reverse=True)[: max(top_k * 2, top_k)]
    reranked = semantic_rerank(settings=settings, query=query, hits=merged, top_k=top_k)

    retrieval_meta = {
        "mode": "self_rag",
        "round_count": round_count,
        "evidence_eval": evidence_eval,
        "expanded_query": expanded_query,
        "initial_plan": plan,
    }
    return reranked, retrieval_meta
