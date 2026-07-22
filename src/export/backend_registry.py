from __future__ import annotations

from typing import Dict, Iterable, Optional

from .backend import EDABackend, ExportRequest
from .export_result import ExportResult


class BackendRegistryError(Exception):
    """Raised when an EDA backend cannot be registered or resolved."""


class BackendRegistry:
    """Registry and dispatcher for EDA export backends."""

    def __init__(
        self,
        backends: Optional[Iterable[EDABackend]] = None,
    ) -> None:
        self._backends: Dict[str, EDABackend] = {}
        for backend in backends or ():
            self.register(backend)

    @staticmethod
    def normalize_name(name: str) -> str:
        normalized = name.strip().lower().replace("-", "_")
        if not normalized:
            raise BackendRegistryError(
                "Backend name cannot be empty."
            )
        return normalized

    def register(
        self,
        backend: EDABackend,
        *,
        replace: bool = False,
    ) -> None:
        name = self.normalize_name(backend.name)
        if name in self._backends and not replace:
            raise BackendRegistryError(
                f"Backend is already registered: {name}"
            )
        self._backends[name] = backend

    def unregister(self, name: str) -> EDABackend:
        normalized = self.normalize_name(name)
        try:
            return self._backends.pop(normalized)
        except KeyError as exc:
            raise BackendRegistryError(
                f"Unknown backend: {normalized}"
            ) from exc

    def get(self, name: str) -> EDABackend:
        normalized = self.normalize_name(name)
        try:
            return self._backends[normalized]
        except KeyError as exc:
            available = ", ".join(self.available_backends())
            suffix = (
                f" Available backends: {available}."
                if available
                else " No backends are registered."
            )
            raise BackendRegistryError(
                f"Unknown backend: {normalized}.{suffix}"
            ) from exc

    def available_backends(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))

    def export(
        self,
        backend: str,
        request: ExportRequest,
    ) -> ExportResult:
        request.validate_common()
        return self.get(backend).export(request)
