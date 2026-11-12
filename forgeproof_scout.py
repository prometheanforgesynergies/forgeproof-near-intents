#!/usr/bin/env python3
"""ForgeProof Scout gate — evidence check, importable edition.

This is the Scout decision rule from scout_check.py (Oct 27, 2026),
kept behavior-identical and made importable so the NEAR Intents quote
layer can call it as a gate: no quote is issued unless a row passes.

A row is evidence-backed ONLY when ALL of these hold:
  * part identity: a real part_name (not a bracketed placeholder) that
    matches the query, and
  * named-source comparable: source_name present and not a bracketed
    placeholder, and
  * listing_date present and not a bracketed placeholder, and
  * region present, and
  * price_usd present and a positive number.

Anything else is refused, with the missing elements named. The gate
never invents a price, a source, a date, or a region.
"""

import csv


def load_comparables(csv_path):
    """Load the comparables CSV (Zetaris FORGEPROOF.comparables format)."""
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _is_placeholder(value):
    value = (value or "").strip()
    return (not value) or value.startswith("[")


def _price_is_positive(value):
    try:
        return float(str(value).strip()) > 0
    except (TypeError, ValueError):
        return False


def _row_defects(row):
    """Return the list of evidence elements this row is missing."""
    defects = []
    if _is_placeholder(row.get("part_name")):
        defects.append("part identity (part_name is a placeholder)")
    if _is_placeholder(row.get("source_name")):
        defects.append("named source (source_name)")
    if _is_placeholder(row.get("listing_date")):
        defects.append("listing date (listing_date)")
    if not (row.get("region") or "").strip():
        defects.append("region")
    if not _price_is_positive(row.get("price_usd")):
        defects.append("price (price_usd, positive number)")
    return defects


def scout_verdict(rows, query):
    """Run the Scout check for a part-name query.

    Returns a dict:
      query, matches, subjects, evidence_rows, verdict,
      missing (list of reasons), reason (one-line summary).
    verdict is "evidence_backed" or "refused". There is no third state.
    """
    q = (query or "").lower()
    matches = [r for r in rows if q in (r.get("part_name") or "").lower()]
    subjects = [
        r for r in matches if "SUBJECT ONLY" in (r.get("evidence_note") or "")
    ]
    evidence = [r for r in matches if not _row_defects(r)]

    if evidence:
        return {
            "query": query,
            "matches": len(matches),
            "subjects": len(subjects),
            "evidence_rows": evidence,
            "verdict": "evidence_backed",
            "missing": [],
            "reason": "evidence row present: show range from evidence only",
        }

    missing = []
    if not matches:
        missing.append("no matching part in table")
    if subjects:
        missing.append(
            "no verified comparable for this part (subject only)"
        )
    # Name the specific defects of the best-matching rows, so a refusal
    # always says WHAT is missing instead of just saying no.
    seen = set()
    for row in matches:
        for defect in _row_defects(row):
            if defect not in seen:
                seen.add(defect)
                missing.append(defect)
    if not missing:
        missing.append("verified source, date, region, and price")
    return {
        "query": query,
        "matches": len(matches),
        "subjects": len(subjects),
        "evidence_rows": [],
        "verdict": "refused",
        "missing": missing,
        "reason": "no evidence-backed row: " + "; ".join(missing),
    }


def gate_allows(verdict):
    """True only for a clean evidence-backed verdict. Nothing else passes."""
    return verdict.get("verdict") == "evidence_backed" and bool(
        verdict.get("evidence_rows")
    )
