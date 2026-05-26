# AI-News-Monitor: Structured Outputs Upgrade Prompt

Paste this into the coding agent / GitHub update workflow.

```text
You are working on the GitHub repo `RuochenLiang/AI-News-Monitor`.

Goal:
Upgrade the LLM output handling from plain JSON mode to OpenAI Structured Outputs with JSON Schema, while preserving compatibility with other OpenAI-compatible providers.

Current state:
The project currently uses `src/llm_client.py` to call an OpenAI-compatible `/chat/completions` endpoint. The request body uses:

    "response_format": {"type": "json_object"}

The prompt also passes a `required_schema` object inside the user message, and the app manually parses/validates the response afterward. This works as JSON mode, but it is not API-enforced Structured Outputs.

Task:
Implement first-class Structured Outputs support for OpenAI-compatible models that support `response_format: {"type": "json_schema", ...}` with `strict: true`.

Requirements:

1. Add a JSON Schema builder for article analysis output.

Create a helper in `src/llm_client.py`, or a small new module if cleaner, such as:

    def _analysis_response_schema() -> dict[str, Any]:

It should return a strict JSON Schema for the existing `LLMAnalysis` shape:

    {
      "relevance_score": integer, 0-100
      "is_actionable_alert": boolean
      "event_type": string
      "summary": string
      "why_it_matters": string
      "market_watch_suggestions": array of objects:
        {
          "ticker": string
          "name_or_theme": string
          "possible_direction": enum ["bullish", "bearish", "mixed", "unclear"]
          "reason": string
          "confidence": enum ["low", "medium", "high"]
        }
      "bullish_path": string
      "bearish_path": string
      "risk_notes": string
      "uncertainty_notes": string
      "source_reliability": enum ["low", "medium", "high"]
      "recommended_user_action": enum ["watch_only", "research_further", "urgent_review", "ignore"]
      "notification_title": string
    }

Schema rules:
- Use `"type": "object"`.
- Include all fields in `"required"`.
- Use `"additionalProperties": false` at every object level.
- Use clear field descriptions where helpful.
- Keep the schema compatible with OpenAI Structured Outputs.
- Do not add fields that are not already accepted by `analysis_from_dict()` unless you also update the model and parser intentionally.

2. Add a JSON Schema builder for translation/summarization output.

Create:

    def _translation_response_schema() -> dict[str, Any]:

It should enforce:

    {
      "translated_title": string
      "translated_snippet": string
      "summary": string
    }

Use all fields as required and `additionalProperties: false`.

3. Replace the current hard-coded JSON mode with a helper.

Add a helper such as:

    def _structured_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        }

Also keep:

    def _json_object_response_format() -> dict[str, Any]:
        return {"type": "json_object"}

4. Add provider/model compatibility fallback.

Because this project supports generic OpenAI-compatible providers, do not assume every provider supports JSON Schema structured outputs.

Implement a setting or automatic fallback strategy:

Preferred approach:
- Add a new config field to `LLMSettings`, for example:

    structured_outputs: bool = True

- If `structured_outputs` is true, try JSON Schema mode first.
- If the provider rejects it with a clear unsupported-parameter / bad-request error, retry once with JSON object mode.
- Log a warning that structured outputs were not supported and JSON mode fallback was used.
- Do not treat the fallback as a fatal error unless both attempts fail.

The fallback should be used for:
- `_chat()` article analysis
- `translate_and_summarize()`
- `_test_chat_body()` or LLM diagnostics, if practical

5. Update `_chat()` so it accepts an optional response schema.

Change `_chat()` from always using:

    "response_format": {"type": "json_object"}

to something like:

    def _chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        response_schema: dict[str, Any] | None = None,
        response_name: str = "ai_news_monitor_response",
    ) -> str:

Then:
- If `response_schema` is provided and structured outputs are enabled, send JSON Schema mode.
- Otherwise send JSON object mode.
- If the first call fails because JSON Schema mode is unsupported, retry with JSON object mode.
- Preserve existing timeout/error handling.
- Preserve `_token_limit_payload()` behavior for GPT-5 models.

6. Update `analyze_article()`.

Call `_chat()` with:

    response_schema=_analysis_response_schema()
    response_name="ai_news_monitor_analysis"

Keep the existing `parse_llm_analysis()` and `analysis_from_dict()` validation after the response. Even with Structured Outputs, the local validation should remain as a defense-in-depth check.

The repair pass should remain available, but it should be less likely to run. For the repair call, either:
- use the same schema again, or
- fall back to JSON object mode if the original provider does not support JSON Schema.

7. Update `translate_and_summarize()`.

Call `_chat()` with:

    response_schema=_translation_response_schema()
    response_name="ai_news_monitor_translation"

Keep the existing local parsing and key extraction.

8. Update prompts to avoid redundant schema stuffing.

When using Structured Outputs, the model does not need the full schema embedded as a loose `required_schema` object in the user prompt.

Adjust `_build_messages()` carefully:
- Keep the task instructions.
- Keep the article payload.
- Keep domain guidance: use only provided article content, do not fabricate facts, state uncertainty, do not provide personalized financial advice.
- Remove or reduce the old `required_schema` prompt field when using schema mode.
- If JSON object fallback is used, it is acceptable to include a compact `required_schema` or field list in the prompt.

A simple implementation is acceptable:
- Keep the current prompt for now to reduce risk.
- But add a comment/TODO explaining that the schema is now enforced by `response_format.json_schema` when supported.

9. Add tests.

Add or update tests for:

A. Schema structure:
- `_analysis_response_schema()` includes all required fields.
- `additionalProperties` is false at top level and nested suggestion object level.
- Enums match the existing Python validation constants:
  - `VALID_DIRECTIONS`
  - `VALID_CONFIDENCE`
  - `VALID_RELIABILITY`
  - `VALID_ACTIONS`

B. Request body:
- When structured outputs are enabled, `_chat()` sends:

    response_format.type == "json_schema"
    response_format.json_schema.strict == True

- The schema name is present.
- The schema is present.

C. Fallback:
- Simulate a provider returning HTTP 400 for unsupported `json_schema`.
- Verify the client retries once with:

    response_format.type == "json_object"

- Verify the final parsed result still works.

D. Existing parser behavior:
- `analysis_from_dict()` still rejects missing keys.
- Invalid enum values still raise `ValueError`.
- `relevance_score` outside 0-100 still raises `ValueError`.

10. Do not break non-OpenAI providers.

The project README says this is an OpenAI-compatible LLM app, not OpenAI-only. Therefore:
- Do not remove JSON mode.
- Do not require the OpenAI Python SDK.
- Keep using `httpx` and the configured `base_url`.
- Keep `/chat/completions` compatibility.
- Do not hardcode OpenAI-only URLs.
- Do not hardcode a specific model.

11. Update documentation.

Update README or relevant docs to explain:
- The app prefers API-enforced JSON Schema structured outputs when supported by the configured provider/model.
- It falls back to JSON mode for providers that only support `response_format: {"type": "json_object"}`.
- Local validation remains enabled either way.

12. Acceptance criteria.

The implementation is complete when:
- The app still runs with the existing default OpenAI-compatible settings.
- Article analysis uses JSON Schema structured outputs when supported.
- Translation/summarization uses JSON Schema structured outputs when supported.
- Unsupported providers gracefully fall back to JSON mode.
- Existing output parsing and validation still work.
- Tests pass.
- No secrets, API keys, local config files, logs, databases, or runtime data are committed.

Suggested implementation shape:

In `src/llm_client.py`, introduce helpers similar to:

    def _analysis_response_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "relevance_score",
                "is_actionable_alert",
                "event_type",
                "summary",
                "why_it_matters",
                "market_watch_suggestions",
                "bullish_path",
                "bearish_path",
                "risk_notes",
                "uncertainty_notes",
                "source_reliability",
                "recommended_user_action",
                "notification_title",
            ],
            "properties": {
                "relevance_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "How relevant the article is to the configured topic.",
                },
                "is_actionable_alert": {"type": "boolean"},
                "event_type": {"type": "string"},
                "summary": {"type": "string"},
                "why_it_matters": {"type": "string"},
                "market_watch_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "ticker",
                            "name_or_theme",
                            "possible_direction",
                            "reason",
                            "confidence",
                        ],
                        "properties": {
                            "ticker": {"type": "string"},
                            "name_or_theme": {"type": "string"},
                            "possible_direction": {
                                "type": "string",
                                "enum": ["bullish", "bearish", "mixed", "unclear"],
                            },
                            "reason": {"type": "string"},
                            "confidence": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                            },
                        },
                    },
                },
                "bullish_path": {"type": "string"},
                "bearish_path": {"type": "string"},
                "risk_notes": {"type": "string"},
                "uncertainty_notes": {"type": "string"},
                "source_reliability": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "recommended_user_action": {
                    "type": "string",
                    "enum": ["watch_only", "research_further", "urgent_review", "ignore"],
                },
                "notification_title": {"type": "string"},
            },
        }

    def _translation_response_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["translated_title", "translated_snippet", "summary"],
            "properties": {
                "translated_title": {"type": "string"},
                "translated_snippet": {"type": "string"},
                "summary": {"type": "string"},
            },
        }

    def _json_schema_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        }

    def _json_object_response_format() -> dict[str, Any]:
        return {"type": "json_object"}

Be conservative: make the smallest safe code change that gives us real Structured Outputs support without reducing compatibility.
```

## Note

Because the repo currently uses raw `httpx` and `/chat/completions`, this prompt intentionally avoids the OpenAI SDK and keeps the existing OpenAI-compatible provider design.
