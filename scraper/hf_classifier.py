"""Optional Hugging Face enrichment for edital text.

The pipeline never depends on this module for correctness. If HF_API_KEY is not
configured or the API fails, callers keep deterministic keyword classification.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

DEFAULT_HF_ENDPOINT = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

SYSTEM_PROMPT = (
    "Você é um extrator de dados de editais acadêmicos. Leia o texto fornecido e retorne "
    "ESTRITAMENTE um objeto JSON válido, sem nenhuma explicação ou texto antes ou depois. "
    "Estrutura exigida: {'status_vagas': booleano, 'total_vagas': inteiro, "
    "'linhas_pesquisa': [lista de strings], 'datas_importantes': {'inicio_inscricao': string, "
    "'fim_inscricao': string}, 'link_oficial': string}."
)


def classify_with_hf(text: str, endpoint: str | None = None, retries: int = 1, timeout: int = 20) -> dict[str, Any] | None:
    api_key = os.environ.get("HF_API_KEY")
    if not api_key:
        return None

    payload = {"inputs": f"{SYSTEM_PROMPT}\n\nTEXTO:\n{text[:4000]}"}
    headers = {"Authorization": f"Bearer {api_key}"}
    url = endpoint or os.environ.get("HF_ENDPOINT") or DEFAULT_HF_ENDPOINT

    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 503 and attempt < retries:
                time.sleep(2)
                continue
            response.raise_for_status()
            return _parse_hf_json(response.json())
        except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
            if attempt >= retries:
                return None
            time.sleep(1)
    return None


def _parse_hf_json(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict):
        text = payload.get("generated_text") or payload.get("summary_text") or payload.get("text")
        if text is None and {"status_vagas", "total_vagas"}.intersection(payload):
            return payload
    else:
        text = str(payload)

    cleaned = str(text or "").replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end >= start:
        cleaned = cleaned[start : end + 1]
    decoded = json.loads(cleaned)
    return decoded if isinstance(decoded, dict) else None

