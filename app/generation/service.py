from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from app.query.schemas import (
    ActionItem,
    CitationItem,
    GeneratedAnswer,
    NutritionTargets,
    SafetyAlert,
    WeeklySession,
)
from app.retrieval.schemas import RetrieveHit


def _trim(text: str, limit: int = 220) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 3] + "..."


def _citeref(ids: List[int]) -> str:
    if not ids:
        return ""
    return "".join(f"[{x}]" for x in sorted(set(ids)))


def _first_ids(citations: List[CitationItem], max_n: int = 2) -> List[int]:
    if not citations:
        return []
    return [c.id for c in citations[:max_n]]


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except Exception:  # noqa: BLE001
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except Exception:  # noqa: BLE001
        return default


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _parse_year(publish_date: str) -> int:
    date = (publish_date or "").strip()
    if len(date) >= 4 and date[:4].isdigit():
        return int(date[:4])
    return 0


def _freshness_level(year: int) -> str:
    if year <= 0:
        return "unknown"
    now = datetime.now().year
    age = now - year
    if age <= 2:
        return "fresh"
    if age <= 5:
        return "recent"
    return "classic"


def _quality_score(source_type: str, year: int, has_doi: bool) -> float:
    source = (source_type or "unknown").lower()
    base_map = {
        "paper": 0.82,
        "book": 0.75,
        "website": 0.62,
        "unknown": 0.55,
    }
    score = base_map.get(source, 0.55)
    freshness = _freshness_level(year)
    if freshness == "fresh":
        score += 0.1
    elif freshness == "recent":
        score += 0.05
    if has_doi:
        score += 0.05
    return round(max(0.45, min(0.99, score)), 3)


def _evidence_note(source_type: str, freshness_level: str, quality_score: float) -> str:
    src = (source_type or "unknown").lower()
    if src == "paper":
        basis = "peer-reviewed evidence"
    elif src == "book":
        basis = "professional textbook guidance"
    elif src == "website":
        basis = "institutional/public guideline"
    else:
        basis = "general reference"
    return f"{basis}; freshness={freshness_level}; quality={quality_score:.2f}"


def _build_citations(hits: List[RetrieveHit], max_items: int = 6) -> List[CitationItem]:
    citations: List[CitationItem] = []
    for idx, hit in enumerate(hits[:max_items], start=1):
        md = hit.metadata or {}
        year = _parse_year(str(md.get("publish_date", "")))
        freshness = _freshness_level(year)
        quality = _quality_score(
            source_type=str(md.get("source_type", "unknown")),
            year=year,
            has_doi=bool(str(md.get("doi", "")).strip()),
        )
        citations.append(
            CitationItem(
                id=idx,
                title=str(md.get("title", "Untitled")),
                section=str(md.get("section", "")),
                publish_date=str(md.get("publish_date", "")),
                url=str(md.get("url", "")),
                source_type=str(md.get("source_type", "unknown")),
                authors=str(md.get("authors", "")),
                venue=str(md.get("venue", "")),
                doi=str(md.get("doi", "")),
                source=str(md.get("source", "")),
                snippet=_trim(hit.content, 180),
                quality_score=quality,
                freshness_level=freshness,
                evidence_note=_evidence_note(str(md.get("source_type", "unknown")), freshness, quality),
            )
        )
    return citations


def _activity_multiplier(level: str) -> float:
    lv = (level or "").strip().lower()
    mapping = {
        "sedentary": 1.2,
        "light": 1.35,
        "moderate": 1.5,
        "high": 1.65,
        "athlete": 1.8,
    }
    return mapping.get(lv, 1.45)


def _intent_adjustment(intent: str) -> float:
    key = (intent or "").strip().lower()
    if key == "fat_loss":
        return -0.15
    if key in {"muscle_gain", "hypertrophy"}:
        return 0.08
    if key == "strength":
        return 0.03
    return 0.0


def _protein_ratio(intent: str) -> float:
    key = (intent or "").strip().lower()
    if key == "fat_loss":
        return 2.0
    if key in {"muscle_gain", "hypertrophy"}:
        return 1.8
    if key == "strength":
        return 1.7
    return 1.6


