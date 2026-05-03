import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.engines.llm_base import BaseLLMClient
from backend.engines.openai_client import OpenAIClient


def test_openai_client_is_base():
    assert issubclass(OpenAIClient, BaseLLMClient)


@pytest.mark.asyncio
async def test_complete_returns_string():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hello from mock"

    with patch("backend.engines.openai_client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        client = OpenAIClient(model="gpt-4o", api_key="sk-test")
        result = await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are helpful.",
        )

    assert result == "Hello from mock"


@pytest.mark.asyncio
async def test_complete_includes_system_prompt():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "ok"

    with patch("backend.engines.openai_client.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        client = OpenAIClient(model="gpt-4o", api_key="sk-test")
        await client.complete(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are a proctor.",
        )

        call_args = mock_client.chat.completions.create.call_args
        messages_sent = call_args.kwargs["messages"]

    assert messages_sent[0] == {"role": "system", "content": "You are a proctor."}
    assert messages_sent[1] == {"role": "user", "content": "hi"}
