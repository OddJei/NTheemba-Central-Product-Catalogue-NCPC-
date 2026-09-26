"""NCPC-06 HTTP publish/search/verify proof; synthetic local data only."""

from __future__ import annotations

import json
import sys
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"
BUSINESS_TOKEN = "ncpc06-business-token-local-only"
READER_TOKEN = "ncpc06-reader-token-local-only"


def request(
    method: str, path: str, token: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    call = Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(call, timeout=20) as response:
            return response.status, cast(dict[str, Any], json.loads(response.read()))
    except HTTPError as error:
        return error.code, cast(dict[str, Any], json.loads(error.read()))


def success(response: tuple[int, dict[str, Any]], expected: int) -> dict[str, Any]:
    status, envelope = response
    assert status == expected and envelope["success"] is True and envelope["version"] == "v1", envelope
    return cast(dict[str, Any], envelope["data"])


def candidates(**params: str) -> list[dict[str, Any]]:
    data = success(request("GET", f"/v1/catalogue/candidates?{urlencode(params)}", READER_TOKEN), 200)
    return cast(list[dict[str, Any]], data["candidates"])


def decide(review_id: str, outcome: str, rationale: str) -> dict[str, Any]:
    return success(
        request(
            "POST",
            f"/v1/admin/reviews/{review_id}/decisions",
            ADMIN_TOKEN,
            {"outcome": outcome, "rationale": rationale},
        ),
        200,
    )


def prove() -> None:
    submission = success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_TOKEN,
            {
                "business_id": "ncpc06-business",
                "business_product_ref": "NCPC06-PUBLISHED",
                "idempotency_key": "ncpc06-published-001",
                "canonical_name": "NCPC09 Quokka Catalogue Identity",
                "variant_name": "NCPC09 Quokka Catalogue Identity 500 ml",
                "aliases": [{"text": "NCPC09 Quokka Alias"}],
                "barcodes": [{"value": "0099999999996", "source": "synthetic_ncpc06"}],
                "source": "synthetic_ncpc06",
            },
        ),
        201,
    )
    assert not candidates(query="NCPC09 Quokka Catalogue Identity")
    approved = decide(submission["review_id"], "APPROVE_NEW", "synthetic identity verified")
    product_id = approved["ncpc_product_id"]
    variant_id = approved["ncpc_variant_id"]
    release_one = success(
        request(
            "POST",
            "/v1/admin/publications",
            ADMIN_TOKEN,
            {"version": "NCPC06-R1", "rationale": "Synthetic publication proof"},
        ),
        201,
    )
    for key, value, expected in (
        ("query", "NCPC09 Quokka Catalogue Identity", "exact_product_name"),
        ("query", "NCPC09 Quokka Alias", "exact_alias"),
        ("barcode", "0099999999996", "barcode"),
        ("query", product_id, "product_id"),
        ("query", variant_id, "variant_id"),
    ):
        matches = candidates(**{key: value})
        assert matches and matches[0]["ncpc_product_id"] == product_id
        assert matches[0]["match_type"] == expected
        assert not ({"price", "stock", "cost", "supplier", "availability", "batches"} & matches[0].keys())
    success(request("GET", f"/v1/catalogue/variants/{variant_id}", READER_TOKEN), 200)
    success(
        request(
            "POST",
            "/v1/catalogue/variants/verify",
            READER_TOKEN,
            {
                "ncpc_product_id": product_id,
                "ncpc_variant_id": variant_id,
                "release_version": release_one["version"],
            },
        ),
        200,
    )
    correction = success(
        request(
            "POST",
            "/v1/submissions/corrections",
            BUSINESS_TOKEN,
            {
                "business_id": "ncpc06-business",
                "business_product_ref": "NCPC06-PUBLISHED",
                "idempotency_key": "ncpc06-correction-001",
                "ncpc_product_id": product_id,
                "ncpc_variant_id": variant_id,
                "changes": {"product.canonical_name": "NCPC09 Quokka Catalogue Corrected"},
                "source": "synthetic_ncpc06",
            },
        ),
        201,
    )
    decide(correction["review_id"], "APPROVE_CORRECTION", "synthetic correction verified")
    release_two = success(
        request(
            "POST",
            "/v1/admin/publications",
            ADMIN_TOKEN,
            {"version": "NCPC06-R2", "rationale": "Synthetic publication correction proof"},
        ),
        201,
    )
    assert release_one["content_hash"] != release_two["content_hash"]
    assert candidates(query="NCPC09 Quokka Catalogue Corrected")[0]["release_version"] == "NCPC06-R2"
    print(f"NCPC_PUBLICATION_CATALOGUE_RUNTIME_PROVED {product_id} {variant_id}")


def verify(product_id: str, variant_id: str) -> None:
    current = candidates(query="NCPC09 Quokka Catalogue Corrected")
    assert current and current[0]["ncpc_product_id"] == product_id
    verified = success(
        request(
            "POST",
            "/v1/catalogue/variants/verify",
            READER_TOKEN,
            {"ncpc_product_id": product_id, "ncpc_variant_id": variant_id, "release_version": "NCPC06-R2"},
        ),
        200,
    )
    assert verified["release_version"] == "NCPC06-R2"
    print("NCPC_PUBLICATION_CATALOGUE_RESTART_PERSISTENCE_PROVED")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--verify"]:
        assert len(sys.argv) == 4
        verify(sys.argv[2], sys.argv[3])
    else:
        assert not sys.argv[1:]
        prove()
