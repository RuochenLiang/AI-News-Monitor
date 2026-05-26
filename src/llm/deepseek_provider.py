from __future__ import annotations

import httpx

from src.llm.openai_provider import OpenAIProvider
from src.models import LLMSettings


class DeepSeekProvider(OpenAIProvider):
    name = "deepseek"

    def __init__(self, settings: LLMSettings, api_key: str | None = None, client: httpx.Client | None = None):
        super().__init__(settings, api_key=api_key, client=client)
