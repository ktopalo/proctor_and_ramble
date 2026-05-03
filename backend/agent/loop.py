from datetime import datetime
from typing import Callable
from backend.session.manager import SessionManager
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import Interjection

_SYSTEM_PROMPT = """\
You are a technical interview proctor watching a candidate solve a problem in real time.
You see their speech transcript and code changes.

Your role: provide short, Socratic nudges when the candidate needs guidance. Never give away the answer.

Rules:
- If the candidate is actively making progress or speaking confidently: respond with exactly "NO"
- If they seem stuck, confused, or could benefit from a nudge: provide 1-2 sentences of guidance
- Be encouraging, directional, never patronizing
- Never solve the problem for them

Respond with either "NO" or the interjection text. No preamble."""


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
        await self._maybe_intervene(trigger="speech_pause")

    async def on_file_save(self) -> None:
        await self._maybe_intervene(trigger="file_save")

    def _cooldown_active(self) -> bool:
        if self._last_interjection_at is None:
            return False
        elapsed = (datetime.utcnow() - self._last_interjection_at).total_seconds()
        return elapsed < self._gap

    def _build_context(self) -> str:
        snap = self._session.snapshot
        plan = snap.plan
        chunks = self._session.recent_transcript_chunks(n=20)
        deltas = self._session.recent_deltas(n=5)

        parts = []
        if plan:
            parts.append(f"PROBLEM: {plan.problem_statement}")
        if chunks:
            transcript = " ".join(c.text for c in chunks)
            parts.append(f"RECENT SPEECH: {transcript}")
        if deltas:
            diffs = "\n".join(d.diff for d in deltas)
            parts.append(f"RECENT CODE CHANGES:\n{diffs}")
        if snap.started_at:
            secs = int((datetime.utcnow() - snap.started_at).total_seconds())
            elapsed = f"{secs // 60}m {secs % 60}s"
            parts.append(f"TIME ELAPSED: {elapsed}")

        return "\n\n".join(parts)

    async def _maybe_intervene(self, trigger: str) -> None:
        if self._cooldown_active():
            return

        context = self._build_context()
        response = await self._llm.complete(
            messages=[{"role": "user", "content": context}],
            system_prompt=_SYSTEM_PROMPT,
        )

        if response.strip().upper() == "NO":
            return

        interjection = Interjection(text=response.strip(), trigger=trigger)
        self._session.add_interjection(interjection)
        self._last_interjection_at = datetime.utcnow()
        self._on_interjection(interjection)
