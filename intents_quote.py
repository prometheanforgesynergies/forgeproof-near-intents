#!/usr/bin/env python3
"""NEAR Intents 1Click quote layer for ForgeProof — QUOTES ONLY.

HARD RULES, enforced by construction (see tests/test_no_execution.py):
  * dry runs ONLY. The request builder hard-codes dry=True. There is no
    parameter, flag, or code path in this package that can send a live
    (non-dry) request.
  * No JWT, no API key, no Authorization header, no credentials of any
    kind. Quotes are unauthenticated (the 1Click docs note an
    unauthenticated platform fee applies to real swaps; this demo never
    swaps, so no fee is ever charged).
  * No wallet interaction at all. No signing, no keys, no deposit, no
    execution, no status polling, no settlement. The only HTTP call this
    package can make is POST /v0/quote with dry=True.
  * A dry response contains NO deposit address, NO deadline, and NO
    timeWhenInactive (per the official 1Click API docs). This module
    asserts their absence and fails closed if any ever appears.
  * The Scout gate runs FIRST (see forgeproof_scout.py). quote_for_row()
    refuses unevidenced rows without making any network call.

HONESTY LABELS (read before demoing):
  * Intents quotes token-to-token amounts. It does NOT price a scrap
    part in dollars and does NOT pay a yard seller in USD/Cash App/bank
    money. The token amounts below are a fixed 1.00 USDC ILLUSTRATION
    showing what a cross-chain settlement quote looks like for a
    verified row. They are NOT the part's price converted to tokens.
    The part's evidence-backed USD price is shown separately, from
    Scout, and the two numbers are never merged.
  * The refundTo/recipient values are the PLACEHOLDER addresses printed
    in the official 1Click API docs example. The API schema requires
    those fields even for dry quotes. Dry quotes issue no deposit
    address and move nothing, so these placeholders are never funded.
    Never replace them with real wallet addresses in this demo.

API source (researched Nov 11, 2026):
  https://docs.near-intents.org/api-reference/oneclick/request-a-swap-quote
  POST https://1click.chaindefuser.com/v0/quote
"""

import json
from datetime import datetime, timedelta, timezone
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from forgeproof_scout import gate_allows

API_URL = "https://1click.chaindefuser.com/v0/quote"

# USDC on Arbitrum -> USDC on Solana, as identified in the 1Click docs
# example. Same stablecoin both sides: the quote shows the cross-chain
# mechanism, not a currency bet.
ORIGIN_ASSET = "nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near"
DESTINATION_ASSET = (
    "nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near"
)
SWAP_TYPE = "EXACT_INPUT"
SLIPPAGE_TOLERANCE_BPS = 100  # 1%
QUOTE_WAITING_TIME_MS = 3000

# Fixed illustration amount: 1.00 USDC in base units (USDC has 6
# decimals). See the honesty labels above: illustration, not a price.
DEMO_AMOUNT_BASE_UNITS = "1000000"
DEMO_AMOUNT_LABEL = "1.00 USDC (illustration only, not the part price)"

# Placeholder addresses copied from the official docs example. Required
# by the API schema; never funded; dry quotes move nothing.
PLACEHOLDER_REFUND_TO = "0x2527D02599Ba641c19FEa793cD0F167589a0f10D"
PLACEHOLDER_RECIPIENT = "13QkxhNMrTPxoCkRdYdJ65tFuwXPhL5gLS2Z5Nr6gjRK"

# Fields a dry quote must NEVER contain (official docs). If any appears,
# the response is rejected outright.
_FORBIDDEN_DRY_FIELDS = ("depositAddress", "timeWhenInactive", "deadline")


class QuoteRefusedError(Exception):
    """Raised when the Scout gate refuses, or a response fails validation."""


def build_quote_request(amount_base_units=DEMO_AMOUNT_BASE_UNITS):
    """Build the one and only request this package can send.

    dry=True is a literal in this function. There is deliberately no
    argument that can change it.
    """
    deadline = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "dry": True,
        "swapType": SWAP_TYPE,
        "slippageTolerance": SLIPPAGE_TOLERANCE_BPS,
        "originAsset": ORIGIN_ASSET,
        "depositType": "ORIGIN_CHAIN",
        "destinationAsset": DESTINATION_ASSET,
        "amount": str(amount_base_units),
        "refundTo": PLACEHOLDER_REFUND_TO,
        "refundType": "ORIGIN_CHAIN",
        "recipient": PLACEHOLDER_RECIPIENT,
        "recipientType": "DESTINATION_CHAIN",
        "deadline": deadline,
        "quoteWaitingTimeMs": QUOTE_WAITING_TIME_MS,
    }


def _default_transport(payload):
    """POST the payload to the 1Click quote endpoint. No auth headers.

    Returns (http_status, parsed_json). This is the only network call in
    the package, and it only ever runs with a dry=True payload built by
    build_quote_request().
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Honest client identification. The 1Click endpoint sits
            # behind Cloudflare, which rejects the default
            # Python-urllib user agent (HTTP 403, error 1010). This
            # header names the demo; it carries no credentials.
            "User-Agent": "ForgeProof-NEAR-Demo/1.0 (dry-quote demo; unauthenticated)",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise QuoteRefusedError(
            f"1Click API returned HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        raise QuoteRefusedError(f"1Click API unreachable: {exc.reason}") from exc


def parse_dry_quote(response):
    """Validate a 1Click response as a dry quote and extract the display fields.

    Fails closed: any deposit/execution field present means the response
    is NOT treated as a dry quote.
    """
    if not isinstance(response, dict) or "quote" not in response:
        raise QuoteRefusedError("1Click response has no 'quote' object")
    quote = response["quote"]
    present = [f for f in _FORBIDDEN_DRY_FIELDS if f in quote]
    if present:
        raise QuoteRefusedError(
            "response is not a dry quote: unexpected fields present: "
            + ", ".join(present)
        )
    return {
        "dry": True,
        "amount_in": quote.get("amountIn"),
        "amount_in_formatted": quote.get("amountInFormatted"),
        "amount_in_usd": quote.get("amountInUsd"),
        "amount_out": quote.get("amountOut"),
        "amount_out_formatted": quote.get("amountOutFormatted"),
        "amount_out_usd": quote.get("amountOutUsd"),
        "min_amount_out": quote.get("minAmountOut"),
        "time_estimate_seconds": quote.get("timeEstimate"),
        "origin_asset": ORIGIN_ASSET,
        "destination_asset": DESTINATION_ASSET,
        "illustration": DEMO_AMOUNT_LABEL,
    }


def request_dry_quote(transport=None):
    """Request one dry quote. Returns the parsed quote dict.

    `transport` is an injectable callable(payload) -> (status, json),
    used by tests and by the --fixture replay path. When omitted, the
    real 1Click endpoint is called, unauthenticated.
    """
    payload = build_quote_request()
    assert payload["dry"] is True, "dry must always be True"
    sender = transport or _default_transport
    _status, response = sender(payload)
    return parse_dry_quote(response)


def quote_for_row(verdict, transport=None):
    """Scout-gated quote entry point. The ONLY way to get a quote.

    If the verdict is not evidence-backed, returns a refusal dict and
    makes NO network call. If evidence-backed, returns the dry quote.
    """
    if not gate_allows(verdict):
        return {
            "quoted": False,
            "reason": verdict.get("reason", "refused by Scout gate"),
            "missing": verdict.get("missing", []),
        }
    quote = request_dry_quote(transport=transport)
    return {
        "quoted": True,
        "evidence_rows": verdict["evidence_rows"],
        "quote": quote,
    }
