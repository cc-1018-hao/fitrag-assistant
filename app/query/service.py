from __future__ import annotations

from typing import Dict, List

from app.core.config import get_settings
from app.generation.service import generate_answer_from_hits
from app.query.rewrite import rewrite_query_with_context
from app.query.schemas import ChatPreprocessResponse, ChatQueryResponse
from app.query.session_store import session_store
from app.retrieval.schemas import RetrieveHit
from app.retrieval.service import run_self_rag_retrieve


def preprocess_user_query(session_id: str, query: str, top_k_context_turns: int) -> ChatPreprocessResponse:
    settings = get_settings()
    recent_messages = session_store.get_recent_messages(session_id=session_id, max_turns=top_k_context_turns)

    rewritten = rewrite_query_with_context(settings=settings, query=query, recent_messages=recent_messages)
    structured_command = {
        "intent": rewritten["intent"],
        "retrieval_query": rewritten["rewritten_query"],
        "sub_queries": rewritten["sub_queries"],
        "entities": rewritten.get("entities", {}),
        "router_hints": {
            "need_multi_hop": len(rewritten["sub_queries"]) > 1,
            "prefer_hybrid_retrieval": True,
        },
        "constraints": {
            "domain": "fitness_nutrition",
            "must_cite_sources": True,
            "safety_first": True,
        },
    }

    session_store.add_user_message(session_id=session_id, content=query)
    session_store.add_assistant_message(session_id=session_id, content=rewritten["rewritten_query"])

    return ChatPreprocessResponse(
        session_id=session_id,
        original_query=query,
        context_summary=rewritten["context_summary"],
        rewritten_query=rewritten["rewritten_query"],
        sub_queries=rewritten["sub_queries"],
        intent=rewritten["intent"],
        structured_command=structured_command,
    )


def _merge_hits(hit_groups: List[List[RetrieveHit]], top_k: int) -> List[RetrieveHit]:
    # Aggregate by exact content as a simple stable dedup key.
    merged: Dict[str, RetrieveHit] = {}
    for hits in hit_groups:
        for hit in hits:
            key = hit.content.strip()
            if key not in merged:
                merged[key] = RetrieveHit(
                    rank=0,
                    score=hit.score,
                    retrieval_sources=list(hit.retrieval_sources),
                    score_details=dict(hit.score_details),
                    content=hit.content,
                    metadata=hit.metadata,
                )
            else:
                existing = merged[key]
                existing.score += hit.score
                existing.retrieval_sources = sorted(set(existing.retrieval_sources + hit.retrieval_sources))
                for score_key, score_value in hit.score_details.items():
                    existing.score_details[score_key] = max(existing.score_details.get(score_key, score_value), score_value)

    ranked = sorted(merged.values(), key=lambda x: x.score, reverse=True)[:top_k]
    for idx, hit in enumerate(ranked, start=1):
        hit.rank = idx
    return ranked


def process_user_query_with_retrieval(
    session_id: str,
    query: str,
    top_k_context_turns: int,
    top_k_retrieval: int,
    max_sub_queries: int,
    user_profile: Dict[str, object] | None = None,
    constraints: Dict[str, object] | None = None,
    adjustment: Dict[str, object] | None = None,
) -> ChatQueryResponse:
    preprocess = preprocess_user_query(
        session_id=session_id,
        query=query,
        top_k_context_turns=top_k_context_turns,
    )

    sub_queries = preprocess.sub_queries[:max_sub_queries]
    intent = preprocess.intent
    need_multi_hop = bool(preprocess.structured_command.get("router_hints", {}).get("need_multi_hop", False))
    retrieval_queries = [preprocess.rewritten_query] + [q for q in sub_queries if q != preprocess.rewritten_query]
    hit_groups: List[List[RetrieveHit]] = []
    retrieval_metas: List[Dict[str, object]] = []
    for rq in retrieval_queries:
        hits, meta = run_self_rag_retrieve(
            query=rq,
            intent=intent,
            top_k=top_k_retrieval,
            need_multi_hop=need_multi_hop,
        )
        hit_groups.append(hits)
        retrieval_metas.append(meta)

    merged_hits = _merge_hits(hit_groups=hit_groups, top_k=top_k_retrieval)
    final_plan = retrieval_metas[0].get("initial_plan", {}) if retrieval_metas else {
        "strategy": "balanced",
        "intent": intent,
        "vector_k": top_k_retrieval,
        "bm25_k": top_k_retrieval,
        "top_k_final": top_k_retrieval,
        "weights": {"vector": 1.0, "bm25": 1.0},
        "need_multi_hop": need_multi_hop,
    }
    final_plan["postprocess"] = {
        "self_rag_enabled": True,
        "semantic_rerank_enabled": True,
        "round_count": retrieval_metas[0].get("round_count", 1) if retrieval_metas else 1,
        "expanded_query": retrieval_metas[0].get("expanded_query", "") if retrieval_metas else "",
        "evidence_eval": retrieval_metas[0].get("evidence_eval", {}) if retrieval_metas else {},
    }
    return ChatQueryResponse(
        preprocess=preprocess,
        retrieval_query=preprocess.rewritten_query,
        adaptive_plan=final_plan,
        hits=merged_hits,
        generated_answer=generate_answer_from_hits(
            query=query,
            intent=intent,
            hits=merged_hits,
            user_profile=user_profile or {},
            constraints=constraints or {},
            adjustment=adjustment or {},
        ),
    )
