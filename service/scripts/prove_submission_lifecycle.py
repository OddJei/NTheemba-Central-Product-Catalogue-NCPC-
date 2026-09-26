"""NCPC-03 HTTP and PostgreSQL persistence proof; synthetic local data only."""

from __future__ import annotations

import argparse
import json
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"
BUSINESS_A_TOKEN = "ncpc03-business-a-token-local-only"
BUSINESS_B_TOKEN = "ncpc03-business-b-token-local-only"


def request(
    method: str, path: str, token: str, body: dict[str, Any] | None = None, request_id: str = ""
) -> tuple[int, dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if request_id:
        headers["X-Request-ID"] = request_id
    call = Request(
        f"{BASE_URL}{path}", data=json.dumps(body).encode() if body else None, method=method, headers=headers
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


def product(ref: str, key: str, name: str, previous: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "business_id": "business-a",
        "business_product_ref": ref,
        "idempotency_key": key,
        "canonical_name": name,
        "variant_name": f"{name} 500 ml",
        "barcodes": [{"value": "0012345678905", "source": "synthetic"}],
        "source": "synthetic_ncpc03",
    }
    if previous:
        result["previous_submission_id"] = previous
    return result


def write() -> None:
    submitted = success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_A_TOKEN,
            product("NCPC03-NEW", "ncpc03-new-001", "NCPC03 New"),
            "ncpc03-create",
        ),
        201,
    )
    retry = success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_A_TOKEN,
            product("NCPC03-NEW", "ncpc03-new-001", "NCPC03 New"),
            "ncpc03-retry",
        ),
        201,
    )
    assert submitted["submission_id"] == retry["submission_id"]
    status, denied = request("GET", f"/v1/submissions/{submitted['submission_id']}", BUSINESS_B_TOKEN)
    assert status == 403 and denied["error"]["code"] == "FORBIDDEN", denied
    status, denied = request(
        "POST",
        f"/v1/admin/reviews/{submitted['review_id']}/decisions",
        BUSINESS_A_TOKEN,
        {"outcome": "APPROVE_NEW", "rationale": "not permitted"},
    )
    assert status == 403 and denied["error"]["code"] == "FORBIDDEN", denied
    success(
        request(
            "POST",
            f"/v1/admin/reviews/{submitted['review_id']}/decisions",
            ADMIN_TOKEN,
            {"outcome": "NEEDS_MORE_INFORMATION", "rationale": "synthetic evidence incomplete"},
            "ncpc03-needs",
        ),
        200,
    )
    approved = success(
        request(
            "POST",
            f"/v1/admin/reviews/{submitted['review_id']}/decisions",
            ADMIN_TOKEN,
            {"outcome": "APPROVE_NEW", "rationale": "synthetic evidence complete"},
            "ncpc03-approve",
        ),
        200,
    )
    assert approved["state"] == "APPROVED" and approved["ncpc_product_id"].startswith("PRD-")
    rejected = success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_A_TOKEN,
            product("NCPC03-REJECT", "ncpc03-reject-001", "NCPC03 Reject"),
            "ncpc03-reject-create",
        ),
        201,
    )
    success(
        request(
            "POST",
            f"/v1/admin/reviews/{rejected['review_id']}/decisions",
            ADMIN_TOKEN,
            {"outcome": "REJECT", "rationale": "synthetic evidence inadequate"},
            "ncpc03-reject",
        ),
        200,
    )
    status, failed = request(
        "POST",
        f"/v1/admin/reviews/{rejected['review_id']}/decisions",
        ADMIN_TOKEN,
        {"outcome": "APPROVE_NEW", "rationale": "must remain terminal"},
    )
    assert status == 409 and failed["error"]["code"] == "INVALID_TRANSITION", failed
    status, failed = request(
        "POST",
        "/v1/submissions/products",
        BUSINESS_A_TOKEN,
        product("NCPC03-NEW", "ncpc03-new-001", "Changed payload"),
    )
    assert status == 409 and failed["error"]["code"] == "CONFLICT", failed
    corrected = success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_A_TOKEN,
            product("NCPC03-REJECT", "ncpc03-corrected-001", "NCPC03 Corrected", rejected["submission_id"]),
            "ncpc03-corrected",
        ),
        201,
    )
    assert corrected["state"] == "PENDING_REVIEW"
    print("NCPC_SUBMISSION_LIFECYCLE_WRITE_PROVED")


def verify(approved_id: str, corrected_id: str, correction_id: str | None = None) -> None:
    approved = success(request("GET", f"/v1/submissions/{approved_id}", BUSINESS_A_TOKEN), 200)
    corrected = success(request("GET", f"/v1/submissions/{corrected_id}", BUSINESS_A_TOKEN), 200)
    # A later publication workflow may legitimately advance an approved submission
    # to PUBLISHED; both states prove that its decided lifecycle persisted.
    assert approved["state"] in {"APPROVED", "PUBLISHED"} and corrected["state"] == "PENDING_REVIEW"
    if correction_id:
        identity_correction = success(
            request("GET", f"/v1/submissions/{correction_id}", BUSINESS_A_TOKEN), 200
        )
        assert identity_correction["state"] == "PENDING_REVIEW"
    print("NCPC_SUBMISSION_LIFECYCLE_RESTART_PERSISTENCE_PROVED")


def correction(product_id: str, variant_id: str) -> None:
    payload = {
        "business_id": "business-a",
        "business_product_ref": "NCPC03-NEW",
        "idempotency_key": "ncpc03-identity-correction-001",
        "ncpc_product_id": product_id,
        "ncpc_variant_id": variant_id,
        "changes": {"product.canonical_name": "NCPC03 New Corrected"},
        "source": "synthetic_ncpc03",
    }
    first = success(
        request("POST", "/v1/submissions/corrections", BUSINESS_A_TOKEN, payload, "ncpc03-correction"),
        201,
    )
    retry = success(request("POST", "/v1/submissions/corrections", BUSINESS_A_TOKEN, payload), 201)
    assert first["submission_id"] == retry["submission_id"] and first["state"] == "PENDING_REVIEW"
    print(first["submission_id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("write", "verify", "correction"))
    parser.add_argument("--approved-id")
    parser.add_argument("--corrected-id")
    parser.add_argument("--product-id")
    parser.add_argument("--variant-id")
    parser.add_argument("--correction-id")
    args = parser.parse_args()
    if args.phase == "write":
        write()
    elif args.phase == "verify":
        assert args.approved_id and args.corrected_id
        verify(args.approved_id, args.corrected_id, args.correction_id)
    else:
        assert args.product_id and args.variant_id
        correction(args.product_id, args.variant_id)
