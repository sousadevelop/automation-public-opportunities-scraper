"""Contract helpers shared by the Telegram bot and scraper integration."""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from uuid import uuid4


ALLOWED_STATUSES = {"success", "empty", "partial_success", "error"}
ALLOWED_MATCH_TAGS = {"mestrado", "doutorado", "pedagogico", "perito"}
DEFAULT_KEYWORDS = ["mestrado", "doutorado", "pedagogico", "perito"]
DEFAULT_SOURCES = ["ufpb", "editais_pb"]
REQUIRED_TOP_LEVEL_FIELDS = {
    "request_id",
    "status",
    "country",
    "state",
    "applied_filters",
    "summary",
    "items",
    "warnings",
}
REQUIRED_SUMMARY_FIELDS = {"total_found", "total_returned", "partial_failures"}
REQUIRED_ITEM_FIELDS = {
    "item_id",
    "title",
    "category",
    "subcategory",
    "institution",
    "source",
    "location",
    "published_at",
    "deadline",
    "status",
    "match_tags",
    "description_clean",
    "source_url",
    "document_urls",
    "confidence",
}
REQUIRED_LOCATION_FIELDS = {"country", "state", "city"}

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

STATE_ALIASES = {
    "AC": "AC",
    "AL": "AL",
    "AM": "AM",
    "AP": "AP",
    "BA": "BA",
    "CE": "CE",
    "DF": "DF",
    "ES": "ES",
    "GO": "GO",
    "MA": "MA",
    "MG": "MG",
    "MS": "MS",
    "MT": "MT",
    "PA": "PA",
    "PB": "PB",
    "PE": "PE",
    "PI": "PI",
    "PR": "PR",
    "RJ": "RJ",
    "RN": "RN",
    "RO": "RO",
    "RR": "RR",
    "RS": "RS",
    "SC": "SC",
    "SE": "SE",
    "SP": "SP",
    "TO": "TO",
    "PARAIBA": "PB",
    "PARAIBA PB": "PB",
    "PARAIBA-PB": "PB",
}


class ContractError(ValueError):
    """Raised when scraper input or output violates the agreed JSON contract."""


def normalize_country(value: str) -> str:
    normalized = _normalize_text(value)
    if normalized in {"BR", "BRASIL", "BRAZIL"}:
        return "BR"
    raise ContractError("Pais nao suportado. Use BR.")


def normalize_state(value: str) -> str:
    normalized = _normalize_text(value)
    state = STATE_ALIASES.get(normalized)
    if state:
        return state
    raise ContractError("Estado invalido. Use a sigla, por exemplo PB.")


def build_search_request(country: str, state: str) -> dict[str, Any]:
    return {
        "request_id": str(uuid4()),
        "country": normalize_country(country),
        "state": normalize_state(state),
        "keywords": list(DEFAULT_KEYWORDS),
        "sources": list(DEFAULT_SOURCES),
        "language": "pt-BR",
        "limit": 20,
        "page": 1,
        "sort": "relevance",
        "include_closed": False,
    }


def validate_scraper_response(
    payload: dict[str, Any],
    *,
    expected_request_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractError("Resposta do scraper deve ser um objeto JSON.")

    missing = REQUIRED_TOP_LEVEL_FIELDS - set(payload)
    if missing:
        raise ContractError(f"Resposta do scraper sem campos obrigatorios: {sorted(missing)}")

    if expected_request_id and payload["request_id"] != expected_request_id:
        raise ContractError("Resposta do scraper com request_id diferente da busca.")

    for field in ("request_id", "country", "state"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ContractError(f"{field} deve ser texto nao vazio.")

    if payload["status"] not in ALLOWED_STATUSES:
        raise ContractError("Status do scraper nao permitido.")

    if not isinstance(payload["applied_filters"], dict):
        raise ContractError("applied_filters deve ser um objeto JSON.")

    if not isinstance(payload["summary"], dict):
        raise ContractError("summary deve ser um objeto JSON.")
    _validate_summary(payload["summary"])

    if not isinstance(payload["items"], list):
        raise ContractError("items deve ser uma lista.")

    if not isinstance(payload["warnings"], list):
        raise ContractError("warnings deve ser uma lista.")

    for warning in payload["warnings"]:
        if not isinstance(warning, str):
            raise ContractError("warnings deve conter apenas textos.")

    for index, item in enumerate(payload["items"], start=1):
        _validate_item(item, index)

    return payload


def _validate_summary(summary: dict[str, Any]) -> None:
    missing = REQUIRED_SUMMARY_FIELDS - set(summary)
    if missing:
        raise ContractError(f"summary sem campos obrigatorios: {sorted(missing)}")

    for field in REQUIRED_SUMMARY_FIELDS:
        value = summary[field]
        if not isinstance(value, int) or value < 0:
            raise ContractError(f"summary.{field} deve ser inteiro maior ou igual a zero.")


def _validate_item(item: Any, index: int) -> None:
    if not isinstance(item, dict):
        raise ContractError(f"Item {index} deve ser um objeto JSON.")

    missing = REQUIRED_ITEM_FIELDS - set(item)
    if missing:
        raise ContractError(f"Item {index} sem campos obrigatorios: {sorted(missing)}")

    source_url = item.get("source_url")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ContractError(f"Item {index} sem source_url obrigatorio.")

    location = item["location"]
    if not isinstance(location, dict):
        raise ContractError(f"Item {index}.location deve ser um objeto JSON.")
    missing_location = REQUIRED_LOCATION_FIELDS - set(location)
    if missing_location:
        raise ContractError(f"Item {index}.location sem campos obrigatorios: {sorted(missing_location)}")

    match_tags = item["match_tags"]
    if not isinstance(match_tags, list) or any(tag not in ALLOWED_MATCH_TAGS for tag in match_tags):
        raise ContractError(f"Item {index} tem match_tags fora do contrato.")

    document_urls = item["document_urls"]
    if not isinstance(document_urls, list) or any(not isinstance(url, str) for url in document_urls):
        raise ContractError(f"Item {index}.document_urls deve ser uma lista de textos.")

    confidence = item["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ContractError(f"Item {index}.confidence deve ser numerico.")
    if confidence < 0 or confidence > 1:
        raise ContractError(f"Item {index}.confidence deve estar entre 0 e 1.")

    for key in ("published_at", "deadline"):
        _validate_nullable_date(item[key], index, key)

    for key in (
        "item_id",
        "title",
        "category",
        "subcategory",
        "institution",
        "source",
        "status",
        "description_clean",
    ):
        _validate_required_text(item[key], index, key)

    for key in ("country", "state"):
        _validate_required_text(location[key], index, f"location.{key}")

    city = location["city"]
    if city is not None:
        _validate_required_text(city, index, "location.city")


def _validate_nullable_date(value: Any, item_index: int, key: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        raise ContractError(f"Item {item_index} tem data invalida em {key}; use YYYY-MM-DD.")


def _validate_required_text(value: Any, item_index: int, key: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"Item {item_index}.{key} deve ser texto nao vazio.")


def _normalize_text(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return " ".join(without_accents.upper().strip().split())