def _fat_ratio(intent: str) -> float:
    key = (intent or "").strip().lower()
    if key == "fat_loss":
        return 0.8
    if key in {"muscle_gain", "hypertrophy"}:
        return 0.9
    return 0.85


def _build_nutrition_targets(
    intent: str,
    user_profile: Dict[str, object],
    constraints: Dict[str, object],
) -> NutritionTargets:
    weight = _safe_float(user_profile.get("weight_kg", 0.0))
    height = _safe_float(user_profile.get("height_cm", 0.0))
    age = _safe_int(user_profile.get("age", 0))
    sex = _normalize_text(user_profile.get("sex", "unknown")).lower()
    activity = _normalize_text(user_profile.get("activity_level", "moderate"))

    if weight <= 0:
        return NutritionTargets(
            calories_kcal=0,
            protein_g=0,
            carbs_g=0,
            fat_g=0,
            hydration_ml=2200,
            note="Fill in bodyweight/height/age to unlock personalized macro targets.",
        )

    if height > 0 and age > 0:
        if sex == "female":
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        else:
            # Default to male equation when sex is unknown to avoid under-fueling.
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        # Fallback heuristic when full profile is missing.
        bmr = 24 * weight

    tdee = bmr * _activity_multiplier(activity)
    calorie_target = int(round(tdee * (1 + _intent_adjustment(intent))))

    protein_g = int(round(weight * _protein_ratio(intent)))
    fat_g = int(round(weight * _fat_ratio(intent)))
    carb_kcal = max(240, calorie_target - protein_g * 4 - fat_g * 9)
    carbs_g = int(round(carb_kcal / 4))
    hydration_ml = int(round(max(1800, weight * 35)))

    diet_pref = _normalize_text(constraints.get("diet_preference", ""))
    note = "Targets are starting points; adjust by 100-150 kcal based on 2-week trend."
    if diet_pref:
        note += f" Diet preference noted: {diet_pref}."

    return NutritionTargets(
        calories_kcal=max(1200, calorie_target),
        protein_g=max(60, protein_g),
        carbs_g=max(60, carbs_g),
        fat_g=max(35, fat_g),
        hydration_ml=hydration_ml,
        note=note,
    )


def _intent_focus_templates(intent: str) -> List[str]:
    key = (intent or "").strip().lower()
    if key == "fat_loss":
        return [
            "Lower Strength + Steps",
            "Upper Hypertrophy",
            "Zone2 Cardio + Core",
            "Full-body Density",
            "Technique + Mobility",
            "Active Recovery",
            "Rest",
        ]
    if key in {"strength", "muscle_gain"}:
        return [
            "Squat Focus",
            "Upper Push Focus",
            "Pull + Posterior Chain",
            "Deadlift Focus",
            "Upper Pull + Arms",
            "Conditioning Optional",
            "Rest",
        ]
    return [
        "Full Body A",
        "Cardio + Core",
        "Full Body B",
        "Movement Skills",
        "Full Body C",
        "Light Activity",
        "Rest",
    ]


def _apply_adjustment_text(adjustment_type: str, session_minutes: int) -> tuple[str, int]:
    adj = (adjustment_type or "none").strip().lower()
    if adj == "limited_time":
        return "Use superset pairs and cap rest to 60-90s.", min(session_minutes, 40)
    if adj == "no_equipment":
        return "Switch to bodyweight + resistance-band alternatives.", session_minutes
    if adj == "pain":
        return "Reduce ROM/load and stop all pain-provoking patterns.", session_minutes
    if adj == "travel":
        return "Use hotel-gym dumbbell templates and walking targets.", session_minutes
    if adj == "plateau":
        return "Insert a 1-week deload then re-ramp volume.", session_minutes
    return "", session_minutes


