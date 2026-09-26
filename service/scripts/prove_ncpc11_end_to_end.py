"""NCPC-11 reproducible synthetic HTTP/Admin-UI acceptance proof.

Run ``write`` once in a new, project-namespaced local Compose volume after
``seed_ncpc_runtime_proof_clients.py``.  Run ``verify`` after a runtime restart.
All product state below is created through public service routes; this script
does not issue SQL or edit database records directly.
"""
# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8080"
ADMIN = "ncpc-proof-bootstrap-token-local-only"
BUSINESS_A = "ncpc11-business-a-token-local-only"
BUSINESS_B = "ncpc11-business-b-token-local-only"
BUSINESS_ID = "ncpc11-business-a"
REF = "NCPC11-MAIN-001"
NAME = "NCPC11 Synthetic Identity"
BARCODE = "0077777777773"


def request(method: str, path: str, token: str, body: dict[str, Any] | None = None, request_id: str = "") -> tuple[int, dict[str, Any] | str]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if request_id:
        headers["X-Request-ID"] = request_id
    call = Request(f"{BASE_URL}{path}", data=json.dumps(body).encode() if body is not None else None, method=method, headers=headers)
    try:
        with urlopen(call, timeout=20) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw
    except HTTPError as error:
        return error.code, cast(dict[str, Any], json.loads(error.read()))


def data(response: tuple[int, dict[str, Any] | str], expected: int) -> dict[str, Any]:
    status, envelope = response
    assert status == expected and isinstance(envelope, dict) and envelope["success"] is True and envelope["version"] == "v1", envelope
    return cast(dict[str, Any], envelope["data"])


def failure(response: tuple[int, dict[str, Any] | str], expected: int, code: str) -> None:
    status, envelope = response
    assert status == expected and isinstance(envelope, dict) and envelope["success"] is False, envelope
    assert envelope["error"]["code"] == code, envelope


def product(ref: str, key: str, name: str, barcode: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "business_id": BUSINESS_ID,
        "business_product_ref": ref,
        "idempotency_key": key,
        "canonical_name": name,
        "variant_name": f"{name} 500 ml",
        "aliases": [{"text": f"{name} alias"}],
        "location_projection": {"country": "ZM", "city": "Synthetic City"},
        "source": "synthetic_ncpc11",
    }
    if barcode:
        body["barcodes"] = [{"value": barcode, "source": "synthetic_ncpc11"}]
    return body


def submit(ref: str, key: str, name: str, barcode: str | None = None) -> dict[str, Any]:
    return data(request("POST", "/v1/submissions/products", BUSINESS_A, product(ref, key, name, barcode), f"ncpc11-{key}"), 201)


def decide(review_id: str, outcome: str, rationale: str, **extra: str) -> dict[str, Any]:
    return data(request("POST", f"/v1/admin/reviews/{review_id}/decisions", ADMIN, {"outcome": outcome, "rationale": rationale, **extra}, f"ncpc11-{outcome.lower()}"), 200)


def candidates(query: str) -> list[dict[str, Any]]:
    result = data(request("GET", f"/v1/catalogue/candidates?{urlencode({'query': query})}", ADMIN), 200)
    return cast(list[dict[str, Any]], result["candidates"])


def has_canonical_name(query: str, name: str) -> bool:
    return any(item["canonical_name"] == name for item in candidates(query))


