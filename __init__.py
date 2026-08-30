"""Yandex Search API (v2, web) Hermes plugin — search-only provider.

Mirrors the bundled layout (``plugins/web/brave_free/``): ``provider.py`` holds the
provider class, ``__init__.py::register(ctx)`` registers an instance.

Uses a *relative* import so the plugin loads identically as a bundled provider
(``plugins/web/yandex/``) and as a user plugin (``~/.hermes/plugins/web/yandex``,
imported by Hermes as ``hermes_plugins.web__yandex``).
"""

from __future__ import annotations

from .provider import YandexWebSearchProvider


def register(ctx) -> None:
    """Register the Yandex provider with the plugin context."""
    ctx.register_web_search_provider(YandexWebSearchProvider())