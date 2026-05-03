import json
import logging
from html.parser import HTMLParser
import httpx
from backend.engines.llm_base import BaseLLMClient
from backend.session.models import InterviewPlan

log = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


_EXTRACTION_PROMPT = """\
Extract the interview question from the page content below and enrich it into a \
full interview plan. Return ONLY valid JSON with exactly these fields:

{
  "problem_markdown": "## Problem Title\\nDetailed markdown description...",
  "follow_ups": ["Follow-up question 1", "Follow-up question 2"],
  "agent_briefing": "Guidance for the proctor on optimal solution, complexity analysis, etc.",
  "rubric": "A comprehensive single string describing success criteria and evaluation dimensions."
}

Page content:
"""

_SYSTEM_PROMPT = (
    "You are an expert technical interviewer preparing a structured interview plan. "
    "Return only valid JSON, no markdown fences."
)


async def load_question(url: str, llm: BaseLLMClient) -> InterviewPlan:
    log.info("Fetching question  url=%s", url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    page_text = extractor.text[:8000]

    raw = await llm.complete(
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + page_text}],
        system_prompt=_SYSTEM_PROMPT,
    )

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        log.error("Failed to parse LLM JSON response  error=%s  raw=%r", exc, raw[:200])
        raise

    plan = InterviewPlan(**data, source_url=url)
    log.info("InterviewPlan created  problem=%s", plan.problem_markdown[:80])
    return plan
