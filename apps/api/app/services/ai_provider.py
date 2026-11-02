"""Central AI provider service for the AI Sales Agent."""

from __future__ import annotations

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.core.config import settings


class AIProviderError(RuntimeError):
    """Base error raised when the AI provider cannot respond."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when AI provider configuration is invalid."""


class AIProviderUnavailableError(AIProviderError):
    """Raised when the configured AI provider is unavailable."""


class AIProviderService:
    """Central interface to the configured AI provider."""

    def __init__(self) -> None:
        provider = settings.ai_provider.strip().lower()

        if provider != "openai":
            raise AIProviderConfigurationError(
                f"Unsupported AI provider: {provider}"
            )

        if not settings.ai_api_key.strip():
            raise AIProviderConfigurationError(
                "AI_API_KEY is not configured."
            )

        if not settings.ai_model.strip():
            raise AIProviderConfigurationError(
                "AI_MODEL is not configured."
            )

        self.provider = provider
        self.model = settings.ai_model.strip()

        self.client = OpenAI(
            api_key=settings.ai_api_key,
            timeout=settings.ai_timeout_seconds,
        )

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text response from the configured model."""

        if not system_prompt.strip():
            raise AIProviderError(
                "System prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise AIProviderError(
                "User prompt cannot be empty."
            )

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=settings.ai_max_output_tokens,
            )

        except AuthenticationError as exc:
            raise AIProviderConfigurationError(
                "AI provider authentication failed."
            ) from exc

        except RateLimitError as exc:
            raise AIProviderUnavailableError(
                "AI provider rate limit was reached."
            ) from exc

        except APITimeoutError as exc:
            raise AIProviderUnavailableError(
                "AI provider request timed out."
            ) from exc

        except APIConnectionError as exc:
            raise AIProviderUnavailableError(
                "Unable to connect to the AI provider."
            ) from exc

        except APIStatusError as exc:
            raise AIProviderUnavailableError(
                "AI provider returned an unsuccessful response."
            ) from exc

        except Exception as exc:
            raise AIProviderError(
                "Unexpected AI provider failure."
            ) from exc

        output = (response.output_text or "").strip()

        if not output:
            raise AIProviderError(
                "AI provider returned an empty response."
            )

        return output