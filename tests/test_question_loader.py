import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.question.loader import load_question
from backend.session.models import InterviewPlan


MOCK_LLM_RESPONSE = json.dumps({
    "problem_statement": "Given an array of integers, return indices of the two numbers that add up to target.",
    "constraints": ["2 <= nums.length <= 10^4", "Each input has exactly one solution"],
    "hints": [
        {"level": 1, "text": "Think about what complement you need for each number."},
        {"level": 2, "text": "A hash map can give O(1) lookups."},
    ],
    "expected_approaches": ["Brute force O(n²)", "Hash map O(n)"],
    "follow_up_questions": ["What if the array is sorted?", "What if there are multiple valid answers?"],
    "rubric": {
        "correctness": "Returns correct indices for all test cases",
        "efficiency": "Achieves O(n) time complexity",
        "communication": "Explains reasoning while coding",
        "edge_cases": "Handles negative numbers and duplicates",
    },
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
    assert "two numbers" in plan.problem_statement.lower() or "indices" in plan.problem_statement.lower()
    assert len(plan.hints) == 2
    assert plan.hints[0].level == 1
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
