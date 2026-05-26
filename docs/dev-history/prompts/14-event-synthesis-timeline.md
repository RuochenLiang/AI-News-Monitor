# Codex Addendum: Event-Level News Synthesis + Timeline Output

You are working on the `AI-News-Monitor` repository.

This addendum extends the final runtime closure prompt. Do not rewrite the whole app. Add this as a targeted product improvement on top of the current stabilized system.

## New core requirement

The monitor must not only summarize isolated news articles. It must be able to group one or several content-related news items into a single coherent user-facing alert.

For a specific event, the user should receive:

1. A clear event-level summary.
2. The key facts from all related articles.
3. A source list with links.
4. A short explanation of why the articles are considered related.
5. A clean timeline of the event.
6. Practical implications or suggested actions where appropriate.

The goal is to move from:

> one article -> one summary

to:

> related articles -> one event cluster -> one synthesized alert with timeline

---

## Product behavior

When multiple articles are about the same underlying event, the app should avoid sending many repetitive alerts.

Instead, it should produce one grouped alert such as:

- Event title
- Current status
- What happened
- Why it matters
- Timeline
- Key sources
- Confidence / uncertainty
- Suggested follow-up

Example:

```text
Event: New US export-control update affects advanced AI chips

Summary:
Several sources report that the US government has updated export-control rules affecting advanced AI chips and related semiconductor equipment. Official sources confirm the regulatory change, while industry media focus on the likely impact on Nvidia, AMD, TSMC, and Chinese data-center supply chains.

Timeline:
- 2026-05-24: Industry media reported possible rule changes.
- 2026-05-25: Official government notice was published.
- 2026-05-26: Semiconductor companies and analysts began responding.

Why it matters:
This may affect AI infrastructure supply chains, GPU availability, China-related semiconductor policy, and related public-market narratives.

Sources:
- Official government notice
- Semiconductor trade press
- Company IR statement if available
```

---

## Task 1: Add event clustering before final alert generation

Add a lightweight event clustering step after article fetching/deduplication and before LLM final summarization.

Suggested design:

- Keep it deterministic first.
- Do not introduce a heavy vector database.
- Use article metadata and text signals:
  - normalized title
  - canonical URL/domain
  - topic keywords
  - named entities if already extractable
  - publication time proximity
  - overlapping important keywords
  - same company / country / policy / product name
- Group articles into event clusters when they are likely about the same underlying event.
- Keep unrelated articles separate.

Suggested module names:

- `src/event_clustering.py`
- `src/event_synthesis.py`

Suggested data models:

```python
@dataclass
class EventCluster:
    cluster_id: str
    title: str
    articles: list[Article]
    topics: list[str]
    entities: list[str]
    earliest_published_at: datetime | None
    latest_published_at: datetime | None
    confidence: float
    relation_reason: str
```

Use existing project model/style if there are already article/candidate dataclasses.

---

## Task 2: Add timeline extraction

For each event cluster, generate a timeline.

Timeline should combine:

- article published time
- event time mentioned in article if available
- official announcement time if available
- company statement time if available
- later market/industry reactions if available

If exact event time is unknown, use publication time and label it clearly.

Example timeline item model:

```python
@dataclass
class TimelineItem:
    date: str
    time: str | None
    label: str
    description: str
    source_title: str
    source_url: str
    confidence: float
```

Rules:

- Timeline must be chronological.
- Do not invent dates.
- If a date is inferred from article publication time, say so.
- If sources disagree, show uncertainty.
- Prefer official sources for definitive dates.

---

## Task 3: Update LLM structured output schema

Structured Outputs already exist. Do not redo the whole implementation.

Extend the existing analysis schema to support event-level synthesis.

The output should include fields like:

```json
{
  "event_title": "string",
  "event_summary": "string",
  "current_status": "string",
  "why_it_matters": "string",
  "timeline": [
    {
      "date": "YYYY-MM-DD or unknown",
      "time": "HH:MM or null",
      "description": "string",
      "source_title": "string",
      "source_url": "string",
      "confidence": 0.0
    }
  ],
  "key_facts": ["string"],
  "affected_entities": ["string"],
  "source_links": [
    {
      "title": "string",
      "url": "string",
      "publisher": "string",
      "published_at": "string"
    }
  ],
  "relation_reason": "string",
  "uncertainties": ["string"],
  "suggested_actions": ["string"],
  "should_notify": true
}
```

Keep backward compatibility:

- A single article should still produce a valid event synthesis.
- Existing tests for single-article analysis should still pass or be updated carefully.
- Translation schema should still work.

---

## Task 4: Update prompts

