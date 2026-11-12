"""Dry-quote tests: evidenced rows get a dry quote; refused rows get
no network call at all; any non-dry response is rejected."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forgeproof_scout import scout_verdict
from intents_quote import (
    API_URL,
    QuoteRefusedError,
    build_quote_request,
    parse_dry_quote,
    quote_for_row,
    request_dry_quote,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "dry_quote_response.json")

EVIDENCE_ROW = {
    "part_name": "Bobcat 753 BICS lockout coil",
    "source_name": "All States Ag Parts",
    "listing_date": "2026-10-26",
    "region": "Mead WA",
    "price_usd": "30.89",
    "evidence_note": "verified",
}
SUBJECT_ROW = {
    "part_name": "GM 6L90 transmission 4WD",
    "source_name": "[source name]",
    "listing_date": "[listing date]",
    "region": "Mead WA",
    "price_usd": "",
    "evidence_note": "SUBJECT ONLY - not a comparable",
}


def _fixture_response():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


class RecordingTransport:
    """Fake transport that records every call and returns the fixture."""

    def __init__(self):
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        return 201, _fixture_response()


class TestDryQuote(unittest.TestCase):
    def test_request_is_always_dry(self):
        for _ in range(5):
            req = build_quote_request()
            self.assertIs(req["dry"], True)

    def test_request_targets_quote_endpoint_only(self):
        self.assertEqual(API_URL, "https://1click.chaindefuser.com/v0/quote")

    def test_request_has_required_fields(self):
        req = build_quote_request()
        for field in (
            "dry", "swapType", "slippageTolerance", "originAsset",
            "depositType", "destinationAsset", "amount", "refundTo",
            "refundType", "recipient", "recipientType", "deadline",
        ):
            self.assertIn(field, req)
        self.assertEqual(req["swapType"], "EXACT_INPUT")
        self.assertEqual(req["amount"], "1000000")

    def test_evidenced_row_gets_dry_quote(self):
        transport = RecordingTransport()
        verdict = scout_verdict([EVIDENCE_ROW], "coil")
        result = quote_for_row(verdict, transport=transport)
        self.assertTrue(result["quoted"])
        self.assertEqual(len(transport.calls), 1)
        self.assertIs(transport.calls[0]["dry"], True)
        quote = result["quote"]
        self.assertTrue(quote["dry"])
        self.assertEqual(quote["amount_in_formatted"], "1")
        self.assertEqual(quote["amount_out_formatted"], "0.9998")

    def test_refused_row_makes_no_network_call(self):
        transport = RecordingTransport()
        verdict = scout_verdict([SUBJECT_ROW], "GM 6L90")
        result = quote_for_row(verdict, transport=transport)
        self.assertFalse(result["quoted"])
        self.assertEqual(transport.calls, [])

    def test_no_match_makes_no_network_call(self):
        transport = RecordingTransport()
        verdict = scout_verdict([EVIDENCE_ROW], "nothing matches this")
        result = quote_for_row(verdict, transport=transport)
        self.assertFalse(result["quoted"])
        self.assertEqual(transport.calls, [])

    def test_response_with_deposit_address_rejected(self):
        bad = _fixture_response()
        bad["quote"]["depositAddress"] = "0xdeadbeef"
        with self.assertRaises(QuoteRefusedError):
            parse_dry_quote(bad)

    def test_response_with_deadline_rejected(self):
        bad = _fixture_response()
        bad["quote"]["deadline"] = "2026-11-12T00:00:00Z"
        with self.assertRaises(QuoteRefusedError):
            parse_dry_quote(bad)

    def test_response_without_quote_rejected(self):
        with self.assertRaises(QuoteRefusedError):
            parse_dry_quote({"correlationId": "x"})

    def test_fixture_itself_is_dry_shaped(self):
        quote = parse_dry_quote(_fixture_response())
        self.assertTrue(quote["dry"])
        self.assertEqual(quote["time_estimate_seconds"], 25)


if __name__ == "__main__":
    unittest.main()
