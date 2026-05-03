from typing import AsyncIterator
from openai import AsyncOpenAI
from backend.engines.llm_base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    def _build_messages(self, messages: list[dict], system_prompt: str) -> list[dict]:
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        return all_messages

    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(messages, system_prompt),
        )
        return response.choices[0].message.content

    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(messages, system_prompt),
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
