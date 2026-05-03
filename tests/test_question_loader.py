import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.question.loader import load_question, _EXTRACTION_PROMPT
from backend.session.models import InterviewPlan


MOCK_LLM_RESPONSE = json.dumps({
    "problem_markdown": "## Two Sum\n\nGiven an array of integers `nums` and an integer `target`, return **indices** of the two numbers such that they add up to `target`.\n\n```python\nnums = [2, 7, 11, 15]\ntarget = 9\n# Output: [0, 1]\n```",
    "follow_ups": [
        "What if the array is sorted? Can you do better than O(n) space?",
        "Now handle the case where there may be multiple valid answers.",
    ],
    "agent_briefing": "Brute force: O(n²) nested loops. Optimal: hash map O(n) time and space — store complement as key. Common mistake: returning values not indices. Edge case: same element used twice (e.g. [3,3], target=6). Reveal follow-up 1 once candidate has a working solution.",
    "rubric": "Strong: O(n) hash map, correct indices, handles duplicates, explains complexity. Weak: brute force only, no edge case reasoning.",
})


@pytest.mark.asyncio
async def test_load_question_returns_interview_plan():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    mock_html = "<html><body><p>Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.</p></body></html>"

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        plan = await load_question("https://leetcode.com/problems/two-sum/", mock_llm)

    assert isinstance(plan, InterviewPlan)
    assert "Two Sum" in plan.problem_markdown
    assert len(plan.follow_ups) == 2
    assert "hash map" in plan.agent_briefing
    assert isinstance(plan.rubric, str)
    assert plan.source_url == "https://leetcode.com/problems/two-sum/"


@pytest.mark.asyncio
async def test_load_question_passes_url_to_plan():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "<p>some problem</p>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        plan = await load_question("https://example.com/problem/123", mock_llm)

    assert plan.source_url == "https://example.com/problem/123"


@pytest.mark.asyncio
async def test_load_question_truncates_page_at_12000():
    """Page content is truncated at 12000 chars before being sent to the LLM."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    long_page = "<p>" + "x" * 20000 + "</p>"

    with patch("backend.question.loader.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = long_page
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        await load_question("https://example.com/", mock_llm)

    call_args = mock_llm.complete.call_args
    user_content = call_args.kwargs["messages"][0]["content"]
    # Prompt prefix + 12000 chars of page content — leave generous slack for the full prompt
    assert len(user_content) <= len(_EXTRACTION_PROMPT) + 12000 + 50
