"""Tests for the Yandex web-search Hermes plugin.

``httpx.post`` is monkeypatched, so no network leaves the machine.
"""
import base64
import json

import httpx
import pytest

import provider

SAMPLE_XML = """<response>
<doc id="1">
<url>https://example.com/1</url>
<title>Кофе</title>
<headline>Лучшая <hlword>2026</hlword> кофемашина</headline>
</doc>
<doc id="2">
<url>https://example.com/2</url>
<passage>про кофе каждый день</passage>
</doc>
<doc id="3">
<headline>без ссылки</headline>
</doc>
</response>"""


class FakeResp:
    def __init__(self, payload, *, status_error=None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


def _api_resp(xml):
    return FakeResp({"rawData": base64.b64encode(xml.encode()).decode()})


@pytest.fixture
def patch_post(monkeypatch):
    captured = {}

    def fake(url, **kw):
        captured["url"] = url
        captured["kwargs"] = kw
        return captured["result"]

    monkeypatch.setattr(httpx, "post", fake)
    return captured


def test_setup_schema_env_vars():
    schema = provider.YandexWebSearchProvider().get_setup_schema()
    assert [v["key"] for v in schema["env_vars"]] == [
        "YANDEX_SEARCH_API_KEY",
        "YANDEX_SEARCH_FOLDER_ID",
    ]


def test_provider_flags():
    p = provider.YandexWebSearchProvider()
    assert p.name == "yandex"
    assert p.supports_search() is True
    assert p.supports_extract() is False


def test_is_available_needs_key(monkeypatch):
    monkeypatch.delenv("YANDEX_SEARCH_API_KEY", raising=False)
    assert provider.YandexWebSearchProvider().is_available() is False
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "k")
    assert provider.YandexWebSearchProvider().is_available() is True


def test_search_returns_error_without_key(monkeypatch):
    monkeypatch.delenv("YANDEX_SEARCH_API_KEY", raising=False)
    out = provider.YandexWebSearchProvider().search("кофе")
    assert out["success"] is False
    assert "API_KEY" in out["error"]


def test_search_success_parses_results(monkeypatch, patch_post):
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "test-key")
    patch_post["result"] = _api_resp(SAMPLE_XML)
    out = provider.YandexWebSearchProvider().search("кофе")
    assert out["success"] is True
    web = out["data"]["web"]
    assert len(web) == 2  # doc without <url> is skipped
    assert web[0] == {
        "title": "Лучшая 2026 кофемашина",  # <hlword> stripped
        "url": "https://example.com/1",
        "description": "Лучшая 2026 кофемашина",
        "position": 1,
    }
    # RU defaults sent in the request body
    body = patch_post["kwargs"]["json"]
    assert body["query"]["searchType"] == "SEARCH_TYPE_RU"
    assert body["query"]["region"] == 225


def test_search_limit_clamped_and_sliced(monkeypatch, patch_post):
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "k")
    patch_post["result"] = _api_resp(SAMPLE_XML)
    provider.YandexWebSearchProvider().search("кофе", limit=50)
    assert patch_post["kwargs"]["json"]["groupSpec"]["groupsOnPage"] == 20  # 50 -> 20
    out = provider.YandexWebSearchProvider().search("кофе", limit=1)
    assert len(out["data"]["web"]) == 1  # sliced to limit


def test_search_folder_id_optional(monkeypatch, patch_post):
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "k")
    monkeypatch.delenv("YANDEX_SEARCH_FOLDER_ID", raising=False)
    monkeypatch.delenv("FOLDER_ID", raising=False)  # provider also honours the generic FOLDER_ID
    patch_post["result"] = _api_resp(SAMPLE_XML)
    provider.YandexWebSearchProvider().search("кофе")
    assert "folderId" not in patch_post["kwargs"]["json"]

    monkeypatch.setenv("YANDEX_SEARCH_FOLDER_ID", "folder-1")
    provider.YandexWebSearchProvider().search("кофе")
    assert patch_post["kwargs"]["json"]["folderId"] == "folder-1"


def test_search_http_error(monkeypatch, patch_post):
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "k")
    req = httpx.Request("POST", provider._WEB_SEARCH_URL)
    resp = httpx.Response(429, request=req)
    patch_post["result"] = FakeResp({}, status_error=httpx.HTTPStatusError(
        "rate limited", request=req, response=resp,
    ))
    out = provider.YandexWebSearchProvider().search("кофе")
    assert out["success"] is False
    assert "429" in out["error"]


def test_search_parse_error(monkeypatch, patch_post):
    monkeypatch.setenv("YANDEX_SEARCH_API_KEY", "k")
    patch_post["result"] = FakeResp({})  # no 'rawData'
    out = provider.YandexWebSearchProvider().search("кофе")
    assert out["success"] is False
    assert out["error"] == "Could not parse Yandex Search response"