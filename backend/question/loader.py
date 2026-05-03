import json
import logging
from html.parser import HTMLParser
import httpx
from backend.engines.llm.llm_base import BaseLLMClient
from backend.prompts import QUESTION_EXTRACTION_PROMPT, QUESTION_SYSTEM_PROMPT
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


async def load_question(url: str, llm: BaseLLMClient) -> InterviewPlan:
    log.info("Fetching question  url=%s", url)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        response.raise_for_status()

    extractor = _TextExtractor()
    extractor.feed(response.text)
    page_text = extractor.text[:12000]

    raw = await llm.complete(
        messages=[{"role": "user", "content": QUESTION_EXTRACTION_PROMPT + page_text}],
        system_prompt=QUESTION_SYSTEM_PROMPT,
    )

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        log.error("Failed to parse LLM JSON response  error=%s  raw=%r", exc, raw[:200])
        raise

    plan = InterviewPlan(**data, source_url=url)
    log.info("InterviewPlan created  problem=%s", plan.problem_markdown[:80])
    return plan
