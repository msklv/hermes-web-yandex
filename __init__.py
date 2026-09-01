"""Yandex Search API (v2, web) Hermes plugin — search-only provider.

Mirrors the bundled layout (``plugins/web/brave_free/``): ``provider.py`` holds the
provider class, ``__init__.py::register(ctx)`` registers an instance.

Uses a *relative* import so the plugin loads identically as a bundled provider
(``plugins/web/yandex/``) and as a user plugin (``~/.hermes/plugins/web/yandex``,
imported by Hermes as ``hermes_plugins.web__yandex``).
"""

from __future__ import annotations

try:
    from .provider import YandexWebSearchProvider
except ImportError:
    # Imported without a parent package (e.g. by test tooling / linting
    # walking the plugin dir). Hermes always imports this as a package member, so
    # the relative import above still works at runtime.
    YandexWebSearchProvider = None  # type: ignore[assignment]


def register(ctx) -> None:
    """Register the Yandex provider with the plugin context."""
    assert YandexWebSearchProvider is not None
    ctx.register_web_search_provider(YandexWebSearchProvider())