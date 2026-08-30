# hermes-web-yandex

[Yandex Search API (v2 web)](https://yandex.cloud/ru/docs/searchapi/) as a
**[Hermes Agent](https://hermes-agent.nousresearch.com)** web-search backend plugin.

```
Hermes web_search  →  Yandex Search API v2 (searchapi.api.cloud.yandex.net)
```

- **Search only** (`supports_extract = False`) — pair with Firecrawl / Tavily / Exa
  for `web_extract`. Perfect fit for `web.search_backend: yandex` +
  `web.extract_backend: firecrawl`.
- **RU-native**: Russian search type (`SEARCH_TYPE_RU`) by default, region `225` (Россия),
  typo correction enabled — good for Cyrillic queries.
- Uses an API key (no CAPTCHA / no IP scraping). There is **no official** yandex provider in
  the Hermes tree (`plugins/web/`) — this is the user-plugin equivalent.

## Requirements

- Hermes Agent (`hermes` CLI / desktop app).
- Yandex Cloud Search API key and folder id. Get them at
  [cloud.yandex.ru/docs/searchapi](https://yandex.cloud/ru/docs/searchapi/).
  (You only need the **web search** (non-generative) key.)
- Python `httpx` available in the Hermes venv (ships with Hermes).

## Install

Drop the repo into the Hermes **user** plugin directory and enable it:

```bash
mkdir -p ~/.hermes/plugins/web/yandex
# copy files from this repo:
cp provider.py __init__.py plugin.yaml ~/.hermes/plugins/web/yandex/

# credentials — add to ~/.hermes/.env
#   YANDEX_SEARCH_API_KEY=...
#   YANDEX_SEARCH_FOLDER_ID=...

hermes plugins enable web-yandex
```

## Usage

Select Yandex for search, keep extraction on Firecrawl:

```bash
hermes config set web.search_backend yandex
hermes config set web.extract_backend firecrawl   # already your value
```

Verify:

```bash
hermes plugins list                     # web-yandex  enabled
hermes config get web                  # search_backend: yandex
```

Then a `web_search "<запрос>"` call in Hermes will hit the Yandex Search API.

## Smoke test without setting the backend

From the repo, import the provider with the keys exported and call it directly:

```bash
export YANDEX_SEARCH_API_KEY=... YANDEX_SEARCH_FOLDER_ID=...
python -c "
import sys; sys.path.insert(0, '<path-to-hermes-dev>/$HERMES_REPO')
from plugins.web.yandex.provider import YandexWebSearchProvider
import json; print(json.dumps(YandexWebSearchProvider().search('кофемашина', limit=3), ensure_ascii=False, indent=2))
"
```

## Files

- `provider.py` — `YandexWebSearchProvider(WebSearchProvider)`
- `__init__.py` — `register(ctx)` → `ctx.register_web_search_provider(...)`
- `plugin.yaml` — `kind: backend`, `provides_web_providers: [yandex]`
- `LICENSE`, `README.md`

## Details

| | |
|---|---|
| Endpoint | `POST https://searchapi.api.cloud.yandex.net/v2/web/search` |
| Auth | `Authorization: Api-Key <key>` |
| Format | `responseFormat: FORMAT_XML` → base64 in `rawData`, `<doc>` blocks parsed |
| Region | `225` (Россия), `SEARCH_TYPE_RU` / `LOCALIZATION_RU`, `fixTypoMode` on |
| Limit | `limit` clamped to `groupsOnPage` [1..20] |

## License

MIT