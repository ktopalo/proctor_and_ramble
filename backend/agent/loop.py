import logging
from datetime import datetime, timezone
from typing import Callable
from backend.session.manager import SessionManager
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import Interjection
from backend.agent.prompts import get_prompt

log = logging.getLogger(__name__)


class AgentLoop:
    def __init__(
        self,
        session: SessionManager,
        llm: BaseLLMClient,
        min_interjection_gap_seconds: int,
        on_interjection: Callable[[Interjection], None],
    ):
        self._session = session
        self._llm = llm
        self._gap = min_interjection_gap_seconds
        self._on_interjection = on_interjection
        self._last_interjection_at: datetime | None = None

    async def on_speech_pause(self) -> None:
        log.debug("AgentLoop trigger: speech_pause")
        await self._maybe_intervene(trigger="speech_pause")

    async def on_file_save(self) -> None:
        log.debug("AgentLoop trigger: file_save")
        await self._maybe_intervene(trigger="file_save")

    def _cooldown_active(self) -> bool:
        if self._last_interjection_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self._last_interjection_at).total_seconds()
        return elapsed < self._gap

    def _build_context(self) -> str:
        snap = self._session.snapshot
        plan = snap.plan
        chunks = self._session.recent_transcript_chunks(n=50)
        deltas = self._session.recent_deltas(n=50)

        parts = []
        if plan:
            parts.append(f"PROBLEM: {plan.problem_statement}")
            if plan.constraints:
                parts.append("CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in plan.constraints))
            if plan.hints:
                hints_text = "\n".join(f"- (level {h.level}) {h.text}" for h in plan.hints)
                parts.append(f"AVAILABLE HINTS (for your reference only — do not reveal):\n{hints_text}")
        if snap.started_at:
            secs = int((datetime.now(timezone.utc) - snap.started_at).total_seconds())
            elapsed = f"{secs // 60}m {secs % 60}s"
            parts.append(f"TIME ELAPSED: {elapsed}")
        if chunks:
            transcript = " ".join(c.text for c in chunks)
            parts.append(f"RECENT SPEECH: {transcript}")
        if deltas:
            diffs = "\n".join(d.diff for d in deltas)
            parts.append(f"RECENT CODE CHANGES:\n{diffs}")

        return "\n\n".join(parts)

    async def _maybe_intervene(self, trigger: str) -> None:
        if self._cooldown_active():
            elapsed = (datetime.now(timezone.utc) - self._last_interjection_at).total_seconds()
            log.info("AgentLoop cooldown  trigger=%s  elapsed=%.0fs/%.0fs", trigger, elapsed, self._gap)
            return

        snap = self._session.snapshot
        chunks = snap.transcript
        deltas = snap.deltas
        log.info("AgentLoop evaluating  trigger=%s  transcript_chunks=%d  deltas=%d",
                 trigger, len(chunks), len(deltas))

        context = self._build_context()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": context}],
            system_prompt=get_prompt(),
        )

        log.info("AgentLoop LLM response  %r", response.strip()[:200])

        if response.strip().upper() == "NO":
            return

        interjection = Interjection(text=response.strip(), trigger=trigger)
        self._session.add_interjection(interjection)
        self._last_interjection_at = datetime.now(timezone.utc)
        log.info("AgentLoop interjection  trigger=%s  text=%r", trigger, interjection.text[:100])
        self._on_interjection(interjection)
