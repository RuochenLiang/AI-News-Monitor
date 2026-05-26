from __future__ import annotations

from src.models import CustomNewsSourceConfig, SourceCandidate, SourceLibraryItem, SourceSettings
from src.sources.library import default_source_library

CATEGORY_DOMAINS = {
    "Global News": ["general_breaking_news", "geopolitics", "politics", "culture", "local_news"],
    "Finance": ["finance", "public_companies"],
    "Official/Government": ["politics", "public_policy", "geopolitics", "elections"],
    "China": ["geopolitics", "politics", "public_policy"],
    "Taiwan": ["geopolitics", "politics", "public_policy", "semiconductor"],
    "US": ["politics", "public_policy", "elections", "geopolitics"],
    "Semiconductor/AI": ["technology", "ai_industry", "semiconductor", "science"],
    "Company IR": ["public_companies", "finance", "technology", "ai_industry", "semiconductor"],
    "Custom": ["custom"],
}


def source_registry(settings: SourceSettings | None = None) -> list[SourceCandidate]:
    settings = settings or SourceSettings()
    items = settings.library if settings.library else default_source_library()
    candidates = [_candidate_from_library_item(item) for item in items]
    candidates.extend(_candidate_from_custom_source(item) for item in settings.custom_sources)
    return _dedupe_candidates(candidates)


def _candidate_from_library_item(item: SourceLibraryItem) -> SourceCandidate:
    domains = CATEGORY_DOMAINS.get(item.category, ["custom"])
    return SourceCandidate(
        id=item.id,
        name=item.name,
        url=item.url,
        source_type=_candidate_source_type(item),
        domain_tags=domains,
        country_or_region=_region_from_category(item.category),
        language=item.language,
        credibility_hint=item.reliability_score,
        cost_hint="free",
        requires_api_key=item.kind == "api",
        enabled_by_default=item.enabled,
        notes=item.editorial_context or item.bias_hint,
    )


def _candidate_from_custom_source(source: CustomNewsSourceConfig) -> SourceCandidate:
    return SourceCandidate(
        id=f"custom:{source.name.strip().casefold()}",
        name=source.name,
        url=source.url,
        source_type=source.kind,
        domain_tags=CATEGORY_DOMAINS.get(source.category, ["custom"]),
        country_or_region=_region_from_category(source.category),
        language=source.default_language,
        credibility_hint=source.reliability_score,
        cost_hint="free",
        requires_api_key=False,
        enabled_by_default=source.enabled,
        notes=source.editorial_context or source.bias_hint,
    )


def _candidate_source_type(item: SourceLibraryItem) -> str:
    text = " ".join([item.id, item.name, item.category, item.source_role, item.source_type]).casefold()
    if "arxiv" in text:
        return "arxiv"
    if item.source_role == "company_ir":
        return "company_ir"
    if item.source_role == "official" or "government" in text:
        return "gov"
    if "sec" in text:
        return "sec"
    return item.source_type or item.kind


def _region_from_category(category: str) -> str | None:
    if category in {"China", "Taiwan", "US"}:
        return category
    return None


def _dedupe_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    seen: set[tuple[str, str]] = set()
    deduped: list[SourceCandidate] = []
    for candidate in candidates:
        key = (candidate.name.strip().casefold(), candidate.url.strip().casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped
