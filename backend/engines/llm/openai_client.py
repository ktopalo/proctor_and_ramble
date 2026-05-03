import logging
import time
from typing import AsyncIterator
from openai import AsyncOpenAI
from backend.engines.llm.llm_base import BaseLLMClient

log = logging.getLogger(__name__)


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
        t0 = time.monotonic()
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(messages, system_prompt),
            )
        except Exception as exc:
            log.error("OpenAI complete failed  model=%s  error=%s", self.model, exc)
            raise
        elapsed = time.monotonic() - t0
        content = response.choices[0].message.content
        log.info("OpenAI complete done  model=%s  chars=%d  elapsed=%.2fs", self.model, len(content), elapsed)
        return content

    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        t0 = time.monotonic()
        total = 0
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(messages, system_prompt),
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    total += len(content)
                    yield content
        except Exception as exc:
            log.error("OpenAI stream_complete failed  model=%s  error=%s", self.model, exc)
            raise
        elapsed = time.monotonic() - t0
        log.info("OpenAI stream_complete done  model=%s  chars=%d  elapsed=%.2fs", self.model, total, elapsed)
