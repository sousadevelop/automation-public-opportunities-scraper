"""Telegram message rendering based only on summary, items and warnings."""

from __future__ import annotations

from html import escape
from typing import Any


MAX_TELEGRAM_MESSAGE_SIZE = 3900


def render_response(payload: dict[str, Any]) -> list[str]:
    status = payload["status"]
    summary = payload["summary"]
    items = payload["items"]
    warnings = payload["warnings"]

    if status == "empty":
        text = _render_empty(summary, warnings)
    elif status == "error":
        text = _render_error(summary, warnings)
    else:
        title = "Resultados parciais" if status == "partial_success" else "Resultados"
        text = _render_items(title, summary, items, warnings)

    return split_message(text)


def split_message(text: str, limit: int = MAX_TELEGRAM_MESSAGE_SIZE) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for block in text.split("\n\n"):
        block_size = len(block) + 2
        if current and current_size + block_size > limit:
            chunks.append("\n\n".join(current))
            current = [block]
            current_size = block_size
        else:
            current.append(block)
            current_size += block_size

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _render_items(
    title: str,
    summary: dict[str, Any],
    items: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    total_found = summary["total_found"]
    total_returned = summary["total_returned"]
    parts = [
        f"<b>{title}</b>",
        f"Encontrados: {escape(str(total_found))} | Retornados: {escape(str(total_returned))}",
    ]

    for item in items:
        parts.append(_render_item(item))

    if warnings:
        parts.append(_render_warnings(warnings))

    return "\n\n".join(parts)


def _render_item(item: dict[str, Any]) -> str:
    title = escape(str(item["title"]))
    source_name = escape(str(item["source"]))
    institution = item["institution"]
    location = item["location"]
    city = location["city"] or "Nao informada"
    deadline = item["deadline"]
    published = item["published_at"]
    tags = item["match_tags"]
    description = item["description_clean"]
    document_urls = item["document_urls"]
    confidence = item["confidence"]
    url = escape(str(item["source_url"]), quote=True)

    lines = [f"- <b>{title}</b>", f"Fonte: {source_name}"]
    lines.append(f"Instituicao: {escape(str(institution))}")
    lines.append(
        "Local: "
        f"{escape(str(location['country']))}/{escape(str(location['state']))} - {escape(str(city))}"
    )
    if deadline:
        lines.append(f"Prazo: {escape(str(deadline))}")
    if published:
        lines.append(f"Publicado: {escape(str(published))}")
    if tags:
        lines.append("Tags: " + ", ".join(escape(str(tag)) for tag in tags))
    if description:
        lines.append(f"Resumo: {escape(str(description))}")
    lines.append(f"Confianca: {confidence:.0%}")
    lines.append(f'<a href="{url}">Abrir edital</a>')
    for index, document_url in enumerate(document_urls, start=1):
        escaped_url = escape(str(document_url), quote=True)
        lines.append(f'<a href="{escaped_url}">Documento {index}</a>')
    return "\n".join(lines)


def _render_empty(summary: dict[str, Any], warnings: list[str]) -> str:
    parts = [
        "<b>Nenhum resultado</b>",
        f"Encontrados: {escape(str(summary['total_found']))} | Retornados: {escape(str(summary['total_returned']))}",
    ]
    if warnings:
        parts.append(_render_warnings(warnings))
    return "\n\n".join(parts)


def _render_error(summary: dict[str, Any], warnings: list[str]) -> str:
    parts = [
        "<b>Erro na busca</b>",
        f"Falhas parciais: {escape(str(summary['partial_failures']))}",
    ]
    if warnings:
        parts.append(_render_warnings(warnings))
    return "\n\n".join(parts)


def _render_warnings(warnings: list[str]) -> str:
    lines = ["Avisos:"]
    lines.extend(f"- {escape(warning)}" for warning in warnings)
    return "\n".join(lines)
