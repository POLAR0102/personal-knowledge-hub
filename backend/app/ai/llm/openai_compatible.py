import logging
import time
from typing import Protocol, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from app.ai.llm.base import (
    ChatMessage,
    ChatModelConfigurationError,
    ChatModelInputError,
    ChatModelProvider,
    ChatModelRequestError,
    ChatModelResponseError,
    ChatModelResult,
    ChatModelUsage,
)

logger = logging.getLogger(__name__)


class _ResponseMessage(Protocol):
    content: str | None


class _ResponseChoice(Protocol):
    message: _ResponseMessage


class _ResponseUsage(Protocol):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class _ChatCompletionResponse(Protocol):
    choices: list[_ResponseChoice]
    model: str
    usage: _ResponseUsage | None


class _CompletionsResource(Protocol):
    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> _ChatCompletionResponse: ...


class _ChatResource(Protocol):
    completions: _CompletionsResource


class _ChatClient(Protocol):
    chat: _ChatResource


class OpenAICompatibleChatModelProvider(ChatModelProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        client: _ChatClient | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ChatModelConfigurationError("CHAT_API_KEY is not configured")
        if not model.strip():
            raise ChatModelConfigurationError("CHAT_MODEL is not configured")
        if timeout_seconds <= 0:
            raise ChatModelConfigurationError(
                "CHAT_TIMEOUT_SECONDS must be greater than 0"
            )
        if max_retries < 0:
            raise ChatModelConfigurationError("CHAT_MAX_RETRIES cannot be negative")

        self._model = model.strip()
        self._max_retries = max_retries
        self._client = client or self._create_client(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ChatModelResult:
        self._validate_input(messages, temperature, max_tokens)
        request_messages = [
            {"role": message.role, "content": message.content}
            for message in messages
        ]
        response = self._request_completion(
            request_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._parse_response(response)

    @staticmethod
    def _create_client(
        *,
        api_key: str,
        base_url: str | None,
        timeout_seconds: float,
    ) -> _ChatClient:
        options: dict[str, object] = {
            "api_key": api_key,
            "timeout": timeout_seconds,
            "max_retries": 0,
        }
        if base_url and base_url.strip():
            options["base_url"] = base_url.strip()
        return cast(_ChatClient, OpenAI(**options))

    def _request_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> _ChatCompletionResponse:
        for attempt in range(self._max_retries + 1):
            try:
                return self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except OpenAIError as exc:
                if not self._is_retryable(exc) or attempt >= self._max_retries:
                    raise ChatModelRequestError(
                        "Chat model provider request failed"
                    ) from exc
                logger.warning(
                    "Chat model request failed with %s; retrying (%s/%s)",
                    type(exc).__name__,
                    attempt + 1,
                    self._max_retries,
                )
                time.sleep(min(2**attempt, 4))

        raise ChatModelRequestError("Chat model provider request failed")

    @staticmethod
    def _validate_input(
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> None:
        if not messages:
            raise ChatModelInputError("Chat messages cannot be empty")
        if any(not message.content.strip() for message in messages):
            raise ChatModelInputError("Chat message content cannot be empty")
        if not 0 <= temperature <= 2:
            raise ChatModelInputError("Chat temperature must be between 0 and 2")
        if max_tokens < 1:
            raise ChatModelInputError("Chat max_tokens must be at least 1")

    @staticmethod
    def _is_retryable(exc: OpenAIError) -> bool:
        if isinstance(exc, (APIConnectionError, RateLimitError)):
            return True
        return isinstance(exc, APIStatusError) and (
            exc.status_code in {408, 409, 429} or exc.status_code >= 500
        )

    @staticmethod
    def _parse_response(response: _ChatCompletionResponse) -> ChatModelResult:
        if not response.choices:
            raise ChatModelResponseError("Chat model response contains no choices")

        content = response.choices[0].message.content
        if content is None or not content.strip():
            raise ChatModelResponseError("Chat model response content is empty")
        if not response.model or not response.model.strip():
            raise ChatModelResponseError("Chat model response model is missing")

        usage = None
        if response.usage is not None:
            usage = ChatModelUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
        return ChatModelResult(
            content=content.strip(),
            model=response.model.strip(),
            usage=usage,
        )