def write() -> None:
    # Same-origin Admin UI is an operator client, while every mutable action
    # below still goes through its server-authorized /v1 endpoint.
    status, page = request("GET", "/admin", ADMIN)
    assert status == 200 and isinstance(page, str) and "Review Workspace" in page and "/v1/admin/reviews" in page

    main = submit(REF, "ncpc11-main-001", NAME, BARCODE)
    assert main["state"] == "PENDING_REVIEW" and main["review_id"]
    retry = submit(REF, "ncpc11-main-001", NAME, BARCODE)
    assert retry["submission_id"] == main["submission_id"]
    failure(request("GET", f"/v1/submissions/{main['submission_id']}", BUSINESS_B), 403, "FORBIDDEN")
    failure(request("GET", f"/v1/businesses/{BUSINESS_ID}/coverage/{REF}/visibility", BUSINESS_B), 403, "FORBIDDEN")
    assert not candidates(NAME), "unpublished identity escaped public catalogue"

    review = data(request("GET", f"/v1/admin/reviews/{main['review_id']}", ADMIN), 200)
    assert review["state"] == "OPEN" and review["submission_id"] == main["submission_id"]
    approved = decide(main["review_id"], "APPROVE_NEW", "synthetic end-to-end identity evidence verified")
    product_id, variant_id = approved["ncpc_product_id"], approved["ncpc_variant_id"]
    assert product_id.startswith("PRD-") and variant_id.startswith("VAR-")

    release_one = data(request("POST", "/v1/admin/publications", ADMIN, {"version": "NCPC11-R1", "rationale": "synthetic end-to-end first release"}, "ncpc11-release-one"), 201)
    found = candidates(NAME)
    assert found and found[0]["ncpc_product_id"] == product_id and found[0]["ncpc_variant_id"] == variant_id
    assert not ({"price", "cost", "stock", "availability", "sales", "supplier", "batches", "orders", "shop"} & found[0].keys())
    verified = data(request("POST", "/v1/catalogue/variants/verify", ADMIN, {"ncpc_product_id": product_id, "ncpc_variant_id": variant_id, "release_version": release_one["version"]}), 200)
    assert verified["release_version"] == "NCPC11-R1"
    coverage = data(request("GET", f"/v1/businesses/{BUSINESS_ID}/coverage/{REF}/visibility", BUSINESS_A), 200)
    assert coverage["coverage_state"] == "LINKED_APPROVED" and coverage["ncpc_variant_id"] == variant_id
    changed = data(request("PATCH", f"/v1/businesses/{BUSINESS_ID}/coverage/{REF}/preference", BUSINESS_A, {"preference": "WITHIN_BUSINESS", "rationale": "synthetic business visibility confirmation"}, "ncpc11-coverage"), 200)
    assert changed["effective_visibility"] == "WITHIN_BUSINESS_TRUSTED"

    rejected = submit("NCPC11-REJECTED-001", "ncpc11-rejected-001", "NCPC11 Rejected Identity")
    decide(rejected["review_id"], "REJECT", "synthetic evidence insufficient")
    failure(request("POST", f"/v1/admin/reviews/{rejected['review_id']}/decisions", ADMIN, {"outcome": "APPROVE_NEW", "rationale": "terminal state must not reopen"}), 409, "INVALID_TRANSITION")
    assert not has_canonical_name("NCPC11 Rejected Identity", "NCPC11 Rejected Identity")

    collision = submit("NCPC11-COLLISION-001", "ncpc11-collision-001", "NCPC11 Collision Identity", BARCODE)
    decide(collision["review_id"], "APPROVE_NEW", "synthetic collision review record")
    barcode_rows = data(request("GET", f"/v1/admin/barcodes?{urlencode({'normalized_value': BARCODE})}", ADMIN), 200)["barcode_claims"]
    assert len(barcode_rows) == 2 and any(row["state"] == "CONFLICTED" for row in barcode_rows), barcode_rows
    assert len({row["conflict_group_id"] for row in barcode_rows}) == 1, barcode_rows

    merge_source = decide(submit("NCPC11-MERGE-SOURCE", "ncpc11-merge-source", "NCPC11 Merge Source")["review_id"], "APPROVE_NEW", "synthetic merge source verified")
    merge_target = decide(submit("NCPC11-MERGE-TARGET", "ncpc11-merge-target", "NCPC11 Merge Target")["review_id"], "APPROVE_NEW", "synthetic merge survivor verified")
    merge_body = {"surviving_variant_id": merge_target["ncpc_variant_id"], "rationale": "synthetic duplicate identity decision", "idempotency_key": "ncpc11-merge-001"}
    merged = data(request("POST", f"/v1/admin/variants/{merge_source['ncpc_variant_id']}/merge", ADMIN, merge_body, "ncpc11-merge"), 200)
    assert data(request("POST", f"/v1/admin/variants/{merge_source['ncpc_variant_id']}/merge", ADMIN, merge_body, "ncpc11-merge-retry"), 200) == merged
    product_merged = data(request("POST", f"/v1/admin/products/{merge_source['ncpc_product_id']}/merge", ADMIN, {"surviving_product_id": merge_target["ncpc_product_id"], "rationale": "source variant was explicitly merged", "idempotency_key": "ncpc11-product-merge-001"}), 200)
    assert product_merged["source_product_id"] == merge_source["ncpc_product_id"]
    history = data(request("GET", f"/v1/admin/audit?{urlencode({'entity_id': merge_source['ncpc_variant_id']})}", ADMIN), 200)["events"]
    assert any(event["event_type"] == "VARIANT_MERGED" for event in history)

    correction = data(request("POST", "/v1/submissions/corrections", BUSINESS_A, {"business_id": BUSINESS_ID, "business_product_ref": REF, "idempotency_key": "ncpc11-correction-001", "ncpc_product_id": product_id, "ncpc_variant_id": variant_id, "changes": {"product.canonical_name": "NCPC11 Synthetic Identity Corrected"}, "source": "synthetic_ncpc11"}, "ncpc11-correction"), 201)
    decide(correction["review_id"], "APPROVE_CORRECTION", "synthetic correction verified")
    release_two = data(request("POST", "/v1/admin/publications", ADMIN, {"version": "NCPC11-R2", "rationale": "synthetic corrected release"}, "ncpc11-release-two"), 201)
    publications = data(request("GET", "/v1/admin/publications", ADMIN), 200)["publications"]
    old = next(item for item in publications if item["version"] == release_one["version"])
    assert old["content_hash"] == release_one["content_hash"] and old["item_count"] == release_one["item_count"]
    assert release_two["content_hash"] != release_one["content_hash"]
    failure(request("POST", "/v1/submissions/products", BUSINESS_A, {**product("NCPC11-OPERATIONAL", "ncpc11-operational", "NCPC11 Operational Rejection"), "location_projection": {"stock": 1}}), 422, "INVALID_REQUEST")
    print("NCPC_END_TO_END_SYNTHETIC_ACCEPTANCE_WRITE_PROVED")


def verify() -> None:
    records = candidates("NCPC11 Synthetic Identity Corrected")
    assert records and records[0]["release_version"] == "NCPC11-R2", records
    item = records[0]
    data(request("POST", "/v1/catalogue/variants/verify", ADMIN, {"ncpc_product_id": item["ncpc_product_id"], "ncpc_variant_id": item["ncpc_variant_id"], "release_version": "NCPC11-R2"}), 200)
    coverage = data(request("GET", f"/v1/businesses/{BUSINESS_ID}/coverage/{REF}/visibility", BUSINESS_A), 200)
    assert coverage["ncpc_variant_id"] == item["ncpc_variant_id"] and coverage["effective_visibility"] == "WITHIN_BUSINESS_TRUSTED"
    assert not has_canonical_name("NCPC11 Rejected Identity", "NCPC11 Rejected Identity")
    print("NCPC_END_TO_END_SYNTHETIC_ACCEPTANCE_RESTART_PERSISTENCE_PROVED")


if __name__ == "__main__":
    assert sys.argv[1:] in (["write"], ["verify"])
    (write if sys.argv[1] == "write" else verify)()
