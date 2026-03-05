"""Polarity Agent exception hierarchy."""

from __future__ import annotations


class PolarityError(Exception):
    """Root exception for every error raised by Polarity Agent."""


class ProviderError(PolarityError):
    """An LLM provider returned an unexpected response or failed."""


class ProviderNotInstalledError(PolarityError):
    """Raised when a provider's SDK dependency is missing."""

    def __init__(self, package: str, install_hint: str) -> None:
        self.package = package
        self.install_hint = install_hint
        super().__init__(
            f"Required package '{package}' is not installed. Install it with: {install_hint}"
        )
