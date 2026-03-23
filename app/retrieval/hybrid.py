from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

from rank_bm25 import BM25Okapi


_WORD_RE = re.compile(r"[a-zA-Z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> List[str]:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    cjk_chars = _CJK_RE.findall(text)
    tokens = words + cjk_chars
    if tokens:
        return tokens
    return list(text.strip())


@dataclass
class BM25Hit:
    chunk_id: str
    content: str
    metadata: Dict[str, object]
    score: float
    rank: int


def bm25_search(records: Sequence[Dict[str, object]], query: str, top_k: int) -> List[BM25Hit]:
    if not records:
        return []

    corpus_tokens = [tokenize(str(r.get("content", ""))) for r in records]
    bm25 = BM25Okapi(corpus_tokens)
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    hits: List[BM25Hit] = []
    for rank, idx in enumerate(ranked_idx, start=1):
        record = records[idx]
        hits.append(
            BM25Hit(
                chunk_id=str(record.get("chunk_id", "")),
                content=str(record.get("content", "")),
                metadata=dict(record.get("metadata", {})),
                score=float(scores[idx]),
                rank=rank,
            )
        )
    return hits


def rrf_fuse(rankings: Dict[str, Dict[str, int]], k: int = 60, weights: Dict[str, float] | None = None) -> Dict[str, float]:
    fused: Dict[str, float] = {}
    for source, rank_map in rankings.items():
        source_weight = float((weights or {}).get(source, 1.0))
        for chunk_id, rank in rank_map.items():
            fused[chunk_id] = fused.get(chunk_id, 0.0) + (source_weight / (k + rank))
    return fused
