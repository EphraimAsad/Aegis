"""Provider manager for handling multiple AI providers.

The ProviderManager is responsible for:
- Registering and managing provider instances
- Selecting the appropriate provider based on configuration
- Providing a unified interface for provider operations
"""

from typing import Any

from app.config import get_settings
from app.core.exceptions import ProviderNotFoundError
from app.providers.base import BaseProvider


class ProviderManager:
    """
    Manager for AI provider instances.

    Handles provider registration, selection, and lifecycle.
    """

    def __init__(self) -> None:
        """Initialize the provider manager."""
        self._providers: dict[str, BaseProvider] = {}
        self._default_provider: str | None = None

    def register(self, provider: BaseProvider, set_default: bool = False) -> None:
        """
        Register a provider instance.

        Args:
            provider: The provider instance to register
            set_default: Whether to set this as the default provider
        """
        self._providers[provider.name] = provider
        if set_default or self._default_provider is None:
            self._default_provider = provider.name

    def unregister(self, name: str) -> None:
        """
        Unregister a provider.

        Args:
            name: Provider name to unregister
        """
        if name in self._providers:
            del self._providers[name]
            if self._default_provider == name:
                self._default_provider = next(iter(self._providers), None)

    def get(self, name: str | None = None) -> BaseProvider:
        """
        Get a provider by name.

        Args:
            name: Provider name. If None, returns the default provider.

        Returns:
            BaseProvider: The requested provider

        Raises:
            ProviderNotFoundError: If the provider is not found
        """
        if name is None:
            name = self._default_provider

        if name is None:
            raise ProviderNotFoundError(
                "No providers registered",
                details={"available": []},
            )

        if name not in self._providers:
            raise ProviderNotFoundError(
                f"Provider '{name}' not found",
                details={"available": list(self._providers.keys())},
            )

        return self._providers[name]

    def get_default(self) -> BaseProvider:
        """
        Get the default provider.

        Returns:
            BaseProvider: The default provider

        Raises:
            ProviderNotFoundError: If no default provider is set
        """
        return self.get(None)

    def set_default(self, name: str) -> None:
        """
        Set the default provider.

        Args:
            name: Provider name to set as default

        Raises:
            ProviderNotFoundError: If the provider is not found
        """
        if name not in self._providers:
            raise ProviderNotFoundError(
                f"Provider '{name}' not found",
                details={"available": list(self._providers.keys())},
            )
        self._default_provider = name

    def list_providers(self) -> list[str]:
        """
        List all registered provider names.

        Returns:
            list[str]: List of provider names
        """
        return list(self._providers.keys())

    def get_provider_info(self, name: str | None = None) -> dict[str, Any]:
        """
        Get detailed information about a provider.

        Args:
            name: Provider name. If None, uses default.

        Returns:
            dict: Provider information including capabilities
        """
        provider = self.get(name)
        return {
            "name": provider.name,
            "is_default": provider.name == self._default_provider,
            "capabilities": provider.capabilities.model_dump(),
        }

    def list_all_info(self) -> list[dict[str, Any]]:
        """
        Get information about all registered providers.

        Returns:
            list[dict]: List of provider information
        """
        return [self.get_provider_info(name) for name in self._providers]

    async def healthcheck_all(self) -> dict[str, bool]:
        """
        Check health of all registered providers.

        Returns:
            dict[str, bool]: Provider name to health status mapping
        """
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.healthcheck()
            except Exception:
                results[name] = False
        return results

    async def close_all(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()


# Global provider manager instance
_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """
    Get the global provider manager instance.

    Creates and initializes the manager on first call.

    Returns:
        ProviderManager: The global provider manager
    """
    global _provider_manager

    if _provider_manager is None:
        _provider_manager = ProviderManager()
        _initialize_default_providers(_provider_manager)

    return _provider_manager


def _initialize_default_providers(manager: ProviderManager) -> None:
    """
    Initialize default providers based on configuration.

    Args:
        manager: The provider manager to initialize
    """
    settings = get_settings()

    # Always register Ollama (local default)
    from app.providers.ollama import OllamaProvider

    ollama = OllamaProvider(
        base_url=settings.ollama_base_url,
        default_model=(
            settings.default_model
            if settings.default_provider == "ollama"
            else "llama2"
        ),
    )
    manager.register(ollama, set_default=(settings.default_provider == "ollama"))

    # Register OpenAI if API key is available
    if settings.openai_api_key:
        from app.providers.openai import OpenAIProvider

        openai = OpenAIProvider(
            api_key=settings.openai_api_key,
            default_model=(
                settings.default_model
                if settings.default_provider == "openai"
                else "gpt-3.5-turbo"
            ),
        )
        manager.register(openai, set_default=(settings.default_provider == "openai"))

    # Register Anthropic if API key is available
    if settings.anthropic_api_key:
        from app.providers.anthropic import AnthropicProvider

        anthropic = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            default_model=(
                settings.default_model
                if settings.default_provider == "anthropic"
                else "claude-3-5-sonnet-20241022"
            ),
        )
        manager.register(
            anthropic, set_default=(settings.default_provider == "anthropic")
        )

    # Register Google if API key is available
    if settings.google_api_key:
        from app.providers.google import GoogleProvider

        google = GoogleProvider(
            api_key=settings.google_api_key,
            default_model=(
                settings.default_model
                if settings.default_provider == "google"
                else "gemini-1.5-flash"
            ),
        )
        manager.register(google, set_default=(settings.default_provider == "google"))


async def cleanup_providers() -> None:
    """Cleanup provider connections on shutdown."""
    global _provider_manager
    if _provider_manager is not None:
        await _provider_manager.close_all()
        _provider_manager = None
