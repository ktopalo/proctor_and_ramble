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
        on_follow_up_revealed: Callable[[], None] = lambda: None,
    ):
        self._session = session
        self._llm = llm
        self._gap = min_interjection_gap_seconds
        self._on_interjection = on_interjection
        self._on_follow_up_revealed = on_follow_up_revealed
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
        parts = []

        if snap.started_at:
            secs = int((datetime.now(timezone.utc) - snap.started_at).total_seconds())
            parts.append(f"TIME ELAPSED: {secs // 60}m {secs % 60}s")

        if plan:
            total = len(plan.follow_ups)
            revealed = len(snap.revealed_follow_up_timestamps)
            parts.append(f"FOLLOW-UPS REVEALED: {revealed} of {total}")

        timeline = self._session.timeline_text
        if timeline:
            parts.append(timeline)

        return "\n\n".join(parts)

    async def _maybe_intervene(self, trigger: str) -> None:
        if self._cooldown_active():
            elapsed = (datetime.now(timezone.utc) - self._last_interjection_at).total_seconds()
            log.info("AgentLoop cooldown  trigger=%s  elapsed=%.0fs/%.0fs", trigger, elapsed, self._gap)
            return

        snap = self._session.snapshot
        log.info("AgentLoop evaluating  trigger=%s  transcript_chunks=%d  deltas=%d",
                 trigger, len(snap.transcript), len(snap.deltas))

        system_prompt = get_prompt()
        if snap.plan:
            system_prompt = (
                f"{system_prompt}\n\n---\n\n"
                f"INTERVIEW BRIEF:\n{snap.plan.agent_briefing}\n\n"
                f"RUBRIC:\n{snap.plan.rubric}"
            )

        context = self._build_context()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": context}],
            system_prompt=system_prompt,
        )

        log.info("AgentLoop LLM response  %r", response.strip()[:200])

        if response.strip().upper().startswith("REVEAL_NEXT_FOLLOWUP"):
            plan = snap.plan
            if plan and len(snap.revealed_follow_up_timestamps) < len(plan.follow_ups):
                next_index = len(snap.revealed_follow_up_timestamps)
                follow_up_text = plan.follow_ups[next_index]
                self._session.reveal_next_follow_up(follow_up_text=follow_up_text)
                self._on_follow_up_revealed()
                log.info("AgentLoop follow-up revealed  count=%d",
                         len(self._session.snapshot.revealed_follow_up_timestamps))
            parts = response.strip().split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                interjection_text = parts[1].strip()
            else:
                return
        elif response.strip().upper() == "NO":
            return
        else:
            interjection_text = response.strip()

        interjection = Interjection(text=interjection_text, trigger=trigger)
        self._session.add_interjection(interjection)
        self._last_interjection_at = datetime.now(timezone.utc)
        log.info("AgentLoop interjection  trigger=%s  text=%r", trigger, interjection.text[:100])
        self._on_interjection(interjection)
