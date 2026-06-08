"""HTML source fetchers and parsers for public opportunity portals."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin

import requests

from scraper.normalization import clean_text, first_date

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - exercised indirectly in environments without bs4
    BeautifulSoup = None


@dataclass(frozen=True)
class SourceConfig:
    key: str
    institution: str
    urls: tuple[str, ...]


SOURCE_REGISTRY = {
    "ufpb": SourceConfig(
        key="ufpb",
        institution="Universidade Federal da Paraíba",
        urls=(
            "https://sigaa.ufpb.br/sigaa/public/programa/processo_seletivo.jsf?id=1879&lc=pt_BR",
            "https://plone.ufpb.br/prpg/contents/noticias/processos-seletivos-abertos",
            "https://www.ufpb.br/oportunidades/",
        ),
    ),
    "editais_pb": SourceConfig(
        key="editais_pb",
        institution="Governo do Estado da Paraíba",
        urls=(
            "https://paraiba.pb.gov.br/diretas/secretaria-de-desenvolvimento-humano/conteudo-de-links/editais1-1",
            "https://centraldecompras.pb.gov.br/appls/sgc/edital.nsf/Web?OpenAgent=&pag=",
            "https://codata.pb.gov.br/institucional/editais-concursos",
        ),
    ),
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 public-opportunity-scraper/1.0 (+https://example.invalid)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_source_candidates(source_key: str, timeout: int = 15) -> tuple[list[dict], list[str]]:
    config = SOURCE_REGISTRY[source_key]
    candidates: list[dict] = []
    warnings: list[str] = []

    for url in config.urls:
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower():
                warnings.append(f"Skipped PDF source listing: {url}")
                continue
            candidates.extend(parse_html_candidates(response.text, url, config.key, config.institution))
        except requests.RequestException as exc:
            warnings.append(f"Failed to fetch {source_key} source {url}: {exc}")

    return candidates, warnings


def parse_html_candidates(html: str, base_url: str, source_key: str, institution: str) -> list[dict]:
    if BeautifulSoup is not None:
        return _parse_with_bs4(html, base_url, source_key, institution)
    return _parse_with_stdlib(html, base_url, source_key, institution)


def _parse_with_bs4(html: str, base_url: str, source_key: str, institution: str) -> list[dict]:
    soup = _make_soup(html)
    for removable in soup(["script", "style", "noscript"]):
        removable.decompose()

    candidates: list[dict] = []
    for tag in soup.find_all(["a", "h2", "h3", "li", "tr"]):
        try:
            text = clean_text(tag.get_text(" ", strip=True))
            if len(text) < 8:
                continue
            link = _first_href(tag)
            candidates.append(
                {
                    "title": text,
                    "text": text,
                    "url": urljoin(base_url, link) if link else base_url,
                    "source_page_url": base_url,
                    "source": source_key,
                    "institution": institution,
                    "publication_date": first_date(text),
                }
            )
        except (AttributeError, TypeError):
            continue

    return _dedupe_candidates(candidates)


def _make_soup(html: str):
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _first_href(tag) -> str | None:
    if tag.name == "a" and tag.get("href"):
        return tag.get("href")
    nested = tag.find("a", href=True)
    return nested.get("href") if nested else None


def _parse_with_stdlib(html: str, base_url: str, source_key: str, institution: str) -> list[dict]:
    parser = _CandidateHTMLParser(base_url, source_key, institution)
    parser.feed(html)
    return _dedupe_candidates(parser.candidates)


def _dedupe_candidates(candidates: Iterable[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for candidate in candidates:
        key = (candidate.get("title"), candidate.get("url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


class _CandidateHTMLParser(HTMLParser):
    target_tags = {"a", "h2", "h3", "li"}

    def __init__(self, base_url: str, source_key: str, institution: str):
        super().__init__()
        self.base_url = base_url
        self.source_key = source_key
        self.institution = institution
        self.stack: list[dict] = []
        self.candidates: list[dict] = []

    def handle_starttag(self, tag: str, attrs):
        if tag not in self.target_tags:
            return
        href = dict(attrs).get("href")
        self.stack.append({"tag": tag, "href": href, "text": []})

    def handle_data(self, data: str):
        for item in self.stack:
            item["text"].append(data)

    def handle_endtag(self, tag: str):
        if not self.stack:
            return
        item = self.stack[-1]
        if item["tag"] != tag:
            return
        self.stack.pop()
        text = clean_text(" ".join(item["text"]))
        if len(text) < 8:
            return
        url = urljoin(self.base_url, item["href"]) if item["href"] else self.base_url
        self.candidates.append(
            {
                "title": text,
                "text": text,
                "url": url,
                "source_page_url": self.base_url,
                "source": self.source_key,
                "institution": self.institution,
                "publication_date": first_date(text),
            }
        )

