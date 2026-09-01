"""Yandex Search API (v2, web) — Hermes web-search provider plugin.

Search-only provider implementing :class:`agent.web_search_provider.WebSearchProvider`.
Yandex Search API has no free content-extraction endpoint, so pair this with a
content provider (Firecrawl / Tavily / Exa) for ``web_extract``.

Config keys::

    web:
      search_backend: "yandex"     # explicit per-capability override
      backend: "yandex"             # shared fallback

Auth env vars (put in ``~/.hermes/.env``)::

    YANDEX_SEARCH_API_KEY=...        # https://aistudio.yandex.ru/ru/docs/search-api/
    YANDEX_SEARCH_FOLDER_ID=...      # optional — service-account keys work without it
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, Dict, List, Optional

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_WEB_SEARCH_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
_DEFAULT_TIMEOUT = 20

# Default region 225 = Russia; 213 = Moscow. The v2 API biases ranking toward it.
_DEFAULT_REGION_RU = 225
_SEARCH_TYPE_RU = "SEARCH_TYPE_RU"
_LOCALIZATION_RU = "LOCALIZATION_RU"


def _env(name: str) -> str:
    from agent.web_search_provider import get_provider_env

    return get_provider_env(name)


# ---------------------------------------------------------------------------
# XML response helpers
# ---------------------------------------------------------------------------

def _split_docs(xml_content: str) -> List[str]:
    """Split the response XML into individual ``<doc>`` blocks (lossy but robust)."""
    docs: List[str] = []
    current: List[str] = []
    in_doc = False
    for line in xml_content.split("\n"):
        if not in_doc and "<doc " in line and "id=" in line:
            in_doc = True
            current = [line]
        elif in_doc and "</doc>" in line:
            current.append(line)
            docs.append("\n".join(current))
            in_doc = False
        elif in_doc:
            current.append(line)
    return docs


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"</?hlword>", "", text).strip()


def _find_one(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _find_all(pattern: str, text: str) -> List[str]:
    return re.findall(pattern, text)


def _parse_docs(xml_content: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for doc_string in _split_docs(xml_content):
        url = _find_one(r"<url>(.*?)</url>", doc_string)
        if not url:
            continue
        content = (
            _find_one(r"<headline>(.*?)</headline>", doc_string)
            or _find_one(r"<title>(.*?)</title>", doc_string)
            or " ".join(p for p in _find_all(r"<passage>(.*?)</passage>", doc_string) if p)
            or _find_one(r"<extended-text>(.*?)</extended-text>", doc_string)
        )
        if not content:
            continue
        title = _clean(content)
        results.append({"url": url, "title": title, "description": title})
    return results


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class YandexWebSearchProvider(WebSearchProvider):
    """Search-only Yandex provider using the Yandex Cloud Search API v2.

    Russian is the default search language (SEARCH_TYPE_RU, region 225).
    """

    @property
    def name(self) -> str:
        # Stable id for web.search_backend / web.backend config keys.
        return "yandex"

    @property
    def display_name(self) -> str:
        return "Yandex Search API (v2 web)"

    def is_available(self) -> bool:
        # Cheap check — no network. Runs on every `hermes tools` paint.
        return bool(_env("YANDEX_SEARCH_API_KEY"))

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def get_setup_schema(self) -> Dict[str, Any]:
        # Drives the API-key fields in the desktop `hermes tools` / Settings → Web
        # Search panel. Without this override the UI inherits an empty `env_vars` list
        # and shows "No API key required" with nowhere to paste the key.
        return {
            "name": "Yandex Search API (v2 web)",
            "badge": "ru",
            "tag": "Yandex Cloud Search API v2 — RU-native search. Requires an AI Studio API key.",
            "env_vars": [
                {
                    "key": "YANDEX_SEARCH_API_KEY",
                    "prompt": "Yandex AI Studio API key",
                    "url": "https://aistudio.yandex.ru/ru/docs/search-api/",
                },
                {
                    "key": "YANDEX_SEARCH_FOLDER_ID",
                    "prompt": "Yandex Cloud folder id (optional)",
                    "url": "https://aistudio.yandex.ru/ru/docs/search-api/concepts/web-search",
                },
            ],
        }

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        api_key = _env("YANDEX_SEARCH_API_KEY")
        if not api_key:
            return {"success": False, "error": "YANDEX_SEARCH_API_KEY is not set"}

        folder_id = _env("YANDEX_SEARCH_FOLDER_ID") or _env("FOLDER_ID") or ""

        groups_on_page = max(1, min(int(limit), 20))

        body: Dict[str, Any] = {
            "query": {
                "searchType": _SEARCH_TYPE_RU,
                "queryText": query,
                "fixTypoMode": "FIX_TYPO_MODE_ON",  # helps Russian queries a lot
                "familyMode": "FAMILY_MODE_NONE",
                "region": _DEFAULT_REGION_RU,
            },
            "groupSpec": {"groupsOnPage": groups_on_page},
            "l10n": _LOCALIZATION_RU,
            "responseFormat": "FORMAT_XML",  # cheapest format; rawData is base64 XML
        }
        if folder_id:
            body["folderId"] = folder_id

        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            return {"success": False, "error": f"httpx is required: {exc}"}

        try:
            resp = httpx.post(
                _WEB_SEARCH_URL,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Api-Key {api_key}",
                },
                timeout=_DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Yandex Search HTTP error: %s", exc)
            return {
                "success": False,
                "error": f"Yandex Search returned HTTP {exc.response.status_code}",
            }
        except httpx.RequestError as exc:
            logger.warning("Yandex Search request error: %s", exc)
            return {"success": False, "error": f"Could not reach Yandex Search: {exc}"}

        try:
            payload = resp.json()
            xml_content = base64.b64decode(payload["rawData"]).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Yandex Search parse error: %s", exc)
            return {"success": False, "error": "Could not parse Yandex Search response"}

        web_results = [
            {
                "title": hit["title"],
                "url": hit["url"],
                "description": hit["description"],
                "position": i + 1,
            }
            for i, hit in enumerate(_parse_docs(xml_content)[:limit])
        ]

        logger.info("Yandex Search '%s': %d results", query, len(web_results))
        return {"success": True, "data": {"web": web_results}}