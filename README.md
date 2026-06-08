# Web Scraper de Oportunidades Publicas

Bot Telegram para consultar oportunidades publicas e academicas a partir de fontes iniciais da Paraiba. O usuario informa pais e estado; o bot monta uma requisicao JSON formal, chama a pipeline de scraper configurada e devolve resultados normalizados no Telegram.

O projeto foi organizado para manter a interface do Telegram separada da coleta e normalizacao dos dados. O bot nao processa HTML, PDF ou texto cru: ele valida e renderiza apenas o JSON normalizado retornado pelo scraper.

## Visao Geral

O fluxo atual cobre:

- Consulta por pais e estado via Telegram.
- Fontes iniciais: UFPB e editais do Governo da Paraiba.
- Filtros padrao: `mestrado`, `doutorado`, `pedagogico`, `perito`.
- Respostas para `success`, `empty`, `partial_success` e `error`.
- Deploy no Render como background worker.
- Enriquecimento opcional via Hugging Face quando `HF_API_KEY` estiver configurada.

## Arquitetura Modular

- `telegram_bot/bot.py`: entrada do bot Telegram com `ConversationHandler`.
- `telegram_bot/contracts.py`: montagem do contrato Bot -> Scraper e validacao formal do contrato Scraper -> Bot.
- `telegram_bot/scraper_client.py`: ponto de integracao configuravel por `SCRAPER_BACKEND`.
- `telegram_bot/messages.py`: renderizacao das mensagens para o Telegram.
- `scraper/pipeline.py`: pipeline que coleta candidatos, normaliza, filtra, ordena e retorna JSON formal.
- `scraper/sources.py`: fontes iniciais e parsers de listagens HTML.
- `scraper/hf_classifier.py`: classificacao opcional via Hugging Face.
- `schemas/scraper_contract.py`: contrato da pipeline do scraper.
- `render.yaml`: configuracao de deploy como worker no Render.
- `tests/`: testes de contrato, pipeline, fixture e renderizacao.

## Fluxo Telegram

1. Usuario envia `/start` ou `/buscar`.
2. Bot pergunta o pais.
3. Usuario envia `BR`.
4. Bot pergunta o estado.
5. Usuario envia uma sigla, por exemplo `PB`.
6. Bot monta o JSON Bot -> Scraper.
7. Bot chama a funcao indicada por `SCRAPER_BACKEND`.
8. Scraper retorna JSON normalizado.
9. Bot valida o contrato formal.
10. Bot renderiza a resposta no Telegram.

Estados do `ConversationHandler`:

- `ESPERANDO_PAIS`: aceita `BR`, `Brasil` ou `Brazil`.
- `ESPERANDO_ESTADO`: aceita siglas de UF, incluindo `PB`.

Durante a chamada ao scraper, o bot envia status `typing...`.

## Contrato Bot -> Scraper

Exemplo de payload enviado pelo bot:

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

Campos:

- `request_id`: UUID da busca.
- `country`: pais da busca. Implementado: `BR`.
- `state`: UF da busca. Exemplo: `PB`.
- `keywords`: tags aceitas para filtro.
- `sources`: fontes habilitadas. Implementado: `ufpb`, `editais_pb`.
- `language`: idioma de resposta/normalizacao. Padrao: `pt-BR`.
- `limit`: quantidade maxima por pagina.
- `page`: pagina solicitada.
- `sort`: `relevance` ou `date`.
- `include_closed`: inclui oportunidades fechadas quando `true`.

## Contrato Scraper -> Bot

Campos top-level obrigatorios:

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

`status` permitido:

- `success`
- `empty`
- `partial_success`
- `error`

`summary` obrigatorio:

- `total_found`: total encontrado apos filtros.
- `total_returned`: total retornado na pagina atual.
- `partial_failures`: quantidade de fontes com falha parcial.

`warnings` deve ser uma lista de textos. Timeouts, HTTP 503 e fontes indisponiveis podem aparecer aqui sem quebrar a entrega quando houver resultados validos.

### Item Normalizado

Cada item deve ter todos os campos abaixo:

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

Regras do item:

- `source_url` e obrigatorio.
- `document_urls` e uma lista de URLs de documentos, podendo ser vazia.
- `match_tags` aceita apenas `mestrado`, `doutorado`, `pedagogico`, `perito`.
- `published_at` e `deadline` devem usar `YYYY-MM-DD` ou `null`.
- `location.country` e `location.state` sao textos obrigatorios.
- `location.city` deve existir, mas pode ser texto nao vazio ou `null`.
- `confidence` deve estar entre `0` e `1`.
- `status` do item pode ser `open`, `closed` ou `unknown`.

## Como Executar Localmente

Requisitos:

- Python 3.13 ou versao compativel.
- Token de bot criado no Telegram.

