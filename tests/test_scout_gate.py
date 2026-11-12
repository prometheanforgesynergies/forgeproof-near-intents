"""Scout gate tests: evidence-backed rows pass, everything else refuses."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forgeproof_scout import gate_allows, load_comparables, scout_verdict

CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "comparables.csv")


def _row(**overrides):
    row = {
        "part_name": "Bobcat 753 BICS lockout coil",
        "part_number": "6309312",
        "source_name": "All States Ag Parts",
        "listing_date": "2026-10-26",
        "region": "Mead WA",
        "currency": "USD",
        "price_usd": "30.89",
        "evidence_note": "verified",
    }
    row.update(overrides)
    return row


class TestScoutGate(unittest.TestCase):
    def test_real_csv_evidence_row_passes(self):
        verdict = scout_verdict(load_comparables(CSV), "BICS lockout coil")
        self.assertEqual(verdict["verdict"], "evidence_backed")
        self.assertTrue(gate_allows(verdict))
        self.assertEqual(len(verdict["evidence_rows"]), 1)

    def test_real_csv_subject_only_refused(self):
        verdict = scout_verdict(load_comparables(CSV), "GM 6L90")
        self.assertEqual(verdict["verdict"], "refused")
        self.assertFalse(gate_allows(verdict))
        self.assertIn("subject only", verdict["reason"])

    def test_no_match_refused(self):
        verdict = scout_verdict(load_comparables(CSV), "part that does not exist")
        self.assertEqual(verdict["verdict"], "refused")
        self.assertIn("no matching part", verdict["reason"])

    def test_bracketed_source_refused(self):
        verdict = scout_verdict([_row(source_name="[source name]")], "coil")
        self.assertEqual(verdict["verdict"], "refused")

    def test_bracketed_date_refused(self):
        verdict = scout_verdict([_row(listing_date="[listing date]")], "coil")
        self.assertEqual(verdict["verdict"], "refused")

    def test_missing_region_refused(self):
        verdict = scout_verdict([_row(region="")], "coil")
        self.assertEqual(verdict["verdict"], "refused")

    def test_missing_price_refused(self):
        verdict = scout_verdict([_row(price_usd="")], "coil")
        self.assertEqual(verdict["verdict"], "refused")

    def test_zero_price_refused(self):
        verdict = scout_verdict([_row(price_usd="0")], "coil")
        self.assertEqual(verdict["verdict"], "refused")

    def test_placeholder_part_name_refused(self):
        verdict = scout_verdict(
            [_row(part_name="[scrap material, e.g. copper]")], "scrap material"
        )
        self.assertEqual(verdict["verdict"], "refused")

    def test_refusal_names_what_is_missing(self):
        verdict = scout_verdict([_row(source_name="", listing_date="")], "coil")
        self.assertTrue(verdict["missing"])
        joined = " ".join(verdict["missing"])
        self.assertIn("source", joined)
        self.assertIn("date", joined)


if __name__ == "__main__":
    unittest.main()
