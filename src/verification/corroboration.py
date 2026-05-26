from __future__ import annotations

from src.models import ExtractedClaim


def corroborate_claims(claims: list[ExtractedClaim]) -> list[ExtractedClaim]:
    groups: dict[str, list[ExtractedClaim]] = {}
    for claim in claims:
        groups.setdefault(_claim_key(claim), []).append(claim)
    corroborated: list[ExtractedClaim] = []
    for items in groups.values():
        base = max(items, key=lambda item: item.confidence)
        base_polarity = _claim_polarity(base.claim)
        supporting_items: list[ExtractedClaim] = []
        contradicting_items: list[ExtractedClaim] = []
        for item in items:
            polarity = _claim_polarity(item.claim)
            if _polarities_conflict(base_polarity, polarity):
                contradicting_items.append(item)
            else:
                supporting_items.append(item)
        sources = sorted({source for item in supporting_items for source in item.supporting_sources})
        contradicting_sources = sorted({source for item in contradicting_items for source in item.supporting_sources})
        entities = sorted({entity for item in items for entity in item.entities})
        confidence = min(1.0, base.confidence + max(0, len(sources) - 1) * 0.12)
        if contradicting_sources:
            confidence = max(0.0, confidence - 0.2)
        corroborated.append(
            ExtractedClaim(
                claim=base.claim,
                claim_type=base.claim_type,
                entities=entities,
                time=base.time,
                supporting_sources=sources,
                contradicting_sources=contradicting_sources,
                confidence=round(confidence, 2),
            )
        )
    return corroborated


def _claim_key(claim: ExtractedClaim) -> str:
    entities = "|".join(sorted(entity.casefold() for entity in claim.entities[:4]))
    words = " ".join(claim.claim.casefold().split()[:12])
    return entities or words


def _claim_polarity(text: str) -> str:
    lowered = text.casefold()
    negative_markers = (
        "denies",
        "denied",
        "rejects",
        "rejected",
        "refutes",
        "false",
        "not ",
        " no ",
        "without",
        "has not",
        "will not",
    )
    positive_markers = (
        "announced",
        "confirmed",
        "says",
        "said",
        "will",
        "plans",
        "approved",
        "launched",
        "signed",
    )
    if any(marker in lowered for marker in negative_markers):
        return "negative"
    if any(marker in lowered for marker in positive_markers):
        return "positive"
    return "unknown"


def _polarities_conflict(left: str, right: str) -> bool:
    return {left, right} == {"positive", "negative"}
