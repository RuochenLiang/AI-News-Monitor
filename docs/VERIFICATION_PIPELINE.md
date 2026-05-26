# Verification Pipeline

The verification layer runs after event clustering and LLM analysis. It is intentionally explainable rather than opaque.

Event aggregation lives under `src/aggregation/`:

- `event_clusterer.py` groups related articles into one event.
- `topic_timeline.py` builds source-grounded timelines and event payloads.
- `deduplication.py` keeps article identity dedupe available behind the aggregation namespace.

## Inputs

- Article source metadata: source role, tier, reliability score, source type, owner, and risk hints.
- Event cluster shape: number of sources and independent source owners.
- Extracted lightweight claims from article titles and snippets.
- LLM analysis reliability hint.

## Output

Each event receives a verification report with:

- `status`: `verified`, `developing`, `unconfirmed`, or `low_confidence`.
- `confidence_score`: normalized from 0 to 1.
- source credibility reasons and risks.
- extracted and corroborated claims.
- whether the event is social-only.
- contradictory claim sources, when found.

The browser report card shows verification status, relevance score, confidence score, source comparison, timeline, source links, and relation reason. Raw diagnostic payloads stay behind expandable details.

## Notification Gate

The gate blocks reports below the topic confidence threshold. Social-only reports can still notify only when clearly labelled as unconfirmed.

Use a higher `min_confidence_score` for topics where false positives are expensive:

```yaml
notification_threshold:
  min_relevance_score: 0.75
  min_confidence_score: 0.70
```

Lower thresholds are better for early-signal monitoring, but expect more developing or unconfirmed reports.

Existing configs keep working because old topics default to:

```yaml
source_mode: manual
social_enabled: false
```