def _build_weekly_plan(
    intent: str,
    citations: List[CitationItem],
    constraints: Dict[str, object],
    adjustment: Dict[str, object],
) -> List[WeeklySession]:
    days_per_week = _safe_int(constraints.get("days_per_week", 4), default=4)
    days_per_week = max(1, min(7, days_per_week))
    session_minutes = _safe_int(constraints.get("session_minutes", 60), default=60)
    session_minutes = max(20, min(150, session_minutes))

    adjustment_type = _normalize_text(adjustment.get("adjustment_type", "none")).lower()
    adjustment_note, adjusted_minutes = _apply_adjustment_text(adjustment_type, session_minutes)
    equipment = constraints.get("equipment", [])
    injuries = constraints.get("injuries", [])

    if not isinstance(equipment, list):
        equipment = []
    if not isinstance(injuries, list):
        injuries = []

    templates = _intent_focus_templates(intent)
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    citation_ids = _first_ids(citations, max_n=2)
    plan: List[WeeklySession] = []
    for idx in range(days_per_week):
        focus = templates[idx % len(templates)]
        day_plan = [
            "Warm-up 8-10 min: mobility + ramp-up sets.",
            "Main lift blocks: 2-4 exercises with RPE 6-8 progression.",
            "Finish with 8-20 min conditioning or low-intensity cardio.",
        ]
        nutrition_focus = [
            "Protein evenly across 3-5 meals.",
            "Hydration target split before/during/after training.",
        ]
        if idx == 0 and equipment:
            day_plan.append(f"Available equipment: {', '.join(str(x) for x in equipment[:4])}.")
        if idx == 0 and injuries:
            day_plan.append(f"Injury constraints: {', '.join(str(x) for x in injuries[:3])}.")
        if adjustment_note:
            day_plan.append(f"Adjustment: {adjustment_note}")

        plan.append(
            WeeklySession(
                day=weekdays[idx],
                focus=focus,
                duration_minutes=adjusted_minutes,
                plan=day_plan,
                nutrition_focus=nutrition_focus,
                citation_ids=citation_ids,
            )
        )
    return plan


def _build_action_items(
    intent: str,
    citations: List[CitationItem],
    nutrition_targets: NutritionTargets,
    adjustment: Dict[str, object],
) -> List[ActionItem]:
    c12 = _first_ids(citations, max_n=2)
    c3 = [citations[2].id] if len(citations) >= 3 else c12
    c4 = [citations[3].id] if len(citations) >= 4 else c12

    items = [
        ActionItem(
            domain="training",
            title="Weekly progressive overload",
            detail=f"Track sets/reps/load weekly and increase one variable at a time {_citeref(c12)}.",
            citation_ids=c12,
            priority="high",
        ),
        ActionItem(
            domain="nutrition",
            title="Macro target execution",
            detail=(
                f"Start with {nutrition_targets.calories_kcal} kcal, {nutrition_targets.protein_g}g protein, "
                f"{nutrition_targets.carbs_g}g carbs, {nutrition_targets.fat_g}g fat."
            ),
            citation_ids=c12,
            priority="high",
        ),
        ActionItem(
            domain="recovery",
            title="Recovery floor",
            detail=f"Keep 7-8h sleep and one low-stress recovery day every week {_citeref(c3)}.",
            citation_ids=c3,
            priority="high",
        ),
        ActionItem(
            domain="tracking",
            title="Bi-weekly adjustment loop",
            detail="Review bodyweight trend, gym performance, and hunger every 14 days; adjust calories by 100-150 kcal.",
            citation_ids=c4,
            priority="medium",
        ),
    ]

    adjustment_type = _normalize_text(adjustment.get("adjustment_type", "none")).lower()
    note = _normalize_text(adjustment.get("note", ""))
    if adjustment_type and adjustment_type != "none":
        details = "Applied user adjustment constraints to keep plan executable."
        if note:
            details += f" User note: {note}"
        items.insert(
            0,
            ActionItem(
                domain="adjustment",
                title=f"Adjustment mode: {adjustment_type}",
                detail=details,
                citation_ids=c12,
                priority="high",
            ),
        )

    # A lightweight intent-specific action so the plan feels customized.
    if intent == "fat_loss":
        items.append(
            ActionItem(
                domain="fat_loss",
                title="Preserve muscle while cutting",
                detail=f"Keep 3-5 resistance sessions/week and avoid aggressive calorie cuts {_citeref(c12)}.",
                citation_ids=c12,
                priority="high",
            )
        )
    elif intent in {"strength", "muscle_gain"}:
        items.append(
            ActionItem(
                domain="performance",
                title="Performance-led progression",
                detail=f"Use planned intensity waves and keep technical failure low {_citeref(c12)}.",
                citation_ids=c12,
                priority="high",
            )
        )

    return items


