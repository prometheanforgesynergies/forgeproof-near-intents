# ForgeProof + NEAR Intents — dry-quote layer

Built by Atlas and Bill at the Forge.

A pricing agent that only offers a payment path once a price is proven.
Built for the NEAR HACKATHON (Nov 1–14, 2026).

## Baseline disclosure — read this first

ForgeProof is an **existing product**: evidence-backed part and material
pricing for a real salvage yard (KS Universal Recycling, Spokane, WA).
A phone photo becomes an evidence-backed row — part identity, comparable
sales with source, date, and region, and a confidence flag. No evidence,
no price. That product, its Scout check, and its comparables table all
predate this hackathon.

**Only the NEAR integration in this folder is new in-window**: a
NEAR Intents (1Click) dry-quote layer, gated by the existing Scout
check. Nothing else here claims to be new. The yard still takes cash in
hand; NEAR adds reach for distant buyers without removing the human gate.

## What this does

1. **Scout gate first.** A part is checked against the comparables CSV.
   A row counts as evidence only with part identity + a named source +
   a listing date + a region + a positive price. Anything less is
   refused, with the missing elements named. Refusal is the feature.
2. **Evidence-backed rows only** get a NEAR Intents 1Click quote.
   The quote is **dry-only** (`dry: true`), unauthenticated (no JWT,
   no API key), with no wallet, no signing, no deposit, no execution,
   and no settlement. A dry response contains no deposit address.
3. **Unevidenced rows get nothing.** No quote is requested, no network
   call is made, no price band is shown.

## Honesty labels

- Intents moves crypto tokens across chains. It does **not** pay a yard
  seller in USD, Cash App, PayPal, or bank money. This demo never claims
  otherwise.
- Token amounts in the demo are a fixed **1.00 USDC illustration**
  (USDC on Arbitrum → USDC on Solana) showing what a cross-chain
  settlement quote looks like. They are **not** the part's price
  converted to tokens. The part's USD price is shown separately, from
  Scout, and the two numbers are never merged.
- The `refundTo` / `recipient` values are the placeholder addresses
  printed in the official 1Click API docs example. The API schema
  requires those fields even for dry quotes. Dry quotes issue no
  deposit address and move nothing, so the placeholders are never
  funded. Never replace them with real wallet addresses in this demo.
- Live quotes vary by the minute (solver pricing, spreads, fees). The
  quote in the demo video is the real answer returned at record time,
  reported as-is — not shopped for a prettier number.
- There is no testnet for NEAR Intents (mainnet only, per the official
  docs). That is exactly why this piece is quote-only: a dry quote is
  the safe exploration path, and no funds can move from it.

## Run it (do X, see Y)

Requires Python 3.10+ and nothing else (standard library only).
No install step. No keys. No accounts. From this folder:

```sh
# X: check a part with NO evidence (subject-only row)
python3 demo.py comparables.csv "GM 6L90 transmission 4WD"
# Y: SCOUT: REFUSED, the missing elements are named, and no network
#    call is made. "No evidence, no quote."

# X: check a part WITH evidence (verified comparable row)
python3 demo.py comparables.csv "Bobcat 753 BICS lockout coil"
# Y: the evidence-backed USD price is printed from Scout ($30.89,
#    All States Ag Parts, 2026-10-26, Mead WA), then ONE dry 1Click
#    quote is printed with "deposit address: NONE".

# X: see the exact request without sending anything
python3 demo.py comparables.csv "coil" --print-request-only
# Y: the request JSON prints with "dry": true, followed by NOT SENT.

# X: replay a saved dry quote with no network call at all
python3 demo.py comparables.csv "Bobcat 753 BICS lockout coil" \
  --fixture tests/fixtures/dry_quote_response.json
# Y: same output shape, labelled FIXTURE REPLAY.

# X: run the test suite (26 tests, no network)
python3 -m unittest discover -s tests
# Y: OK. The suite proves: the gate refuses unevidenced rows,
#    evidenced rows get a dry quote, refused rows make zero network
#    calls, non-dry responses are rejected, and no code path in the
#    package can execute a settlement (static scan).
```

## Files

| File | What it is |
|---|---|
| `forgeproof_scout.py` | Scout evidence gate (importable edition of the Oct 27 `scout_check.py` rule). |
| `intents_quote.py` | 1Click dry-quote client. `dry=True` is hard-coded; no auth, no wallet, no execution endpoints. |
| `demo.py` | CLI demo: Scout check, then (only if evidence-backed) one dry quote. |
| `comparables.csv` | Comparables table: one verified row + subject-only rows. Same format as the Zetaris table. |
| `tests/` | 26 stdlib tests + fixtures, including a saved real dry-quote response (`live_dry_quote_2026-11-11.json`, captured Nov 11, 2026). |
| `demo_transcript_2026-11-11.txt` | Verbatim transcript of the recorded local run. |
| `demo-quote-moment.mp4` | Rendered replay of that transcript (see below). |
| `render_demo_video.py` | The renderer that turns the transcript into the video. |

## Demo video

`demo-quote-moment.mp4` is a rendered replay of the verbatim local-run
transcript in `demo_transcript_2026-11-11.txt` (both demo cases: the
refusal, then the live dry quote). Every line on screen is a line from
that transcript; nothing was scripted for the camera. To verify, run
the two commands in the transcript yourself and diff the output — the
live quote numbers will differ (solver pricing moves), the shape and
the refusal will not.

## API source

NEAR Intents 1Click API, official docs, researched Nov 11, 2026:
<https://docs.near-intents.org/api-reference/oneclick/request-a-swap-quote>
— `POST https://1click.chaindefuser.com/v0/quote`, `dry: true`
returns no `depositAddress`, `timeWhenInactive`, or `deadline`.

## Status / gates

Local build only. Nothing here has been published, posted, or
submitted. Publication, the demo post, and any submission each need
Bill Koschney's separate go, in that order. This folder contains no
credentials, no wallet material, and no payout address.

## License

MIT — see `LICENSE`.
