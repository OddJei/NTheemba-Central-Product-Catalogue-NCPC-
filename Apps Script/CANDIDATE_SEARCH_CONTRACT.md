# NCPC Candidate Search Contract v1

`ncpc-candidate-search-v1` is the read-only NCPC contract for Ntheemba and
TradeFlow identity matching. It is intentionally limited to published shared
catalogue identity. It is not an inventory, price, supplier, cost, or tenant
data interface.

## Endpoint and request

Use the deployed NCPC web-app URL with either:

```text
?action=candidates&q={wording-or-alias-or-barcode}&limit={1..20}
?action=search&q={wording-or-alias-or-barcode}&limit={1..20}
?action=barcode&barcode={exact-identifier}&limit={1..20}
```

`barcode` is exact-identifier-only. `candidates` and `search` accept forgiving
wording: canonical name, variant name, brand wording, alias, identifier,
one-edit spelling typo, and `ml`, `l`, `g`, or `kg` size clues. Equivalent
metric clues are normalized (`1 L` equals `1000 ml`; `1 kg` equals `1000 g`).

Only records satisfying all of these conditions are eligible:

- product: `publicationStatus: published`, `status: active`
- variant: `publicationStatus: published`, `status: active`
- identifier and alias (when used): `status: active`

Callers cannot override these publication filters. The result is diversified to
at most two variants from a product family. `limit` is clamped to `1..20`; a
missing, zero, negative, or nonnumeric value safely defaults to `10`.

## Success envelope

```json
{
  "success": true,
  "message": "Candidate search completed",
  "data": {
    "contractVersion": "ncpc-candidate-search-v1",
    "status": "ok",
    "query": "coke 500 ml",
    "catalogueVersion": 42,
    "warnings": [],
    "noneOfTheseSupported": true,
    "candidates": [
      {
        "productId": "PRD-000001",
        "variantId": "VAR-000001",
        "canonicalName": "Coca-Cola",
        "variantName": "500 ml bottle",
        "brandName": "Coca-Cola",
        "sizeValue": 500,
        "sizeUnit": "ml",
        "salesUnit": "bottle",
        "identifiers": [{"type": "EAN13", "value": "1234567890123", "primary": true}],
        "aliases": ["Coke"],
        "matchReason": "alias_exact",
        "matchReasons": ["alias_exact"],
        "confidence": "strong_match",
        "warnings": [],
        "score": 850
      }
    ]
  },
  "catalogueVersion": 42,
  "timestamp": "2026-08-22T00:00:00.000Z"
}
```

`confidence` is one of `best_match`, `strong_match`, `possible_match`, or
`low_confidence`. `matchReasons` uses stable reason codes: `identifier_exact`,
`canonical_exact`, `alias_exact`, `all_tokens_match`, `fuzzy_spelling_match`,
`text_match`, and `size_conflict`. A size conflict keeps a textually relevant
candidate but adds the human-readable warning `Requested size does not match
this variant.` and reduces its score.

## No match and errors

A syntactically valid request with no eligible result is successful, with
`data.status: "no_match"`, `data.candidates: []`, and a warning explaining the
absence. An empty query is also `no_match`; it is never interpreted as a broad
catalogue browse.

Operational failures have `success: false`, a stable `errorCode`, and
`data.status: "error"`. The public message is intentionally safe and does not
include Apps Script, spreadsheet, authorization, or tenant details. If NCPC
cannot read its catalogue version during such a failure, `catalogueVersion` is
`null` rather than an invented value.

## Consumer rules

Consumers must retain the returned IDs and `catalogueVersion`, ask for human
confirmation when confidence or warnings warrant it, then query TradeFlow for
that tenant's availability, price, stock, supplier, and policies. Do not use
drafts, candidates, import jobs, or unapproved releases as consumer data.
