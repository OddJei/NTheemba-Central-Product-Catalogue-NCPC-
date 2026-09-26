"""NCPC-04 HTTP review-engine proof; synthetic local data only."""

from __future__ import annotations

import json
import sys
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8080"
BUSINESS_TOKEN = "ncpc04-business-token-local-only"
REVIEWER_TOKEN = "ncpc04-reviewer-token-local-only"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"


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
        with urlopen(call, timeout=10) as response:
            return response.status, cast(dict[str, Any], json.loads(response.read()))
    except HTTPError as error:
        return error.code, cast(dict[str, Any], json.loads(error.read()))


def success(response: tuple[int, dict[str, Any]], expected: int) -> dict[str, Any]:
    status, envelope = response
    assert status == expected and envelope["success"] is True and envelope["version"] == "v1", envelope
    return cast(dict[str, Any], envelope["data"])


def submit(ref: str, key: str, name: str) -> dict[str, Any]:
    return success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_TOKEN,
            {
                "business_id": "ncpc04-business",
                "business_product_ref": ref,
                "idempotency_key": key,
                "canonical_name": name,
                "variant_name": f"{name} 500 ml",
                "source": "synthetic_ncpc04",
            },
        ),
        201,
    )


def decide(
    review_id: str, body: dict[str, Any], token: str = REVIEWER_TOKEN
) -> dict[str, Any]:
    return success(request("POST", f"/v1/admin/reviews/{review_id}/decisions", token, body), 200)


def prove() -> None:
    approved = submit("NCPC04-NEW", "ncpc04-new-001", "NCPC04 Canonical")
    status, denied = request(
        "POST",
        f"/v1/admin/reviews/{approved['review_id']}/decisions",
        BUSINESS_TOKEN,
        {"outcome": "APPROVE_NEW", "rationale": "business cannot review"},
    )
    assert status == 403 and denied["error"]["code"] == "FORBIDDEN", denied
    approved_result = decide(
        approved["review_id"],
        {"outcome": "APPROVE_NEW", "rationale": "identity evidence verified"},
        ADMIN_TOKEN,
    )
    product_id = approved_result["ncpc_product_id"]
    variant_id = approved_result["ncpc_variant_id"]
    assert product_id.startswith("PRD-") and variant_id.startswith("VAR-")
    match = submit("NCPC04-MATCH", "ncpc04-match-001", "NCPC04 Duplicate")
    matched = decide(
        match["review_id"],
        {
            "outcome": "MATCH_EXISTING",
            "rationale": "matches approved identity",
            "matched_variant_id": variant_id,
        },
    )
    assert matched["state"] == "APPROVED" and matched["ncpc_variant_id"] == variant_id

    correction = success(
        request(
            "POST",
            "/v1/submissions/corrections",
            BUSINESS_TOKEN,
            {
                "business_id": "ncpc04-business",
                "business_product_ref": "NCPC04-NEW",
                "idempotency_key": "ncpc04-correction-001",
                "ncpc_product_id": product_id,
                "ncpc_variant_id": variant_id,
                "changes": {"variant.canonical_name": "NCPC04 Canonical Corrected 500 ml"},
                "source": "synthetic_ncpc04",
            },
        ),
        201,
    )
    corrected = decide(
        correction["review_id"],
        {"outcome": "APPROVE_CORRECTION", "rationale": "correction evidence verified"},
    )
    assert corrected["state"] == "APPROVED"

    needs = submit("NCPC04-NEEDS", "ncpc04-needs-001", "NCPC04 Needs")
    needs_result = decide(
        needs["review_id"], {"outcome": "NEEDS_MORE_INFORMATION", "rationale": "need package evidence"}
    )
    assert needs_result["state"] == "NEEDS_CHANGES"
    withdrawn = decide(needs["review_id"], {"outcome": "WITHDRAW", "rationale": "submitter withdrew request"})
    assert withdrawn["state"] == "WITHDRAWN"

    rejected = submit("NCPC04-REJECT", "ncpc04-reject-001", "NCPC04 Reject")
    rejected_result = decide(
        rejected["review_id"], {"outcome": "REJECT", "rationale": "identity evidence insufficient"}
    )
    assert rejected_result["state"] == "REJECTED"
    status, terminal = request(
        "POST",
        f"/v1/admin/reviews/{rejected['review_id']}/decisions",
        REVIEWER_TOKEN,
        {"outcome": "APPROVE_NEW", "rationale": "terminal review must remain closed"},
    )
    assert status == 409 and terminal["error"]["code"] == "INVALID_TRANSITION", terminal
    print(f"NCPC_REVIEW_ENGINE_PROVED {product_id} {variant_id}")


def verify(review_ids: list[str]) -> None:
    expected = ["APPROVED", "APPROVED", "APPROVED", "WITHDRAWN", "REJECTED"]
    observed = []
    for review_id in review_ids:
        item = success(request("GET", f"/v1/admin/reviews/{review_id}", REVIEWER_TOKEN), 200)
        observed.append(item["submission_state"])
    assert observed == expected, observed
    print("NCPC_REVIEW_ENGINE_RESTART_PERSISTENCE_PROVED")


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify"]:
        raise SystemExit("review identifiers are required after --verify")
    if sys.argv[1:2] == ["--verify"]:
        verify(sys.argv[2:])
    else:
        prove()