Instalacao:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Execucao com scraper real:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="scraper.pipeline:run_scraper_pipeline"
$env:LOG_LEVEL="INFO"
python -m telegram_bot.bot
```

Execucao com fixture local:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -m telegram_bot.bot
```

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Sim | Token do bot Telegram. |
| `SCRAPER_BACKEND` | Nao | Funcao no formato `modulo:funcao`. Padrao: `scraper.pipeline:run_scraper_pipeline`. |
| `LOG_LEVEL` | Nao | Nivel de log. Padrao: `INFO`. |
| `HF_API_KEY` | Nao | Chave para enriquecimento opcional via Hugging Face. |
| `HF_ENDPOINT` | Nao | Endpoint alternativo de inferencia Hugging Face. |

## Deploy no Render

O deploy usa `render.yaml` como background worker, nao como web service:

```yaml
services:
  - type: worker
    name: oportunidades-publicas-telegram-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m telegram_bot.bot
```

Passos:

1. Crie um novo Blueprint no Render apontando para o repositorio.
2. Confirme que o servico gerado e do tipo `worker`.
3. Configure `TELEGRAM_BOT_TOKEN` como secret.
4. Mantenha `SCRAPER_BACKEND=scraper.pipeline:run_scraper_pipeline`.
5. Configure `HF_API_KEY` e `HF_ENDPOINT` apenas se for usar enriquecimento por Hugging Face.
6. Faça o deploy.
7. Verifique logs do worker e envie `/buscar` para o bot.

## Fontes Iniciais

Fonte `ufpb`:

- SIGAA UFPB - processos seletivos.
- PRPG UFPB - processos seletivos abertos.
- Portal de oportunidades da UFPB.

Fonte `editais_pb`:

- Editais do Governo da Paraiba.
- Central de Compras PB.
- CODATA PB - editais e concursos.

As fontes podem retornar timeout, 503 ou HTML diferente do esperado. Nesses casos, o scraper registra `warnings` e tenta continuar com as demais fontes.

## Limitacoes Conhecidas

- Rede externa pode falhar por timeout, DNS, bloqueio, HTTP 503 ou mudanca de disponibilidade.
- HTML de portais publicos e instavel; mudancas de layout podem reduzir resultados.
- PDFs nao sao parseados pelo bot; aparecem apenas como links em `document_urls` ou `source_url`.
- Hugging Face e opcional. Sem `HF_API_KEY`, o sistema usa classificacao deterministica por palavras-chave.
- A cidade pode nao existir na fonte; nesse caso `location.city` deve vir como `null`.
- O bot nao implementa busca livre por texto nem selecao dinamica de fontes na conversa atual.

## Criterios de Rollback

Considere rollback quando ocorrer um destes casos apos deploy:

- Worker do Render nao inicia ou reinicia continuamente.
- Bot nao responde a `/start` ou `/buscar`.
- `validate_scraper_response` rejeita respostas reais que deveriam seguir o contrato formal.
- A maioria das buscas retorna `error` sem itens por falha de integracao, nao apenas por indisponibilidade temporaria de fonte.
- Mudanca nova altera nomes de campos do contrato publico.
- Logs indicam erro recorrente de token Telegram, importacao de backend ou variaveis ausentes.

Rollback recomendado:

1. Reverter para a ultima revisao aprovada no Render ou no Git.
2. Confirmar `TELEGRAM_BOT_TOKEN` e `SCRAPER_BACKEND`.
3. Rodar a suite local.
4. Validar uma busca com fixture antes de reativar fontes reais.

## Testes

Rodar a suite:

```powershell
python -B -m unittest discover -s tests
```

Validacao direta da fixture:

```powershell
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -B -c "import asyncio; from telegram_bot.contracts import build_search_request; from telegram_bot.scraper_client import run_scraper; from telegram_bot.messages import render_response; req=build_search_request('BR','PB'); res=asyncio.run(run_scraper(req)); msgs=render_response(res); print(res['status'], res['summary']['total_found'], len(res['items']), 'Resultados' in msgs[0])"
```

Resultado esperado:

```text
success 1 1 True
```

## Documentacao de Infraestrutura

O servico deve permanecer como background worker porque o bot opera por polling do Telegram e nao expoe rota HTTP publica. O Render executa `python -m telegram_bot.bot`, que inicializa o `Application` do `python-telegram-bot`, registra o `ConversationHandler` e mantem o processo ativo.

O `SCRAPER_BACKEND` desacopla a interface do Telegram da pipeline de dados. Em producao, use `scraper.pipeline:run_scraper_pipeline`. Em teste local, use `telegram_bot.scraper_client:fixture_scraper`.

Variaveis sensiveis, como `TELEGRAM_BOT_TOKEN` e `HF_API_KEY`, devem ser configuradas no painel do Render como secrets. Elas nao devem ser commitadas no repositorio.

Falhas de rede das fontes devem ser tratadas como degradacao parcial quando houver itens validos. O contrato formal permite isso por meio de `status=partial_success`, `summary.partial_failures` e `warnings`.
