import os
import unittest

from telegram_bot.contracts import (
    ContractError,
    build_search_request,
    validate_scraper_response,
)
from telegram_bot.messages import render_response
from telegram_bot.scraper_client import fixture_scraper, run_scraper


class ContractTests(unittest.TestCase):
    def test_build_search_request_matches_contract(self):
        request = build_search_request("br", "Paraiba")

        self.assertEqual(request["country"], "BR")
        self.assertEqual(request["state"], "PB")
        self.assertEqual(request["keywords"], ["mestrado", "doutorado", "pedagogico", "perito"])
        self.assertEqual(request["sources"], ["ufpb", "editais_pb"])
        self.assertFalse(request["include_closed"])

    def test_validate_fixture_response(self):
        request = build_search_request("BR", "PB")
        response = validate_scraper_response(
            fixture_scraper(request),
            expected_request_id=request["request_id"],
        )

        self.assertEqual(response["status"], "success")
        self.assertIn("applied_filters", response)
        self.assertEqual(response["summary"]["total_found"], 1)
        self.assertEqual(response["summary"]["total_returned"], 1)
        self.assertEqual(response["summary"]["partial_failures"], 0)

    def test_rejects_invalid_match_tag(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["items"][0]["match_tags"] = ["html"]

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_non_iso_date(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["items"][0]["deadline"] = "15/07/2026"

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_accepts_null_dates(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["items"][0]["deadline"] = None
        response["items"][0]["published_at"] = None

        validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_accepts_null_location_city(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["items"][0]["location"]["city"] = None

        validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_empty_location_city(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["items"][0]["location"]["city"] = ""

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_missing_applied_filters(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        del response["applied_filters"]

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_missing_summary_field(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        del response["summary"]["partial_failures"]

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_missing_formal_item_field(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        del response["items"][0]["description_clean"]

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])

    def test_rejects_missing_location_field(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        del response["items"][0]["location"]["city"]

        with self.assertRaises(ContractError):
            validate_scraper_response(response, expected_request_id=request["request_id"])


class MessageTests(unittest.TestCase):
    def test_render_success_contains_link_and_tags(self):
        request = build_search_request("BR", "PB")
        messages = render_response(fixture_scraper(request))

        self.assertEqual(len(messages), 1)
        self.assertIn("Resultados", messages[0])
        self.assertIn("Abrir edital", messages[0])
        self.assertIn("mestrado", messages[0])
        self.assertIn("Resumo:", messages[0])
        self.assertIn("Documento 1", messages[0])
        self.assertIn("Confianca: 92%", messages[0])

    def test_render_empty(self):
        payload = {
            "request_id": "abc",
            "status": "empty",
            "country": "BR",
            "state": "PB",
            "applied_filters": {},
            "summary": {"total_found": 0, "total_returned": 0, "partial_failures": 0},
            "items": [],
            "warnings": [],
        }

        self.assertIn("Nenhum resultado", render_response(payload)[0])

    def test_render_partial_success(self):
        request = build_search_request("BR", "PB")
        response = fixture_scraper(request)
        response["status"] = "partial_success"

        self.assertIn("Resultados parciais", render_response(response)[0])

    def test_render_error(self):
        payload = {
            "request_id": "abc",
            "status": "error",
            "country": "BR",
            "state": "PB",
            "applied_filters": {},
            "summary": {"total_found": 0, "total_returned": 0, "partial_failures": 1},
            "items": [],
            "warnings": ["Sem dados atualizados."],
        }

        rendered = render_response(payload)[0]
        self.assertIn("Erro na busca", rendered)
        self.assertIn("Sem dados atualizados", rendered)


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_to_scraper_to_render_with_fixture(self):
        previous_backend = os.environ.get("SCRAPER_BACKEND")
        os.environ["SCRAPER_BACKEND"] = "telegram_bot.scraper_client:fixture_scraper"
        try:
            request = build_search_request("BR", "PB")
            response = await run_scraper(request)
            messages = render_response(response)
        finally:
            if previous_backend is None:
                os.environ.pop("SCRAPER_BACKEND", None)
            else:
                os.environ["SCRAPER_BACKEND"] = previous_backend

        self.assertEqual(response["request_id"], request["request_id"])
        self.assertIn("Resultados", messages[0])


if __name__ == "__main__":
    unittest.main()