Update the LLM prompt so it explicitly says:

- You may receive one article or multiple related articles.
- Summarize them as one event, not as separate disconnected summaries.
- Build a timeline only from provided source text and metadata.
- Do not invent dates, companies, policies, or causal relationships.
- Distinguish confirmed facts from interpretation.
- Prefer official or primary sources when conflict exists.
- Keep output concise enough for notification channels.
- Include links to all important sources.

The Chinese output should be natural Chinese, not machine-translated mixed English.

English output should be clean English.

Technical names such as NVIDIA, TSMC, HBM, GDELT, RSS, LLM may remain English.

---

## Task 5: Update notification rendering

Update notification output so grouped event alerts are readable in Email/Telegram/WeCom/webhook channels.

Recommended structure:

```text
[Event Title]

Current status:
...

Summary:
...

Timeline:
- 2026-05-24: ...
- 2026-05-25: ...
- 2026-05-26: ...

Why it matters:
...

Sources:
1. Publisher — Title
   URL
2. Publisher — Title
   URL

Uncertainty:
...
```

Rules:

- Do not send raw JSON to notification channels.
- Do not include long code blocks.
- Keep mobile readability.
- Include source links.
- If the alert is created from multiple articles, say how many articles were grouped.
- If it is a single article, do not make it look artificially complex.

---

## Task 6: Update browser UI

The web UI should show event clusters, not only isolated article cards.

Add or update UI cards to show:

- Event title
- Number of grouped articles
- Latest update time
- Current status
- Concise summary
- Timeline preview
- Source list
- Relation reason
- Expandable details

Avoid code/JSON overflow:

- Raw event JSON only inside expandable diagnostic details.
- Long URLs wrap or are displayed as named links.
- The primary card should be concise.
- Chinese mode and English mode must both be localized.

---

## Task 7: Add tests

Add tests for:

1. Two articles about the same event are grouped into one cluster.
2. Two unrelated articles are not grouped.
3. A single article still creates one event cluster.
4. Timeline items are chronological.
5. Timeline does not invent dates when source dates are missing.
6. LLM schema accepts event-level synthesis.
7. Notification rendering includes timeline and source links.
8. Browser UI text does not expose raw JSON in primary cards.
9. Chinese and English locale keys exist for new UI strings.
10. Existing single-article tests still pass.

Suggested tests:

- `tests/test_event_clustering.py`
- `tests/test_event_synthesis_schema.py`
- `tests/test_event_notification_rendering.py`
- update existing pipeline tests where necessary

---

## Task 8: Pipeline diagnostics

Update funnel diagnostics to distinguish:

- articles fetched
- articles deduplicated
- candidates produced
- event clusters produced
- event clusters sent to LLM
- event clusters rejected by LLM
- event alerts generated
- notifications sent

Example:

```json
{
  "articles_fetched": 23,
  "articles_after_dedupe": 15,
  "candidates": 8,
  "event_clusters": 3,
  "clusters_sent_to_llm": 2,
  "event_alerts_generated": 1,
  "notifications_sent": 1
}
```

In the browser UI, show this as a concise human-readable summary, not raw JSON.

---

## Task 9: Documentation

Update docs only where needed:

- `README.md`
- `README.zh-CN.md`
- `SOURCE_GUIDE.md`
- `NOTIFICATION_GUIDE.md`
- `docs/RELEASE_CHECKLIST.md`
- `HANDOFF.md`
- `CHATBOT_CONTEXT.md`

Docs should explain:

- The system groups related articles into event-level alerts.
- A single event alert may include multiple sources.
- Timelines are generated only from source metadata and article text.
- The system may still send a single-article alert when only one source is available.
- Users should prefer official/primary sources for reliable timelines.

---

## Task 10: Verification

Run:

```bash
python -m ruff check .
python -m black --check .
python -m pytest -q
python -m compileall src tests
python -c "from pathlib import Path; from src.config import load_config; load_config(Path('config.example.yaml'), load_env=False); print('config ok')"
```

Then manually verify:

- E2E Test Mode can produce one event-level alert.
- A real Run Once can show event cluster diagnostics.
- Browser UI has no raw JSON/code overflow in primary cards.
- Chinese mode has natural Chinese event summaries and timeline labels.
- English mode has clean English event summaries and timeline labels.

---

## Final report required

At the end, report:

1. Files changed.
2. Event clustering behavior implemented.
3. Timeline behavior implemented.
4. LLM schema changes.
5. Notification rendering changes.
6. Browser UI/i18n changes.
7. Tests run and exact results.
8. Any limitations or follow-up work.
