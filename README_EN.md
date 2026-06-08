# Public Opportunities Web Scraper

Telegram bot for querying public and academic opportunities from initial sources in Paraiba, Brazil. The user provides a country and state; the bot builds a formal JSON request, calls the configured scraper pipeline, and returns normalized results in Telegram.

The project is organized to keep the Telegram interface separate from data collection and normalization. The bot does not process HTML, PDF, or raw text: it validates and renders only the normalized JSON returned by the scraper.

## Overview

The current flow covers:

- Query by country and state through Telegram.
- Initial sources: UFPB and Paraiba state notices.
- Default filters: `mestrado`, `doutorado`, `pedagogico`, `perito`.
- Responses for `success`, `empty`, `partial_success`, and `error`.
- Render deployment as a background worker.
- Optional Hugging Face enrichment when `HF_API_KEY` is configured.

## Modular Architecture

- `telegram_bot/bot.py`: Telegram bot entrypoint with `ConversationHandler`.
- `telegram_bot/contracts.py`: Bot -> Scraper contract creation and formal Scraper -> Bot validation.
- `telegram_bot/scraper_client.py`: integration point configurable through `SCRAPER_BACKEND`.
- `telegram_bot/messages.py`: Telegram message rendering.
- `scraper/pipeline.py`: pipeline that collects candidates, normalizes, filters, sorts, and returns formal JSON.
- `scraper/sources.py`: initial sources and HTML listing parsers.
- `scraper/hf_classifier.py`: optional Hugging Face classification.
- `schemas/scraper_contract.py`: scraper pipeline contract.
- `render.yaml`: Render worker deployment configuration.
- `tests/`: contract, pipeline, fixture, and rendering tests.

## Telegram Flow

1. User sends `/start` or `/buscar`.
2. Bot asks for the country.
3. User sends `BR`.
4. Bot asks for the state.
5. User sends a state abbreviation, for example `PB`.
6. Bot builds the Bot -> Scraper JSON.
7. Bot calls the function indicated by `SCRAPER_BACKEND`.
8. Scraper returns normalized JSON.
9. Bot validates the formal contract.
10. Bot renders the response in Telegram.

`ConversationHandler` states:

- `ESPERANDO_PAIS`: accepts `BR`, `Brasil`, or `Brazil`.
- `ESPERANDO_ESTADO`: accepts Brazilian state abbreviations, including `PB`.

During the scraper call, the bot sends `typing...`.

## Bot -> Scraper Contract

Example payload sent by the bot:

```json
{
  "request_id": "11111111-1111-1111-1111-111111111111",
  "country": "BR",
  "state": "PB",
  "keywords": ["mestrado", "doutorado", "pedagogico", "perito"],
  "sources": ["ufpb", "editais_pb"],
  "language": "pt-BR",
  "limit": 20,
  "page": 1,
  "sort": "relevance",
  "include_closed": false
}
```

Fields:

- `request_id`: search UUID.
- `country`: search country. Implemented: `BR`.
- `state`: search state. Example: `PB`.
- `keywords`: accepted filter tags.
- `sources`: enabled sources. Implemented: `ufpb`, `editais_pb`.
- `language`: response/normalization language. Default: `pt-BR`.
- `limit`: maximum number of items per page.
- `page`: requested page.
- `sort`: `relevance` or `date`.
- `include_closed`: includes closed opportunities when `true`.

## Scraper -> Bot Contract

Required top-level fields:

```json
{
  "request_id": "11111111-1111-1111-1111-111111111111",
  "status": "success",
  "country": "BR",
  "state": "PB",
  "applied_filters": {
    "keywords": ["mestrado", "doutorado"],
    "sources": ["ufpb", "editais_pb"]
  },
  "summary": {
    "total_found": 13,
    "total_returned": 13,
    "partial_failures": 0
  },
  "items": [],
  "warnings": []
}
```

Allowed `status` values:

- `success`
- `empty`
- `partial_success`
- `error`

Required `summary` fields:

- `total_found`: total found after filters.
- `total_returned`: total returned in the current page.
- `partial_failures`: number of sources with partial failure.

`warnings` must be a list of strings. Timeouts, HTTP 503, and unavailable sources may appear here without breaking delivery when valid results exist.

### Normalized Item

Each item must contain all fields below:

```json
{
  "item_id": "2fcb332afd49191f",
  "title": "Convocacao de aprovados para Perito Oficial Criminal",
  "category": "public_exam",
  "subcategory": "perito",
  "institution": "Governo do Estado da Paraiba",
  "source": "editais_pb",
  "location": {
    "country": "BR",
    "state": "PB",
    "city": null
  },
  "published_at": "2025-02-19",
  "deadline": "2025-02-21",
  "status": "closed",
  "match_tags": ["perito"],
  "description_clean": "Convocacao de aprovados para Perito Oficial Criminal.",
  "source_url": "https://codata.pb.gov.br/institucional/editais-concursos/convocacao-perito.pdf",
  "document_urls": [
    "https://codata.pb.gov.br/institucional/editais-concursos/convocacao-perito.pdf"
  ],
  "confidence": 0.7
}
```

