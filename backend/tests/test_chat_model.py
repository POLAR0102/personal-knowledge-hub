import logging
from dataclasses import dataclass

import httpx
import pytest
from fastapi import HTTPException
from openai import APITimeoutError, RateLimitError

from app.ai.llm import (
    ChatMessage,
    ChatModelConfigurationError,
    ChatModelInputError,
    ChatModelRequestError,
    ChatModelResponseError,
    ChatModelUsage,
)
from app.ai.llm.factory import create_chat_model_provider
from app.ai.llm.openai_compatible import OpenAICompatibleChatModelProvider
from app.core.config import Settings


@dataclass
class FakeResponseMessage:
    content: str | None


@dataclass
class FakeResponseChoice:
    message: FakeResponseMessage


@dataclass
class FakeResponseUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class FakeChatResponse:
    choices: list[FakeResponseChoice]
    model: str = "deepseek-v4-flash"
    usage: FakeResponseUsage | None = None


class FakeCompletionsResource:
    def __init__(self, outcomes: list[FakeChatResponse | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> FakeChatResponse:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeChatResource:
    def __init__(self, completions: FakeCompletionsResource) -> None:
        self.completions = completions


class FakeChatClient:
    def __init__(self, completions: FakeCompletionsResource) -> None:
        self.chat = FakeChatResource(completions)


def make_response(
    content: str | None = "根据知识库，核心版本计划在 14 天内完成。[来源 1]",
    *,
    model: str = "deepseek-v4-flash",
    with_usage: bool = True,
) -> FakeChatResponse:
    usage = (
        FakeResponseUsage(
            prompt_tokens=120,
            completion_tokens=20,
            total_tokens=140,
        )
        if with_usage
        else None
    )
    return FakeChatResponse(
        choices=[FakeResponseChoice(message=FakeResponseMessage(content=content))],
        model=model,
        usage=usage,
    )


def make_provider(
    resource: FakeCompletionsResource,
    *,
    max_retries: int = 0,
    api_key: str = "test-chat-api-key",
) -> OpenAICompatibleChatModelProvider:
    return OpenAICompatibleChatModelProvider(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        timeout_seconds=5,
        max_retries=max_retries,
        client=FakeChatClient(resource),
    )


def test_generate_returns_content_model_and_usage() -> None:
    resource = FakeCompletionsResource([make_response()])
    provider = make_provider(resource)
    messages = [
        ChatMessage(role="system", content="只根据知识库上下文回答。"),
        ChatMessage(role="user", content="核心版本多久完成？"),
    ]

    result = provider.generate(messages, temperature=0.2, max_tokens=800)

    assert result.content == "根据知识库，核心版本计划在 14 天内完成。[来源 1]"
    assert result.model == "deepseek-v4-flash"
    assert result.usage == ChatModelUsage(
        prompt_tokens=120,
        completion_tokens=20,
        total_tokens=140,
    )
    assert resource.calls == [
        {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": "只根据知识库上下文回答。"},
                {"role": "user", "content": "核心版本多久完成？"},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
    ]


def test_generate_allows_missing_usage() -> None:
    provider = make_provider(
        FakeCompletionsResource([make_response(with_usage=False)])
    )

    result = provider.generate(
        [ChatMessage(role="user", content="问题")],
        temperature=0,
        max_tokens=100,
    )

    assert result.usage is None


@pytest.mark.parametrize(
    ("messages", "temperature", "max_tokens", "error"),
    [
        ([], 0.2, 100, "messages cannot be empty"),
        ([ChatMessage(role="user", content="   ")], 0.2, 100, "content"),
        ([ChatMessage(role="user", content="question")], -0.1, 100, "temperature"),
        ([ChatMessage(role="user", content="question")], 2.1, 100, "temperature"),
        ([ChatMessage(role="user", content="question")], 0.2, 0, "max_tokens"),
    ],
)
def test_invalid_generate_input_is_rejected(
    messages: list[ChatMessage],
    temperature: float,
    max_tokens: int,
    error: str,
) -> None:
    provider = make_provider(FakeCompletionsResource([]))

    with pytest.raises(ChatModelInputError, match=error):
        provider.generate(messages, temperature, max_tokens)


def test_missing_chat_api_key_is_rejected() -> None:
    with pytest.raises(ChatModelConfigurationError, match="CHAT_API_KEY"):
        OpenAICompatibleChatModelProvider(
            api_key=None,
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            timeout_seconds=30,
            max_retries=0,
        )


@pytest.mark.parametrize(
    "response",
    [
        FakeChatResponse(choices=[]),
        make_response(None),
        make_response("   "),
        make_response("answer", model=""),
    ],
)
def test_invalid_provider_response_is_rejected(response: FakeChatResponse) -> None:
    provider = make_provider(FakeCompletionsResource([response]))

    with pytest.raises(ChatModelResponseError):
        provider.generate(
            [ChatMessage(role="user", content="question")],
            temperature=0.2,
            max_tokens=100,
        )


def test_timeout_is_converted_to_business_error() -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    provider = make_provider(
        FakeCompletionsResource([APITimeoutError(request=request)])
    )

    with pytest.raises(ChatModelRequestError, match="request failed"):
        provider.generate(
            [ChatMessage(role="user", content="question")],
            temperature=0.2,
            max_tokens=100,
        )


def test_rate_limit_is_retried_without_logging_secrets_or_context(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(429, request=request)
    resource = FakeCompletionsResource(
        [
            RateLimitError("rate limited", response=response, body=None),
            make_response("answer"),
        ]
    )
    secret = "secret-key-must-not-be-logged"
    context = "private-context-must-not-be-logged"
    provider = make_provider(resource, max_retries=1, api_key=secret)
    monkeypatch.setattr(
        "app.ai.llm.openai_compatible.time.sleep",
        lambda _seconds: None,
    )

    with caplog.at_level(logging.WARNING):
        result = provider.generate(
            [ChatMessage(role="user", content=context)],
            temperature=0.2,
            max_tokens=100,
        )

    assert result.content == "answer"
    assert len(resource.calls) == 2
    assert secret not in caplog.text
    assert context not in caplog.text


def test_retry_limit_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(429, request=request)
    resource = FakeCompletionsResource(
        [
            RateLimitError("rate limited", response=response, body=None),
            RateLimitError("rate limited", response=response, body=None),
        ]
    )
    provider = make_provider(resource, max_retries=1)
    monkeypatch.setattr(
        "app.ai.llm.openai_compatible.time.sleep",
        lambda _seconds: None,
    )

    with pytest.raises(ChatModelRequestError, match="request failed"):
        provider.generate(
            [ChatMessage(role="user", content="question")],
            temperature=0.2,
            max_tokens=100,
        )
    assert len(resource.calls) == 2


def test_factory_uses_independent_chat_settings() -> None:
    settings = Settings(
        _env_file=None,
        chat_api_key="chat-only-key",
        chat_base_url="https://api.deepseek.com",
        chat_model="deepseek-v4-flash",
        chat_timeout_seconds=15,
        chat_max_retries=1,
    )

    provider = create_chat_model_provider(settings)

    assert isinstance(provider, OpenAICompatibleChatModelProvider)
    assert provider.model_name == "deepseek-v4-flash"


def test_settings_do_not_expose_chat_api_key() -> None:
    secret = "real-secret-must-not-appear"
    settings = Settings(_env_file=None, chat_api_key=secret)

    assert secret not in repr(settings)
    assert secret not in str(settings.model_dump())
    assert settings.chat_api_key is not None
    assert settings.chat_api_key.get_secret_value() == secret


def test_cached_factory_reuses_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ai.llm import factory

    provider = make_provider(FakeCompletionsResource([]))
    call_count = 0

    def create_provider() -> OpenAICompatibleChatModelProvider:
        nonlocal call_count
        call_count += 1
        return provider

    factory.get_chat_model_provider.cache_clear()
    monkeypatch.setattr(factory, "create_chat_model_provider", create_provider)
    try:
        assert factory.get_chat_model_provider() is provider
        assert factory.get_chat_model_provider() is provider
        assert call_count == 1
    finally:
        factory.get_chat_model_provider.cache_clear()


def test_dependency_converts_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api import dependencies

    def raise_configuration_error() -> None:
        raise ChatModelConfigurationError("secret configuration detail")

    monkeypatch.setattr(
        dependencies,
        "get_chat_model_provider",
        raise_configuration_error,
    )

    with pytest.raises(HTTPException) as exc_info:
        dependencies.get_chat_model_provider_dependency()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Chat model service is not configured"
