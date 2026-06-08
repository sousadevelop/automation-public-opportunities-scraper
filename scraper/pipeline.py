"""Main Bot-facing scraper pipeline."""

from __future__ import annotations

from datetime import date
from typing import Callable

from schemas.scraper_contract import normalize_request, validate_response_contract
from scraper.hf_classifier import classify_with_hf
from scraper.normalization import (
    ascii_fold,
    classify_match_tags,
    clean_text,
    deadline_date,
    is_closed,
    is_document_url,
    source_name,
    stable_id,
    summarize,
)
from scraper.sources import fetch_source_candidates

CandidateFetcher = Callable[[str], tuple[list[dict], list[str]]]


def run_scraper_pipeline(payload: dict, fetcher: CandidateFetcher | None = None) -> dict:
    """Run the full Scraper -> Bot pipeline for a Bot -> Scraper request dict."""
    warnings: list[str] = []
    try:
        request, request_warnings = normalize_request(payload)
        warnings.extend(request_warnings)
    except ValueError as exc:
        return _response(payload or {}, "error", [], [str(exc)])

    candidates: list[dict] = []
    source_failures = 0
    candidate_fetcher = fetcher or fetch_source_candidates
    for source in request["sources"]:
        source_candidates, source_warnings = candidate_fetcher(source)
        if source_warnings:
            warnings.extend(source_warnings)
        if not source_candidates:
            source_failures += 1
        candidates.extend(source_candidates)

    items = [_normalize_candidate(candidate, request) for candidate in candidates]
    items = [item for item in items if item is not None]
    items = _dedupe_items(items)

    if not request["include_closed"]:
        items = [item for item in items if item["status"] != "closed"]

    items = _sort_items(items, request["sort"])
    total_found = len(items)
    offset = (request["page"] - 1) * request["limit"]
    paged_items = items[offset : offset + request["limit"]]
    public_items = [_public_item(item) for item in paged_items]

    if public_items:
        status = "partial_success" if source_failures else "success"
    elif source_failures == len(request["sources"]):
        status = "error" if warnings else "empty"
    else:
        status = "empty"

    response = _response(request, status, public_items, warnings, total_found, source_failures)
    validate_response_contract(response)
    return response


def _normalize_candidate(candidate: dict, request: dict) -> dict | None:
    title = clean_text(candidate.get("title"))
    candidate_text = clean_text(candidate.get("text"))
    text = title if candidate_text == title else clean_text(f"{title} {candidate_text}")
    tags = classify_match_tags(text, request["keywords"])
    if not tags:
        return None

    source_url = candidate.get("url") or candidate.get("source_page_url")
    if not source_url:
        return None

    deadline = deadline_date(text)
    publication = candidate.get("publication_date")
    doc_urls = _document_urls(source_url, candidate.get("document_url"))
    hf_data = classify_with_hf(text)
    if hf_data:
        dates = hf_data.get("datas_importantes") or {}
        deadline = _coalesce_date(dates.get("fim_inscricao"), deadline)
        doc_urls = _document_urls(*(doc_urls + [hf_data.get("link_oficial")]))
    score = _score(title, tags, candidate.get("source"))
    item_status = _item_status(deadline)

    return {
        "item_id": stable_id(title, source_url),
        "title": title,
        "category": _category(tags, title),
        "subcategory": _subcategory(tags),
        "institution": candidate.get("institution") or source_name(candidate.get("source", "")),
        "source": candidate.get("source"),
        "location": {
            "country": request["country"],
            "state": request["state"],
            "city": candidate.get("city"),
        },
        "published_at": publication,
        "deadline": deadline,
        "status": item_status,
        "match_tags": tags,
        "description_clean": summarize(text),
        "source_url": source_url,
        "document_urls": doc_urls,
        "confidence": _confidence(score, tags, publication, deadline),
        "_score": score,
    }


def _coalesce_date(value: str | None, fallback: str | None) -> str | None:
    if not value:
        return fallback
    from scraper.normalization import first_date

    return first_date(value) or fallback


def _score(title: str, tags: list[str], source: str | None) -> int:
    folded_title = title.lower()
    score = len(tags) * 10
    if "edital" in folded_title or "processo seletivo" in folded_title:
        score += 5
    if source == "ufpb":
        score += 2
    return score


def _category(tags: list[str], title: str) -> str:
    folded_title = title.lower()
    if "perito" in tags or "concurso" in folded_title:
        return "public_exam"
    return "academic_opportunity"


def _subcategory(tags: list[str]) -> str:
    # Priority agreed for Fase 3: perito > doutorado > mestrado > pedagogico.
    for tag in ("perito", "doutorado", "mestrado", "pedagogico"):
        if tag in tags:
            return tag
    return "pedagogico"


def _item_status(deadline: str | None) -> str:
    if not deadline:
        return "unknown"
    return "closed" if is_closed(deadline, date.today()) else "open"


def _document_urls(*urls: str | None) -> list[str]:
    result = []
    for url in urls:
        if url and is_document_url(url) and url not in result:
            result.append(url)
    return result


def _confidence(score: int, tags: list[str], published_at: str | None, deadline: str | None) -> float:
    confidence = 0.5 + min(len(tags), 3) * 0.12
    if score >= 15:
        confidence += 0.1
    if published_at or deadline:
        confidence += 0.08
    return round(min(confidence, 0.98), 2)


def _sort_items(items: list[dict], sort: str) -> list[dict]:
    if sort == "date":
        return sorted(items, key=lambda item: item.get("published_at") or "0000-00-00", reverse=True)
    return sorted(items, key=lambda item: (item.get("_score", 0), item.get("published_at") or ""), reverse=True)


def _dedupe_items(items: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in items:
        key = (ascii_fold(item["title"]), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _public_item(item: dict) -> dict:
    public_item = dict(item)
    public_item.pop("_score", None)
    return public_item


def _response(
    request: dict,
    status: str,
    items: list[dict],
    warnings: list[str],
    total_found: int = 0,
    partial_failures: int = 0,
) -> dict:
    return {
        "request_id": request.get("request_id"),
        "status": status,
        "country": request.get("country", "BR"),
        "state": request.get("state", "PB"),
        "summary": {
            "total_found": total_found,
            "total_returned": len(items),
            "partial_failures": partial_failures,
        },
        "applied_filters": {
            "keywords": list(request.get("keywords", [])),
            "sources": list(request.get("sources", [])),
        },
        "items": items,
        "warnings": warnings,
    }
