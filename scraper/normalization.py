"""Normalization and deterministic classification for public opportunity items."""

from __future__ import annotations

from datetime import date
import hashlib
import re
import unicodedata
from urllib.parse import urlparse

MATCH_TAG_PATTERNS = {
    "mestrado": ("mestrado", "stricto sensu", "pos-graduacao", "pos graduacao"),
    "doutorado": ("doutorado",),
    "pedagogico": (
        "pedagogico",
        "pedagogica",
        "educacao",
        "docente",
        "professor",
        "formador",
        "alfabetiza",
        "ensino",
    ),
    "perito": ("perito", "pericia", "pericial", "papiloscopista", "medico-legal", "tecnico em pericia"),
}

PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def clean_text(value: str | None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text.replace("\u00a0", " ")


def ascii_fold(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def classify_match_tags(text: str, allowed_keywords: list[str]) -> list[str]:
    folded = ascii_fold(text)
    tags = []
    for tag, patterns in MATCH_TAG_PATTERNS.items():
        if tag not in allowed_keywords:
            continue
        if any(pattern in folded for pattern in patterns):
            tags.append(tag)
    return tags


def extract_dates(text: str) -> list[str]:
    found: list[str] = []
    for day, month, year in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text or ""):
        iso = _to_iso_date(day, month, year)
        if iso and iso not in found:
            found.append(iso)

    for year, month, day in re.findall(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text or ""):
        iso = _to_iso_date(day, month, year)
        if iso and iso not in found:
            found.append(iso)

    month_pattern = "|".join(PT_MONTHS)
    long_dates = re.findall(rf"\b(\d{{1,2}})\s+de\s+({month_pattern})\s+de\s+(20\d{{2}})\b", text or "", re.I)
    for day, month_name, year in long_dates:
        iso = _to_iso_date(day, str(PT_MONTHS[month_name.lower()]), year)
        if iso and iso not in found:
            found.append(iso)
    return found


def first_date(text: str) -> str | None:
    dates = extract_dates(text)
    return dates[0] if dates else None


def deadline_date(text: str) -> str | None:
    dates = extract_dates(text)
    return dates[-1] if dates else None


def is_closed(deadline: str | None, today: date | None = None) -> bool:
    if not deadline:
        return False
    current = today or date.today()
    try:
        year, month, day = [int(part) for part in deadline.split("-")]
        return date(year, month, day) < current
    except ValueError:
        return False


def stable_id(*parts: str | None) -> str:
    raw = "|".join(clean_text(part) for part in parts if part)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def source_name(source_key: str) -> str:
    names = {
        "ufpb": "Universidade Federal da Paraíba",
        "editais_pb": "Governo do Estado da Paraíba",
    }
    return names.get(source_key, source_key)


def is_document_url(url: str | None) -> bool:
    path = urlparse(url or "").path.lower()
    return path.endswith((".pdf", ".doc", ".docx", ".odt"))


def summarize(text: str, max_len: int = 260) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _to_iso_date(day: str, month: str, year: str) -> str | None:
    try:
        year_int = int(year)
        if year_int < 100:
            year_int += 2000
        value = date(year_int, int(month), int(day))
        return value.isoformat()
    except ValueError:
        return None

