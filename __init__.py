"""Yandex Search API (v2, web) Hermes plugin — search-only provider.

Mirrors the bundled layout (``plugins/web/brave_free/``): ``provider.py`` holds the
provider class, ``__init__.py::register(ctx)`` registers an instance.
"""

from __future__ import annotations

from plugins.web.yandex.provider import YandexWebSearchProvider


def register(ctx) -> None:
    """Register the Yandex provider with the plugin context."""
    ctx.register_web_search_provider(YandexWebSearchProvider())