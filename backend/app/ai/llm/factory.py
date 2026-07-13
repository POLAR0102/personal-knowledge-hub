from functools import lru_cache

from app.ai.llm.base import ChatModelProvider
from app.ai.llm.openai_compatible import OpenAICompatibleChatModelProvider
from app.core.config import Settings, get_settings


def create_chat_model_provider(
    settings: Settings | None = None,
) -> ChatModelProvider:
    current_settings = settings or get_settings()
    return OpenAICompatibleChatModelProvider(
        api_key=(
            current_settings.chat_api_key.get_secret_value()
            if current_settings.chat_api_key is not None
            else None
        ),
        base_url=current_settings.chat_base_url,
        model=current_settings.chat_model,
        timeout_seconds=current_settings.chat_timeout_seconds,
        max_retries=current_settings.chat_max_retries,
    )


@lru_cache
def get_chat_model_provider() -> ChatModelProvider:
    return create_chat_model_provider()
