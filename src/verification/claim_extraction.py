from __future__ import annotations

import re

from src.models import Article, ExtractedClaim

ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9&.-]{1,}(?:\s+[A-Z][A-Za-z0-9&.-]{1,}){0,3}\b")


def extract_claims(article: Article) -> list[ExtractedClaim]:
    text = " ".join(part for part in [article.title, article.snippet or ""] if part).strip()
    if not text:
        return []
    sentence = re.split(r"(?<=[.!?])\s+", text)[0][:280].strip()
    entities = list(dict.fromkeys(match.group(0) for match in ENTITY_RE.finditer(sentence)))[:8]
    return [
        ExtractedClaim(
            claim=sentence,
            claim_type=_claim_type(sentence),
            entities=entities,
            time=article.published_at.date().isoformat() if article.published_at else None,
            supporting_sources=[article.source],
            confidence=max(0.1, min(1.0, article.reliability_score)),
        )
    ]


def _claim_type(text: str) -> str:
    lowered = text.casefold()
    if any(marker in lowered for marker in ["announced", "launch", "release", "unveiled"]):
        return "announcement"
    if any(marker in lowered for marker in ["said", "reported", "according"]):
        return "report"
    if any(marker in lowered for marker in ["rule", "policy", "sanction", "tariff", "regulation"]):
        return "policy"
    return "unknown"
