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
You are preparing a technical coding interview brief for a software engineering candidate. \
Extract the coding problem from the page content below and produce a rich interview plan. \
Return ONLY valid JSON with exactly these fields:

{
  "problem_markdown": "The complete problem description in markdown. Include the problem statement, \
any code snippets as fenced code blocks, and any constraints that are immediately relevant to solving \
the problem. Write this exactly as the candidate will read it during the interview.",
  "follow_ups": [
    "A markdown string for the first deferred challenge or constraint to reveal (gentlest — e.g. a follow-on constraint or small twist)",
    "A markdown string for the next challenge (harder — e.g. a stricter complexity requirement or a variant)",
    "..."
  ],
  "agent_briefing": "A thorough prose briefing a senior software engineer would write before running \
this interview. Cover: all known approaches from brute-force to optimal with their time and space \
complexity; the most common mistakes candidates make; subtle gotchas and edge cases the candidate \
is likely to miss; what strong vs weak performance looks like at each stage of the interview; and \
specific guidance on when to surface each follow-up (e.g. reveal follow-up 1 once the candidate has \
a working brute-force solution). No length limit — be thorough.",
  "rubric": "A free-form evaluation guide describing what a strong submission looks like. Cover: \
correctness, time and space efficiency, code quality, communication and reasoning while coding, \
and edge case handling."
}

Page content:
"""

_SYSTEM_PROMPT = (
    "You are an expert software engineering interviewer preparing a structured brief for a live "
    "technical coding interview. The candidate is a software engineer. "
    "Return only valid JSON, no markdown fences."
)


async def load_question(url: str, llm: BaseLLMClient) -> InterviewPlan:
    log.info("Fetching question  url=%s", url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    page_text = extractor.text[:12000]

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
