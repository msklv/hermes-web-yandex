# hermes-web-yandex

[Yandex Search API (v2 web)](https://aistudio.yandex.ru/ru/docs/search-api/concepts/) as a
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
- A [Yandex Search API](https://aistudio.yandex.ru/ru/docs/search-api/) key
  (and optionally a folder id) — see [Credentials](#credentials) below.
- Python `httpx` available in the Hermes venv (ships with Hermes).

## Credentials

There are two environment variables, both placed in `~/.hermes/.env`:

| Variable | Required | Where to get it |
|---|---|---|
| `YANDEX_SEARCH_API_KEY` | ✅ yes | [Create an API key](#create-an-api-key) (AI Studio) |
| `YANDEX_SEARCH_FOLDER_ID` | ⚠️ optional | [Get the folder id](#get-the-folder-id) (AI Studio) |

### Create an API key

Yandex AI Studio is part of Yandex Cloud and reuses its auth. This plugin uses an **API key**
(`Authorization: Api-Key <key>`), which the docs recommend over a short-lived IAM token.

1. Open the **AI Studio console**: <https://aistudio.yandex.cloud/platform/>.
2. Click **Создать API-ключ** (*Create API key*) in the top-right corner.
3. *(Optional)* Edit the key description so you can find it later.
4. Choose the key lifetime.
5. Click **Создать** (*Create*), then **save the key right away** — it is shown only once
   and becomes unavailable after the dialog closes.

This automatically creates a service account with the minimal roles you need —
notably `search-api.webSearch.user` (access to Yandex Search API v2) — so **no extra
role assignment is required** for this plugin.

To reuse an existing service account instead: in the same console, open **Доступ** (*Access*) →
tab **API-ключи** → **Создать API-ключ** for the account.

Docs: <https://aistudio.yandex.ru/ru/docs/ai-studio/operations/get-api-key>

### Get the folder id

`YANDEX_SEARCH_FOLDER_ID` is **optional**: for the service-account API key created above,
Yandex Search API automatically works in the service account's catalog, so you can omit it.
Pass it only if you want to pin the catalog explicitly.

To get it: in the AI Studio console, hover over the **catalog name** at the top of the screen
and click the copy icon that appears — the id lands in your clipboard.

Docs: <https://aistudio.yandex.ru/ru/docs/search-api/concepts/web-search> (the `folderId` field)

```bash
# ~/.hermes/.env
YANDEX_SEARCH_API_KEY=AQVN...your-key...
YANDEX_SEARCH_FOLDER_ID=b1g...your-folder-id...   # optional
```

## Install

Drop the repo into the Hermes **user** plugin directory and enable it:

```bash
mkdir -p ~/.hermes/plugins/web/yandex
# copy files from this repo:
cp provider.py __init__.py plugin.yaml ~/.hermes/plugins/web/yandex/

# credentials — add to ~/.hermes/.env (see Credentials above)
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

## Documentation

- **Yandex Search API — modes & search types (Overview):**
  <https://aistudio.yandex.ru/ru/docs/search-api/concepts/>
- Text search & all request parameters (`searchType`, `familyMode`, `groupsOnPage`, `folderId`, …):
  <https://aistudio.yandex.ru/ru/docs/search-api/concepts/web-search>
- Authentication (`Api-Key` / IAM token, folder id rules):
  <https://aistudio.yandex.ru/ru/docs/search-api/api-ref/authentication>
- Creating an API key:
  <https://aistudio.yandex.ru/ru/docs/ai-studio/operations/get-api-key>
- Search regions:
  <https://aistudio.yandex.ru/ru/docs/search-api/reference/regions>

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