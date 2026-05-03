import asyncio
import logging
import os
import tempfile
import time
from typing import AsyncIterator
from backend.engines.llm_base import BaseLLMClient

# Ensure Homebrew bin is on PATH so `codex` is found when running as a subprocess
_ENV = {**os.environ, "PATH": f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"}

log = logging.getLogger(__name__)


class CodexCLIClient(BaseLLMClient):
    def __init__(self, model: str = "o4-mini", codex_path: str = "codex"):
        self._model = model
        self._codex_path = codex_path

    def _build_prompt(self, messages: list[dict], system_prompt: str) -> str:
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        for msg in messages:
            parts.append(f"{msg['role'].capitalize()}: {msg['content']}")
        return "\n\n".join(parts)

    async def complete(self, messages: list[dict], system_prompt: str = "") -> str:
        prompt = self._build_prompt(messages, system_prompt)

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            out_path = f.name

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                self._codex_path, "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "-m", self._model,
                "-s", "read-only",
                "-o", out_path,
                "-",  # read prompt from stdin
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,  # progress chatter goes nowhere
                stderr=asyncio.subprocess.PIPE,
                env=_ENV,
            )
            _, stderr = await proc.communicate(input=prompt.encode())
            if proc.returncode != 0:
                err = stderr.decode().strip()
                log.error("Codex complete failed  model=%s  exit=%d  stderr=%s", self._model, proc.returncode, err)
                raise RuntimeError(f"codex exited {proc.returncode}: {err}")
            with open(out_path) as f:
                result = f.read().strip()
        finally:
            os.unlink(out_path)

        elapsed = time.monotonic() - t0
        log.info("Codex complete done  model=%s  chars=%d  elapsed=%.2fs", self._model, len(result), elapsed)
        return result

    async def stream_complete(
        self, messages: list[dict], system_prompt: str = ""
    ) -> AsyncIterator[str]:
        # Codex CLI doesn't stream — yield the full response as one chunk
        result = await self.complete(messages, system_prompt)
        yield result