Item rules:

- `source_url` is required.
- `document_urls` is a list of document URLs and may be empty.
- `match_tags` accepts only `mestrado`, `doutorado`, `pedagogico`, `perito`.
- `published_at` and `deadline` must use `YYYY-MM-DD` or `null`.
- `location.country` and `location.state` are required strings.
- `location.city` must exist, but may be a non-empty string or `null`.
- `confidence` must be between `0` and `1`.
- Item `status` may be `open`, `closed`, or `unknown`.

## Running Locally

Requirements:

- Python 3.13 or compatible version.
- Telegram bot token.

Installation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run with the real scraper:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="scraper.pipeline:run_scraper_pipeline"
$env:LOG_LEVEL="INFO"
python -m telegram_bot.bot
```

Run with the local fixture:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -m telegram_bot.bot
```

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token. |
| `SCRAPER_BACKEND` | No | Function in `modulo:funcao` format. Default: `scraper.pipeline:run_scraper_pipeline`. |
| `LOG_LEVEL` | No | Log level. Default: `INFO`. |
| `HF_API_KEY` | No | Key for optional Hugging Face enrichment. |
| `HF_ENDPOINT` | No | Alternative Hugging Face inference endpoint. |

## Render Deployment

Deployment uses `render.yaml` as a background worker, not as a web service:

```yaml
services:
  - type: worker
    name: oportunidades-publicas-telegram-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m telegram_bot.bot
```

Steps:

1. Create a new Render Blueprint pointing to the repository.
2. Confirm that the generated service is a `worker`.
3. Configure `TELEGRAM_BOT_TOKEN` as a secret.
4. Keep `SCRAPER_BACKEND=scraper.pipeline:run_scraper_pipeline`.
5. Configure `HF_API_KEY` and `HF_ENDPOINT` only if Hugging Face enrichment is needed.
6. Deploy.
7. Check worker logs and send `/buscar` to the bot.

## Initial Sources

Source `ufpb`:

- UFPB SIGAA selective processes.
- UFPB PRPG open selective processes.
- UFPB opportunities portal.

Source `editais_pb`:

- Paraiba state notices.
- Paraiba Central de Compras.
- CODATA PB notices and public examinations.

Sources may return timeout, 503, or HTML different from expected. In these cases, the scraper records `warnings` and attempts to continue with the remaining sources.

## Known Limitations

- External network access may fail because of timeout, DNS, blocking, HTTP 503, or availability changes.
- Public portal HTML is unstable; layout changes may reduce results.
- PDFs are not parsed by the bot; they appear only as links in `document_urls` or `source_url`.
- Hugging Face is optional. Without `HF_API_KEY`, the system uses deterministic keyword classification.
- City may be absent from the source; in that case `location.city` must be `null`.
- The current conversation does not implement free-text search or dynamic source selection.

## Rollback Criteria

Consider rollback when one of these cases occurs after deployment:

- Render worker does not start or continuously restarts.
- Bot does not respond to `/start` or `/buscar`.
- `validate_scraper_response` rejects real responses that should comply with the formal contract.
- Most searches return `error` with no items because of integration failure, not merely temporary source unavailability.
- A new change alters public contract field names.
- Logs show recurring Telegram token, backend import, or missing-variable errors.

Recommended rollback:

1. Revert to the last approved Render or Git revision.
2. Confirm `TELEGRAM_BOT_TOKEN` and `SCRAPER_BACKEND`.
3. Run the local test suite.
4. Validate a fixture search before re-enabling real sources.

## Tests

Run the suite:

```powershell
python -B -m unittest discover -s tests
```

Direct fixture validation:

```powershell
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -B -c "import asyncio; from telegram_bot.contracts import build_search_request; from telegram_bot.scraper_client import run_scraper; from telegram_bot.messages import render_response; req=build_search_request('BR','PB'); res=asyncio.run(run_scraper(req)); msgs=render_response(res); print(res['status'], res['summary']['total_found'], len(res['items']), 'Resultados' in msgs[0])"
```

Expected result:

```text
success 1 1 True
```

## Infrastructure Documentation

The service should remain a background worker because the bot operates through Telegram polling and does not expose a public HTTP route. Render executes `python -m telegram_bot.bot`, which initializes the `python-telegram-bot` `Application`, registers the `ConversationHandler`, and keeps the process active.

`SCRAPER_BACKEND` decouples the Telegram interface from the data pipeline. In production, use `scraper.pipeline:run_scraper_pipeline`. In local testing, use `telegram_bot.scraper_client:fixture_scraper`.

Sensitive variables such as `TELEGRAM_BOT_TOKEN` and `HF_API_KEY` must be configured in the Render dashboard as secrets. They must not be committed to the repository.

Source network failures should be treated as partial degradation when valid items exist. The formal contract supports this through `status=partial_success`, `summary.partial_failures`, and `warnings`.
