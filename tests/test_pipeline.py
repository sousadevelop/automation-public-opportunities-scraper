from pathlib import Path
import json
import unittest

from schemas.scraper_contract import validate_response_contract
from scraper.pipeline import run_scraper_pipeline
from scraper.sources import parse_html_candidates


ROOT = Path(__file__).resolve().parent

FORMAL_ITEM_FIELDS = {
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

LEGACY_ITEM_FIELDS = {
    "id",
    "publication_date",
    "deadline_date",
    "summary",
    "document_url",
    "is_closed",
    "score",
}


def fixture_fetcher(source):
    if source == "ufpb":
        html = (ROOT / "fixtures" / "ufpb_processos.html").read_text(encoding="utf-8")
        return parse_html_candidates(
            html,
            "https://sigaa.ufpb.br/sigaa/public/programa/processo_seletivo.jsf?id=1879&lc=pt_BR",
            "ufpb",
            "Universidade Federal da Paraiba",
        ), []
    if source == "editais_pb":
        html = (ROOT / "fixtures" / "editais_pb.html").read_text(encoding="utf-8")
        return parse_html_candidates(
            html,
            "https://paraiba.pb.gov.br/diretas/secretaria-de-desenvolvimento-humano/conteudo-de-links/editais1-1",
            "editais_pb",
            "Governo do Estado da Paraiba",
        ), []
    return [], [f"Unknown fixture source: {source}"]


class PipelineContractTest(unittest.TestCase):
    def test_pipeline_returns_formal_contract(self):
        response = run_scraper_pipeline(
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
                "include_closed": False,
            },
            fetcher=fixture_fetcher,
        )

        validate_response_contract(response)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["request_id"], "11111111-1111-1111-1111-111111111111")
        self.assertGreaterEqual(len(response["items"]), 2)
        self.assertIn("total_found", response["summary"])
        self.assertIn("total_returned", response["summary"])
        self.assertIn("partial_failures", response["summary"])
        self.assertNotIn("total", response["summary"])
        self.assertNotIn("returned", response["summary"])
        self.assertIn("applied_filters", response)
        self.assertEqual(
            response["applied_filters"]["keywords"],
            ["mestrado", "doutorado", "pedagogico", "perito"],
        )
        self.assertEqual(response["applied_filters"]["sources"], ["ufpb", "editais_pb"])

        for item in response["items"]:
            self.assertTrue(FORMAL_ITEM_FIELDS.issubset(item), item)
            self.assertFalse(LEGACY_ITEM_FIELDS.intersection(item), item)
            self.assertIn(item["category"], {"academic_opportunity", "public_exam"})
            self.assertIn(item["status"], {"open", "closed", "unknown"})
            self.assertIsInstance(item["document_urls"], list)
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 1)
            self.assertEqual(item["location"]["country"], "BR")
            self.assertEqual(item["location"]["state"], "PB")
            self.assertIn("city", item["location"])

        serialized = json.dumps(response, ensure_ascii=False)
        self.assertIn("Mestrado", serialized)
        self.assertIn("pedag", serialized)
        self.assertNotIn("Perito Oficial Criminal", serialized)

    def test_closed_items_can_be_included(self):
        response = run_scraper_pipeline(
            {
                "request_id": "22222222-2222-2222-2222-222222222222",
                "country": "BR",
                "state": "PB",
                "keywords": ["perito"],
                "sources": ["editais_pb"],
                "include_closed": True,
            },
            fetcher=fixture_fetcher,
        )

        validate_response_contract(response)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["items"][0]["match_tags"], ["perito"])
        self.assertEqual(response["items"][0]["category"], "public_exam")
        self.assertEqual(response["items"][0]["subcategory"], "perito")
        self.assertEqual(response["items"][0]["deadline"], "2025-02-21")
        self.assertEqual(response["items"][0]["status"], "closed")
        self.assertEqual(
            response["items"][0]["document_urls"],
            ["https://codata.pb.gov.br/institucional/editais-concursos/convocacao-perito.pdf"],
        )

    def test_invalid_request_returns_error_contract(self):
        response = run_scraper_pipeline({}, fetcher=fixture_fetcher)
        validate_response_contract(response)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["summary"]["total_found"], 0)
        self.assertEqual(response["summary"]["total_returned"], 0)
        self.assertEqual(response["summary"]["partial_failures"], 0)
        self.assertEqual(response["items"], [])

    def test_contract_rejects_missing_formal_item_fields(self):
        response = run_scraper_pipeline(
            {
                "request_id": "33333333-3333-3333-3333-333333333333",
                "country": "BR",
                "state": "PB",
                "keywords": ["mestrado"],
                "sources": ["ufpb"],
                "include_closed": False,
            },
            fetcher=fixture_fetcher,
        )
        response["items"][0].pop("item_id")

        with self.assertRaises(ValueError):
            validate_response_contract(response)

    def test_contract_rejects_missing_applied_filters(self):
        response = run_scraper_pipeline(
            {
                "request_id": "44444444-4444-4444-4444-444444444444",
                "country": "BR",
                "state": "PB",
                "keywords": ["mestrado"],
                "sources": ["ufpb"],
                "include_closed": False,
            },
            fetcher=fixture_fetcher,
        )
        response.pop("applied_filters")

        with self.assertRaises(ValueError):
            validate_response_contract(response)


if __name__ == "__main__":
    unittest.main()
