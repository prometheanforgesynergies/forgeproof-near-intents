#!/usr/bin/env python3
"""ForgeProof + NEAR Intents demo CLI — quotes only, Scout-gated.

Usage:
  python3 demo.py <comparables.csv> <part query> [--fixture FILE]
  python3 demo.py comparables.csv "Bobcat 753 BICS lockout coil"
  python3 demo.py comparables.csv "GM 6L90 transmission 4WD"

Behavior:
  1. Scout-checks the part against the comparables CSV.
  2. If the row is NOT evidence-backed: prints the refusal + what is
     missing, and makes NO network call. Exit code 0 (refusal is the
     feature, not a failure).
  3. If evidence-backed: prints the evidence-backed USD price from
     Scout, then requests ONE dry 1Click quote (dry=True, no auth, no
     wallet, no deposit) and prints it, clearly labelled as a 1.00 USDC
     illustration — NOT the part price converted.

  --fixture FILE: replay a saved dry-quote response JSON instead of
     calling the network. Output is labelled FIXTURE REPLAY.
  --print-request-only: print the exact request JSON and exit without
     sending anything (shows dry=True on the record).

Nothing in this program can sign, spend, deposit, or settle anything.
"""
import argparse
import json
import sys

from forgeproof_scout import load_comparables, scout_verdict
from intents_quote import (
    DEMO_AMOUNT_LABEL,
    build_quote_request,
    parse_dry_quote,
    quote_for_row,
)


def _fixture_transport(path):
    with open(path, encoding="utf-8") as handle:
        saved = json.load(handle)

    def transport(_payload):
        return 200, saved

    return transport


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="comparables CSV path")
    parser.add_argument("query", help="part-name substring to check")
    parser.add_argument(
        "--fixture",
        metavar="FILE",
        help="replay a saved dry-quote response instead of calling the API",
    )
    parser.add_argument(
        "--print-request-only",
        action="store_true",
        help="print the request JSON and exit without sending anything",
    )
    args = parser.parse_args(argv)

    if args.print_request_only:
        print(json.dumps(build_quote_request(), indent=2))
        print("NOT SENT. dry=True is hard-coded; this request was never transmitted.")
        return 0

    rows = load_comparables(args.csv)
    verdict = scout_verdict(rows, args.query)

    print(f"ForgeProof Scout check — query '{args.query}'")
    print(
        f"matches: {verdict['matches']}  "
        f"subject-only: {verdict['subjects']}  "
        f"evidence rows: {len(verdict['evidence_rows'])}"
    )

    if verdict["verdict"] != "evidence_backed":
        print("SCOUT: REFUSED — no quote issued, no network call made.")
        print(f"reason: {verdict['reason']}")
        for item in verdict["missing"]:
            print(f"  missing: {item}")
        print("No evidence, no quote.")
        return 0

    for row in verdict["evidence_rows"]:
        print(
            f"evidence: {row['part_name']} | {row['price_usd']} {row['currency']} "
            f"| {row['source_name']} | {row['listing_date']} | {row['region']}"
        )
    print("SCOUT: EVIDENCE-BACKED — price shown from evidence only.")
    print(
        "NEAR Intents: requesting ONE dry quote "
        f"({DEMO_AMOUNT_LABEL}). No wallet, no deposit, no execution."
    )
    if args.fixture:
        print("FIXTURE REPLAY — no network call; saved dry-quote response shown.")

    try:
        transport = _fixture_transport(args.fixture) if args.fixture else None
        result = quote_for_row(verdict, transport=transport)
    except Exception as exc:  # noqa: BLE001 - demo CLI reports API errors plainly
        print(f"QUOTE FAILED: {exc}")
        print("No quote was issued. Nothing was spent or deposited.")
        return 1

    if not result["quoted"]:
        print(f"QUOTE REFUSED: {result['reason']}")
        return 0

    quote = result["quote"]
    print("DRY QUOTE (1Click, dry=True, unauthenticated):")
    print(f"  in:  {quote['amount_in_formatted']} (base units {quote['amount_in']})")
    print(f"  out: {quote['amount_out_formatted']} (base units {quote['amount_out']})")
    print(f"  out USD estimate: {quote['amount_out_usd']}")
    print(f"  min out after slippage: {quote['min_amount_out']}")
    print(f"  time estimate: {quote['time_estimate_seconds']}s")
    print("  deposit address: NONE (dry quotes issue none)")
    print(
        "  NOTE: token amounts are the 1.00 USDC illustration above. "
        "The part price is the Scout USD price printed earlier. "
        "Intents does not pay the yard in dollars."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