def _build_safety_alerts(query: str, constraints: Dict[str, object]) -> List[SafetyAlert]:
    text = f"{query} {' '.join(str(x) for x in constraints.get('injuries', []))}".lower()
    alerts: List[SafetyAlert] = []
    if any(k in text for k in ["chest pain", "faint", "dizzy", "blackout", "numbness"]):
        alerts.append(
            SafetyAlert(
                risk_level="high",
                message="Potential red-flag symptoms detected.",
                action="Stop training and seek in-person medical evaluation immediately.",
            )
        )
    if any(k in text for k in ["injury", "pain", "knee", "shoulder", "back pain"]):
        alerts.append(
            SafetyAlert(
                risk_level="medium",
                message="Pain/injury context detected.",
                action="Lower load/ROM, choose pain-free alternatives, and monitor symptoms for 48-72h.",
            )
        )
    if not alerts:
        alerts.append(
            SafetyAlert(
                risk_level="low",
                message="No acute red flags detected in text input.",
                action="Train with conservative progression and maintain technique quality.",
            )
        )
    return alerts


def _build_progress_tips(intent: str) -> List[str]:
    base = [
        "Log bodyweight at least 3x/week and use weekly average.",
        "Log key lifts (load/reps/RPE) for top 3 movements.",
        "Mark sleep quality and stress level daily (1-5).",
    ]
    if intent == "fat_loss":
        base.append("If weight trend stalls for 2 weeks, reduce 100-150 kcal or add 2k daily steps.")
    else:
        base.append("If performance drops for >7 days, schedule a deload week.")
    return base


def _estimate_confidence(hits: List[RetrieveHit], citations: List[CitationItem]) -> float:
    if not hits:
        return 0.35
    top_score = float(hits[0].score)
    dual_source_bonus = 0.08 if len(hits[0].retrieval_sources) >= 2 else 0.0
    quality_avg = sum(c.quality_score for c in citations) / max(1, len(citations))
    quality_bonus = min(0.12, max(0.0, (quality_avg - 0.6) * 0.3))
    conf = 0.44 + min(0.34, top_score * 8.0) + dual_source_bonus + quality_bonus
    return round(max(0.3, min(0.96, conf)), 3)


def _markdown_weekly(weekly_plan: List[WeeklySession]) -> str:
    if not weekly_plan:
        return "- No weekly plan available."
    lines: List[str] = []
    for day in weekly_plan:
        lines.append(f"- {day.day} | {day.focus} | {day.duration_minutes} min {_citeref(day.citation_ids)}")
        for task in day.plan:
            lines.append(f"  - {task}")
    return "\n".join(lines)


def _markdown_actions(action_items: List[ActionItem]) -> str:
    if not action_items:
        return "- No action items."
    return "\n".join(
        f"{idx}. **{item.title}** ({item.domain}, {item.priority}) - {item.detail}"
        for idx, item in enumerate(action_items, start=1)
    )


def _markdown_safety(alerts: List[SafetyAlert]) -> str:
    return "\n".join(f"- [{a.risk_level}] {a.message} -> {a.action}" for a in alerts)


