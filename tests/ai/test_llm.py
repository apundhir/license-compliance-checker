import json

import pytest
from unittest.mock import MagicMock, patch
from lcc.ai.llm_client import LLMClient
from lcc.config import LCCConfig


def test_llm_client_classify():
    config = LCCConfig(llm_endpoint="http://localhost:8000", llm_api_key="dummy", llm_provider="local")
    client = LLMClient(config)

    # Mock the synchronous OpenAI client's chat.completions.create method
    with patch.object(client.client.chat.completions, "create") as mock_create:
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "license_id": "MIT",
            "confidence": 0.95,
            "is_proprietary": False,
            "reasoning": "Standard MIT header detected",
        })
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response

        result = client.classify_license("some text")
        assert result == "MIT"
        mock_create.assert_called_once()


def test_llm_client_disabled():
    config = LCCConfig(llm_endpoint=None)
    client = LLMClient(config)
    assert not client.enabled
    result = client.classify_license("text")
    assert result is None


def test_llm_client_error():
    config = LCCConfig(llm_endpoint="http://localhost:8000", llm_api_key="dummy", llm_provider="local")
    client = LLMClient(config)

    with patch.object(client.client.chat.completions, "create") as mock_create:
        mock_create.side_effect = Exception("API Error")

        result = client.classify_license("text")
        assert result is None
