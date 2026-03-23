from __future__ import annotations

from typing import Dict, List

from app.query.schemas import CitationItem, GeneratedAnswer
from app.retrieval.schemas import RetrieveHit


def _trim(text: str, limit: int = 220) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 3] + "..."


def _citeref(ids: List[int]) -> str:
    return "".join(f"[{x}]" for x in sorted(set(ids)))


def _build_citations(hits: List[RetrieveHit], max_items: int = 4) -> List[CitationItem]:
    citations: List[CitationItem] = []
    for idx, hit in enumerate(hits[:max_items], start=1):
        md = hit.metadata or {}
        citations.append(
            CitationItem(
                id=idx,
                title=str(md.get("title", "Untitled")),
                section=str(md.get("section", "")),
                publish_date=str(md.get("publish_date", "")),
                url=str(md.get("url", "")),
                source=str(md.get("source", "")),
                snippet=_trim(hit.content, 180),
            )
        )
    return citations


def _build_training_items(intent: str, citations: List[CitationItem]) -> List[str]:
    c1 = [1] if citations else []
    c2 = [2] if len(citations) >= 2 else c1

    if intent in {"strength", "muscle_gain"}:
        return [
            f"Use progressive overload with planned tracking of sets, reps, and load {_citeref(c1)}.",
            f"Increase one variable per week (load/reps/sets) while keeping technique stable {_citeref(c2)}.",
        ]
    if intent in {"fat_loss", "nutrition"}:
        return [
            f"Keep resistance training 3-5 days per week to preserve lean mass during fat-loss phases {_citeref(c1)}.",
            f"Prioritize compound movements and maintain performance markers as anti-muscle-loss signals {_citeref(c2)}.",
        ]
    return [
        f"Use a sustainable weekly training split with measurable progression {_citeref(c1)}.",
        f"Adjust volume and intensity based on recovery and soreness patterns {_citeref(c2)}.",
    ]


def _build_nutrition_items(intent: str, citations: List[CitationItem]) -> List[str]:
    c1 = [1] if citations else []
    c2 = [2] if len(citations) >= 2 else c1
    if intent in {"fat_loss", "nutrition"}:
        return [
            f"Start with a moderate calorie deficit and evaluate weekly trend instead of daily fluctuations {_citeref(c1)}.",
            f"Keep protein intake high to protect muscle retention while cutting {_citeref(c2)}.",
        ]
    if intent in {"muscle_gain", "strength"}:
        return [
            f"Use a slight calorie surplus or maintenance-plus strategy based on performance response {_citeref(c1)}.",
            f"Distribute protein across 3-5 meals to support training quality and recovery {_citeref(c2)}.",
        ]
    return [
        f"Set calories from current bodyweight trend first, then refine macros {_citeref(c1)}.",
        f"Focus on whole-food consistency before advanced nutrient timing {_citeref(c2)}.",
    ]


def _build_recovery_items(citations: List[CitationItem]) -> List[str]:
    c = [min(3, len(citations))] if citations else []
    return [
        f"Sleep 7-8+ hours and avoid abrupt load spikes week-to-week {_citeref(c)}.",
        f"Use warm-up and technique checks before heavy compound lifts {_citeref(c)}.",
    ]


def _build_safety_items(citations: List[CitationItem]) -> List[str]:
    c = [min(3, len(citations))] if citations else []
    return [
        f"If pain persists or worsens, reduce training stress and seek qualified in-person evaluation {_citeref(c)}.",
        "Do not push through sharp joint pain or neurologic symptoms.",
    ]


def _estimate_confidence(hits: List[RetrieveHit]) -> float:
    if not hits:
        return 0.3
    top_score = float(hits[0].score)
    dual_source_bonus = 0.08 if len(hits[0].retrieval_sources) >= 2 else 0.0
    conf = 0.45 + min(0.4, top_score * 8.0) + dual_source_bonus
    return round(max(0.3, min(0.95, conf)), 3)


def generate_answer_from_hits(query: str, intent: str, hits: List[RetrieveHit]) -> GeneratedAnswer:
    citations = _build_citations(hits=hits, max_items=4)
    training = _build_training_items(intent=intent, citations=citations)
    nutrition = _build_nutrition_items(intent=intent, citations=citations)
    recovery = _build_recovery_items(citations=citations)
    safety = _build_safety_items(citations=citations)
    summary = (
        f"Question focus: {query}. Based on retrieved evidence, this plan prioritizes {intent} with actionable training, "
        "nutrition, and recovery steps."
    )
    confidence = _estimate_confidence(hits)

    answer_markdown = (
        "### Summary\n"
        f"{summary}\n\n"
        "### Training\n"
        + "\n".join(f"{i}. {x}" for i, x in enumerate(training, start=1))
        + "\n\n### Nutrition\n"
        + "\n".join(f"{i}. {x}" for i, x in enumerate(nutrition, start=1))
        + "\n\n### Recovery\n"
        + "\n".join(f"{i}. {x}" for i, x in enumerate(recovery, start=1))
        + "\n\n### Safety\n"
        + "\n".join(f"{i}. {x}" for i, x in enumerate(safety, start=1))
    )

    return GeneratedAnswer(
        summary=summary,
        training_plan=training,
        nutrition_plan=nutrition,
        recovery_plan=recovery,
        safety_notes=safety,
        confidence=confidence,
        citations=citations,
        answer_markdown=answer_markdown,
    )
