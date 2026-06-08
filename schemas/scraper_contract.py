"""Contract helpers for Bot -> Scraper and Scraper -> Bot JSON payloads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

ALLOWED_STATUS = {"success", "empty", "partial_success", "error"}
ALLOWED_MATCH_TAGS = {"mestrado", "doutorado", "pedagogico", "perito"}
ALLOWED_ITEM_STATUS = {"open", "closed", "unknown"}
ALLOWED_CATEGORIES = {"academic_opportunity", "public_exam"}
ALLOWED_SOURCES = {"ufpb", "editais_pb"}
ALLOWED_SORT = {"relevance", "date"}

DEFAULT_REQUEST = {
    "country": "BR",
    "state": "PB",
    "keywords": ["mestrado", "doutorado", "pedagogico", "perito"],
    "sources": ["ufpb", "editais_pb"],
    "language": "pt-BR",
    "limit": 20,
    "page": 1,
    "sort": "relevance",
    "include_closed": False,
}

REQUIRED_RESPONSE_FIELDS = {
    "request_id",
    "status",
    "country",
    "state",
    "summary",
    "items",
    "warnings",
    "applied_filters",
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


def normalize_request(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalize and lightly validate the Bot -> Scraper request."""
    warnings: list[str] = []
    request = deepcopy(DEFAULT_REQUEST)
    request.update(payload or {})

    if not request.get("request_id"):
        raise ValueError("request_id is required")

    request["country"] = str(request.get("country") or "BR").upper()
    request["state"] = str(request.get("state") or "PB").upper()
    request["language"] = str(request.get("language") or "pt-BR")

    keywords = request.get("keywords") or DEFAULT_REQUEST["keywords"]
    normalized_keywords = []
    for keyword in keywords:
        value = str(keyword).strip().lower()
        if value in ALLOWED_MATCH_TAGS and value not in normalized_keywords:
            normalized_keywords.append(value)
    if not normalized_keywords:
        normalized_keywords = list(DEFAULT_REQUEST["keywords"])
        warnings.append("No supported keywords were provided; using default match tags.")
    request["keywords"] = normalized_keywords

    sources = request.get("sources") or DEFAULT_REQUEST["sources"]
    normalized_sources = []
    for source in sources:
        value = str(source).strip().lower()
        if value in ALLOWED_SOURCES and value not in normalized_sources:
            normalized_sources.append(value)
        elif value:
            warnings.append(f"Unsupported source ignored: {value}")
    if not normalized_sources:
        normalized_sources = list(DEFAULT_REQUEST["sources"])
        warnings.append("No supported sources were provided; using default sources.")
    request["sources"] = normalized_sources

    try:
        request["limit"] = max(1, min(int(request.get("limit", 20)), 50))
    except (TypeError, ValueError):
        request["limit"] = 20
        warnings.append("Invalid limit; using 20.")

    try:
        request["page"] = max(1, int(request.get("page", 1)))
    except (TypeError, ValueError):
        request["page"] = 1
        warnings.append("Invalid page; using 1.")

    if request.get("sort") not in ALLOWED_SORT:
        request["sort"] = "relevance"
        warnings.append("Invalid sort; using relevance.")

    request["include_closed"] = bool(request.get("include_closed", False))
    return request, warnings


def validate_response_contract(response: dict[str, Any]) -> None:
    """Raise ValueError when Scraper -> Bot response violates the public contract."""
    missing = REQUIRED_RESPONSE_FIELDS.difference(response)
    if missing:
        raise ValueError(f"Missing response fields: {sorted(missing)}")
    if response["status"] not in ALLOWED_STATUS:
        raise ValueError(f"Invalid status: {response['status']}")
    if not isinstance(response["items"], list):
        raise ValueError("items must be a list")
    if not isinstance(response["warnings"], list):
        raise ValueError("warnings must be a list")
    if not isinstance(response["summary"], dict):
        raise ValueError("summary must be an object")
    if not isinstance(response["applied_filters"], dict):
        raise ValueError("applied_filters must be an object")
    for field in ("keywords", "sources"):
        value = response["applied_filters"].get(field)
        if not isinstance(value, list):
            raise ValueError(f"applied_filters.{field} must be a list")

    missing_summary = REQUIRED_SUMMARY_FIELDS.difference(response["summary"])
    if missing_summary:
        raise ValueError(f"Missing summary fields: {sorted(missing_summary)}")
    for field in REQUIRED_SUMMARY_FIELDS:
        if not isinstance(response["summary"][field], int) or response["summary"][field] < 0:
            raise ValueError(f"summary.{field} must be a non-negative integer")

    for index, item in enumerate(response["items"]):
        missing_item = REQUIRED_ITEM_FIELDS.difference(item)
        if missing_item:
            raise ValueError(f"items[{index}] missing fields: {sorted(missing_item)}")
        if item["category"] not in ALLOWED_CATEGORIES:
            raise ValueError(f"items[{index}].category is invalid")
        if item["status"] not in ALLOWED_ITEM_STATUS:
            raise ValueError(f"items[{index}].status is invalid")
        if not item.get("source_url"):
            raise ValueError(f"items[{index}].source_url is required")
        if not isinstance(item["document_urls"], list):
            raise ValueError(f"items[{index}].document_urls must be a list")
        if not isinstance(item["location"], dict):
            raise ValueError(f"items[{index}].location must be an object")
        for location_field in ("country", "state", "city"):
            if location_field not in item["location"]:
                raise ValueError(f"items[{index}].location.{location_field} is required")
        confidence = item["confidence"]
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            raise ValueError(f"items[{index}].confidence must be between 0 and 1")
        tags = item.get("match_tags")
        if not isinstance(tags, list):
            raise ValueError(f"items[{index}].match_tags must be a list")
        invalid_tags = set(tags).difference(ALLOWED_MATCH_TAGS)
        if invalid_tags:
            raise ValueError(f"items[{index}] has invalid match_tags: {sorted(invalid_tags)}")
        for field in ("published_at", "deadline"):
            value = item.get(field)
            if value is not None and not _is_iso_date(value):
                raise ValueError(f"items[{index}].{field} must be YYYY-MM-DD or null")


def _is_iso_date(value: str) -> bool:
    if len(value) != 10:
        return False
    year, month, day = value.split("-") if value.count("-") == 2 else ("", "", "")
    return year.isdigit() and month.isdigit() and day.isdigit()