def _build_summary(query: str, intent: str, weekly_plan: List[WeeklySession], nutrition_targets: NutritionTargets) -> str:
    if weekly_plan:
        exec_text = f"{len(weekly_plan)} training days/week"
    else:
        exec_text = "a personalized weekly cadence"
    if nutrition_targets.calories_kcal > 0:
        nutrition_text = (
            f"{nutrition_targets.calories_kcal} kcal with {nutrition_targets.protein_g}g protein target"
        )
    else:
        nutrition_text = "nutrition targets pending profile completion"
    return (
        f"Question focus: {query}. Plan intent={intent}. The output prioritizes {exec_text}, "
        f"actionable load progression, and {nutrition_text}."
    )


def generate_answer_from_hits(
    query: str,
    intent: str,
    hits: List[RetrieveHit],
    user_profile: Dict[str, object] | None = None,
    constraints: Dict[str, object] | None = None,
    adjustment: Dict[str, object] | None = None,
) -> GeneratedAnswer:
    profile = user_profile or {}
    plan_constraints = constraints or {}
    plan_adjustment = adjustment or {}

    citations = _build_citations(hits=hits, max_items=6)
    nutrition_targets = _build_nutrition_targets(
        intent=intent,
        user_profile=profile,
        constraints=plan_constraints,
    )
    weekly_plan = _build_weekly_plan(
        intent=intent,
        citations=citations,
        constraints=plan_constraints,
        adjustment=plan_adjustment,
    )
    action_items = _build_action_items(
        intent=intent,
        citations=citations,
        nutrition_targets=nutrition_targets,
        adjustment=plan_adjustment,
    )
    safety_alerts = _build_safety_alerts(query=query, constraints=plan_constraints)
    progress_tips = _build_progress_tips(intent=intent)

    # Keep legacy sections for backward compatibility with existing validations/UI.
    training = [x.detail for x in action_items if x.domain in {"training", "performance", "fat_loss"}][:4]
    nutrition = [x.detail for x in action_items if x.domain == "nutrition"][:3]
    recovery = [x.detail for x in action_items if x.domain == "recovery"][:3]
    if not recovery:
        recovery = ["Sleep 7-8h per night and manage weekly fatigue with at least one lower-stress day."]
    safety_notes = [f"[{x.risk_level}] {x.action}" for x in safety_alerts]

    summary = _build_summary(
        query=query,
        intent=intent,
        weekly_plan=weekly_plan,
        nutrition_targets=nutrition_targets,
    )
    confidence = _estimate_confidence(hits=hits, citations=citations)

    answer_markdown = (
        "### Summary\n"
        f"{summary}\n\n"
        "### Action Items\n"
        f"{_markdown_actions(action_items)}\n\n"
        "### Weekly Plan\n"
        f"{_markdown_weekly(weekly_plan)}\n\n"
        "### Nutrition Targets\n"
        f"- Calories: {nutrition_targets.calories_kcal} kcal/day\n"
        f"- Protein: {nutrition_targets.protein_g} g/day\n"
        f"- Carbs: {nutrition_targets.carbs_g} g/day\n"
        f"- Fat: {nutrition_targets.fat_g} g/day\n"
        f"- Hydration: {nutrition_targets.hydration_ml} ml/day\n"
        f"- Note: {nutrition_targets.note}\n\n"
        "### Safety\n"
        f"{_markdown_safety(safety_alerts)}\n\n"
        "### Progress Tracking\n"
        + "\n".join(f"- {x}" for x in progress_tips)
        + "\n\n### References\n"
        + "\n".join(
            (
                f"- [{c.id}] ({c.source_type}/{c.freshness_level}, q={c.quality_score:.2f}) "
                f"{c.title} {f'| DOI: {c.doi}' if c.doi else ''} {f'| {c.url}' if c.url else ''}"
            )
            for c in citations
        )
    )

    return GeneratedAnswer(
        summary=summary,
        training_plan=training,
        nutrition_plan=nutrition,
        recovery_plan=recovery,
        safety_notes=safety_notes,
        confidence=confidence,
        citations=citations,
        answer_markdown=answer_markdown,
        action_items=action_items,
        weekly_plan=weekly_plan,
        nutrition_targets=nutrition_targets,
        safety_alerts=safety_alerts,
        progress_tracking_tips=progress_tips,
    )

