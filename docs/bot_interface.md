# Interface do Bot Telegram

Documento parcial da Fase 1 para o bot. O README consolidado fica para a Fase 3.

## Fluxo

1. `/start` ou `/buscar`
2. Bot solicita o pais.
3. Usuario envia `BR`.
4. Bot solicita o estado.
5. Usuario envia a sigla, por exemplo `PB`.
6. Bot monta o JSON Bot -> Scraper e chama a funcao configurada em `SCRAPER_BACKEND`.

## Integracao

`SCRAPER_BACKEND` deve apontar para `modulo:funcao`.

A funcao recebe o contrato Bot -> Scraper e retorna o contrato Scraper -> Bot. O bot valida:

- top-level: `request_id`, `status`, `country`, `state`, `applied_filters`, `summary`, `items`, `warnings`
- `summary`: `total_found`, `total_returned`, `partial_failures`
- item: `item_id`, `title`, `category`, `subcategory`, `institution`, `source`, `location`, `published_at`, `deadline`, `status`, `match_tags`, `description_clean`, `source_url`, `document_urls`, `confidence`
- `location`: `country`, `state`, `city`
- `status` em `success`, `empty`, `partial_success`, `error`
- `source_url` obrigatorio por item
- datas em `YYYY-MM-DD` ou `null`
- `match_tags` apenas em `mestrado`, `doutorado`, `pedagogico`, `perito`

No deploy, `SCRAPER_BACKEND` aponta para `scraper.pipeline:run_scraper_pipeline`.

Para testes locais sem pipeline real, use `telegram_bot.scraper_client:fixture_scraper`.
