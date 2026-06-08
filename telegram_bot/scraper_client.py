"""Clean integration point between Telegram bot and the scraper pipeline."""

from __future__ import annotations

import inspect
import os
from importlib import import_module
from typing import Any, Awaitable, Callable

from .contracts import validate_scraper_response


ScraperFunction = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


async def run_scraper(search_request: dict[str, Any]) -> dict[str, Any]:
    scraper = load_scraper_function()
    result = scraper(search_request)
    if inspect.isawaitable(result):
        result = await result
    return validate_scraper_response(result, expected_request_id=search_request["request_id"])


def load_scraper_function() -> ScraperFunction:
    target = os.environ.get("SCRAPER_BACKEND", "scraper.pipeline:run_scraper_pipeline")
    module_name, separator, function_name = target.partition(":")
    if not separator or not module_name or not function_name:
        raise RuntimeError("SCRAPER_BACKEND deve usar o formato modulo:funcao.")

    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        if target == "scraper.pipeline:run_scraper_pipeline":
            return fixture_scraper
        raise
    scraper = getattr(module, function_name)
    if not callable(scraper):
        raise RuntimeError("SCRAPER_BACKEND nao aponta para uma funcao chamavel.")
    return scraper


def fixture_scraper(search_request: dict[str, Any]) -> dict[str, Any]:
    """Temporary fixture for local tests until the real scraper function exists."""

    return {
        "request_id": search_request["request_id"],
        "status": "success",
        "country": search_request["country"],
        "state": search_request["state"],
        "applied_filters": {
            "keywords": search_request["keywords"],
            "sources": search_request["sources"],
            "limit": search_request["limit"],
            "page": search_request["page"],
            "sort": search_request["sort"],
            "include_closed": search_request["include_closed"],
        },
        "summary": {
            "total_found": 1,
            "total_returned": 1,
            "partial_failures": 0,
        },
        "items": [
            {
                "item_id": "fixture-ufpb-001",
                "title": "Edital de selecao - programa de pos-graduacao",
                "category": "pos-graduacao",
                "subcategory": "processo-seletivo",
                "institution": "UFPB",
                "source": "ufpb",
                "location": {
                    "country": search_request["country"],
                    "state": search_request["state"],
                    "city": "Joao Pessoa",
                },
                "published_at": "2026-06-01",
                "deadline": "2026-07-15",
                "status": "open",
                "match_tags": ["mestrado", "doutorado"],
                "description_clean": "Processo seletivo com vagas de mestrado e doutorado.",
                "source_url": "https://example.invalid/edital.pdf",
                "document_urls": ["https://example.invalid/edital.pdf"],
                "confidence": 0.92,
            }
        ],
        "warnings": ["Fixture local: substituir SCRAPER_BACKEND pela pipeline real."],
    }
