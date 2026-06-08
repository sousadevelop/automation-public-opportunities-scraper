# Scraper Web d'Opportunites Publiques

Bot Telegram permettant de consulter des opportunites publiques et academiques a partir de sources initiales en Paraiba, au Bresil. L'utilisateur fournit un pays et un etat; le bot construit une requete JSON formelle, appelle la pipeline de scraper configuree, puis renvoie des resultats normalises dans Telegram.

Le projet est organise afin de separer l'interface Telegram de la collecte et de la normalisation des donnees. Le bot ne traite pas de HTML, de PDF ni de texte brut: il valide et affiche uniquement le JSON normalise retourne par le scraper.

## Vue d'Ensemble

Le flux actuel couvre:

- Consultation par pays et etat via Telegram.
- Sources initiales: UFPB et avis publics de l'Etat de Paraiba.
- Filtres par defaut: `mestrado`, `doutorado`, `pedagogico`, `perito`.
- Reponses pour `success`, `empty`, `partial_success` et `error`.
- Deploiement Render comme worker en arriere-plan.
- Enrichissement optionnel via Hugging Face lorsque `HF_API_KEY` est configuree.

## Architecture Modulaire

- `telegram_bot/bot.py`: point d'entree du bot Telegram avec `ConversationHandler`.
- `telegram_bot/contracts.py`: creation du contrat Bot -> Scraper et validation formelle du contrat Scraper -> Bot.
- `telegram_bot/scraper_client.py`: point d'integration configurable par `SCRAPER_BACKEND`.
- `telegram_bot/messages.py`: rendu des messages Telegram.
- `scraper/pipeline.py`: pipeline qui collecte les candidats, normalise, filtre, trie et retourne le JSON formel.
- `scraper/sources.py`: sources initiales et parseurs de listes HTML.
- `scraper/hf_classifier.py`: classification optionnelle via Hugging Face.
- `schemas/scraper_contract.py`: contrat de la pipeline scraper.
- `render.yaml`: configuration du deploiement Render comme worker.
- `tests/`: tests de contrat, pipeline, fixture et rendu.

## Flux Telegram

1. L'utilisateur envoie `/start` ou `/buscar`.
2. Le bot demande le pays.
3. L'utilisateur envoie `BR`.
4. Le bot demande l'etat.
5. L'utilisateur envoie une abreviation d'etat, par exemple `PB`.
6. Le bot construit le JSON Bot -> Scraper.
7. Le bot appelle la fonction indiquee par `SCRAPER_BACKEND`.
8. Le scraper retourne un JSON normalise.
9. Le bot valide le contrat formel.
10. Le bot affiche la reponse dans Telegram.

Etats du `ConversationHandler`:

- `ESPERANDO_PAIS`: accepte `BR`, `Brasil` ou `Brazil`.
- `ESPERANDO_ESTADO`: accepte les abreviations d'etats bresiliens, dont `PB`.

Pendant l'appel au scraper, le bot envoie l'etat `typing...`.

## Contrat Bot -> Scraper

Exemple de payload envoye par le bot:

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

Champs:

- `request_id`: UUID de la recherche.
- `country`: pays de recherche. Implemente: `BR`.
- `state`: etat de recherche. Exemple: `PB`.
- `keywords`: balises acceptees pour le filtrage.
- `sources`: sources activees. Implemente: `ufpb`, `editais_pb`.
- `language`: langue de reponse/normalisation. Valeur par defaut: `pt-BR`.
- `limit`: nombre maximal d'elements par page.
- `page`: page demandee.
- `sort`: `relevance` ou `date`.
- `include_closed`: inclut les opportunites fermees lorsque `true`.

## Contrat Scraper -> Bot

Champs top-level obligatoires:

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

Valeurs autorisees pour `status`:

- `success`
- `empty`
- `partial_success`
- `error`

Champs obligatoires de `summary`:

- `total_found`: total trouve apres filtrage.
- `total_returned`: total retourne dans la page courante.
- `partial_failures`: nombre de sources en echec partiel.

`warnings` doit etre une liste de textes. Les timeouts, HTTP 503 et sources indisponibles peuvent apparaitre ici sans interrompre la livraison lorsqu'il existe des resultats valides.

### Element Normalise

Chaque element doit contenir tous les champs ci-dessous:

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

Regles de l'element:

- `source_url` est obligatoire.
- `document_urls` est une liste d'URLs de documents et peut etre vide.
- `match_tags` accepte uniquement `mestrado`, `doutorado`, `pedagogico`, `perito`.
- `published_at` et `deadline` doivent utiliser `YYYY-MM-DD` ou `null`.
- `location.country` et `location.state` sont des textes obligatoires.
- `location.city` doit exister, mais peut etre un texte non vide ou `null`.
- `confidence` doit etre comprise entre `0` et `1`.
- Le `status` d'un element peut etre `open`, `closed` ou `unknown`.

## Execution Locale

Prérequis:

- Python 3.13 ou version compatible.
- Token de bot Telegram.

