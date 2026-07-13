from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


ChatRole = Literal["system", "user", "assistant"]


class ChatModelError(Exception):
    """Base error for chat model operations."""


class ChatModelConfigurationError(ChatModelError):
    """Raised when the chat model is not configured correctly."""


class ChatModelInputError(ChatModelError):
    """Raised when a chat model request contains invalid input."""


class ChatModelRequestError(ChatModelError):
    """Raised when the provider request cannot be completed."""


class ChatModelResponseError(ChatModelError):
    """Raised when the provider returns an invalid response."""


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class ChatModelUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ChatModelResult:
    content: str
    model: str
    usage: ChatModelUsage | None = None


class ChatModelProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured chat model name."""

    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ChatModelResult:
        """Generate one chat completion from the supplied messages."""
