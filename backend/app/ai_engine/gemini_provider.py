from __future__ import annotations

import google.generativeai as genai

from app.ai_engine.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self._model_name = model

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2000) -> str:
        model = genai.GenerativeModel(model_name=self._model_name, system_instruction=system)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
        )
        return response.text or ""