Installation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Execution avec le scraper reel:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="scraper.pipeline:run_scraper_pipeline"
$env:LOG_LEVEL="INFO"
python -m telegram_bot.bot
```

Execution avec la fixture locale:

```powershell
$env:TELEGRAM_BOT_TOKEN="seu-token"
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -m telegram_bot.bot
```

## Variables d'Environnement

| Variable | Obligatoire | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Oui | Token du bot Telegram. |
| `SCRAPER_BACKEND` | Non | Fonction au format `modulo:funcao`. Valeur par defaut: `scraper.pipeline:run_scraper_pipeline`. |
| `LOG_LEVEL` | Non | Niveau de journalisation. Valeur par defaut: `INFO`. |
| `HF_API_KEY` | Non | Cle pour l'enrichissement optionnel via Hugging Face. |
| `HF_ENDPOINT` | Non | Endpoint alternatif d'inference Hugging Face. |

## Deploiement Render

Le deploiement utilise `render.yaml` comme worker en arriere-plan, et non comme service web:

```yaml
services:
  - type: worker
    name: oportunidades-publicas-telegram-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m telegram_bot.bot
```

Etapes:

1. Creer un nouveau Blueprint Render pointant vers le depot.
2. Confirmer que le service genere est de type `worker`.
3. Configurer `TELEGRAM_BOT_TOKEN` comme secret.
4. Conserver `SCRAPER_BACKEND=scraper.pipeline:run_scraper_pipeline`.
5. Configurer `HF_API_KEY` et `HF_ENDPOINT` uniquement si l'enrichissement Hugging Face est necessaire.
6. Deployer.
7. Verifier les logs du worker et envoyer `/buscar` au bot.

## Sources Initiales

Source `ufpb`:

- Processus selectifs SIGAA UFPB.
- Processus selectifs ouverts PRPG UFPB.
- Portail d'opportunites de l'UFPB.

Source `editais_pb`:

- Avis publics de l'Etat de Paraiba.
- Central de Compras PB.
- CODATA PB - avis et concours publics.

Les sources peuvent retourner timeout, 503 ou HTML different de l'attendu. Dans ces cas, le scraper enregistre des `warnings` et tente de continuer avec les autres sources.

## Limitations Connues

- L'acces reseau externe peut echouer a cause d'un timeout, DNS, blocage, HTTP 503 ou changement de disponibilite.
- Le HTML des portails publics est instable; les changements de mise en page peuvent reduire les resultats.
- Les PDF ne sont pas analyses par le bot; ils apparaissent uniquement comme liens dans `document_urls` ou `source_url`.
- Hugging Face est optionnel. Sans `HF_API_KEY`, le systeme utilise une classification deterministe par mots-cles.
- La ville peut etre absente de la source; dans ce cas `location.city` doit etre `null`.
- La conversation actuelle n'implemente pas de recherche libre par texte ni de selection dynamique de sources.

## Criteres de Rollback

Envisager un rollback lorsqu'un de ces cas survient apres deploiement:

- Le worker Render ne demarre pas ou redemarre en continu.
- Le bot ne repond pas a `/start` ou `/buscar`.
- `validate_scraper_response` rejette des reponses reelles qui devraient respecter le contrat formel.
- La majorite des recherches retourne `error` sans elements a cause d'un echec d'integration, et non d'une indisponibilite temporaire de source.
- Un changement nouveau modifie les noms de champs du contrat public.
- Les logs indiquent des erreurs recurrentes de token Telegram, d'importation backend ou de variables manquantes.

Rollback recommande:

1. Revenir a la derniere revision Render ou Git approuvee.
2. Confirmer `TELEGRAM_BOT_TOKEN` et `SCRAPER_BACKEND`.
3. Executer la suite de tests locale.
4. Valider une recherche avec fixture avant de reactiver les sources reelles.

## Tests

Executer la suite:

```powershell
python -B -m unittest discover -s tests
```

Validation directe de la fixture:

```powershell
$env:SCRAPER_BACKEND="telegram_bot.scraper_client:fixture_scraper"
python -B -c "import asyncio; from telegram_bot.contracts import build_search_request; from telegram_bot.scraper_client import run_scraper; from telegram_bot.messages import render_response; req=build_search_request('BR','PB'); res=asyncio.run(run_scraper(req)); msgs=render_response(res); print(res['status'], res['summary']['total_found'], len(res['items']), 'Resultados' in msgs[0])"
```

Resultat attendu:

```text
success 1 1 True
```

## Documentation d'Infrastructure

Le service doit rester un worker en arriere-plan parce que le bot fonctionne par polling Telegram et n'expose pas de route HTTP publique. Render execute `python -m telegram_bot.bot`, qui initialise l'`Application` de `python-telegram-bot`, enregistre le `ConversationHandler` et maintient le processus actif.

`SCRAPER_BACKEND` decouple l'interface Telegram de la pipeline de donnees. En production, utiliser `scraper.pipeline:run_scraper_pipeline`. En test local, utiliser `telegram_bot.scraper_client:fixture_scraper`.

Les variables sensibles, comme `TELEGRAM_BOT_TOKEN` et `HF_API_KEY`, doivent etre configurees dans le tableau de bord Render comme secrets. Elles ne doivent pas etre commitees dans le depot.

Les echecs reseau des sources doivent etre traites comme une degradation partielle lorsqu'il existe des elements valides. Le contrat formel le permet via `status=partial_success`, `summary.partial_failures` et `warnings`.
