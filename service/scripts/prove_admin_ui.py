"""NCPC-07 same-origin admin UI proof with synthetic local data only."""
# ruff: noqa: E501

from __future__ import annotations

import json
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8087"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"
BUSINESS_TOKEN = "ncpc07-business-token-local-only"


def request(
    method: str, path: str, token: str = "", body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any] | str]:
    call = Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {},
    )
    try:
        with urlopen(call, timeout=20) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw
    except HTTPError as error:
        return error.code, cast(dict[str, Any], json.loads(error.read()))


def success(response: tuple[int, dict[str, Any] | str], expected: int) -> dict[str, Any]:
    status, payload = response
    assert status == expected and isinstance(payload, dict) and payload["success"] is True, payload
    return cast(dict[str, Any], payload["data"])


def prove() -> None:
    status, page = request("GET", "/admin")
    assert status == 200 and isinstance(page, str)
    for screen in (
        "Dashboard", "Review Queue", "Review Workspace", "Catalogue Search", "Product Detail",
        "Variant Detail", "Barcode Claims / Conflict Review", "Duplicate / Merge Review",
        "Publications / Release History", "BusinessCoverage", "Audit",
    ):
        assert screen in page
    for route in ("/v1/submissions/products", "/v1/admin/reviews", "/v1/admin/publications", "/v1/catalogue/candidates", "/v1/catalogue/variants/verify", "/v1/admin/barcodes", "/v1/admin/audit"):
        assert route in page
    assert "This is not federated production identity" in page

    submission = success(request("POST", "/v1/submissions/products", BUSINESS_TOKEN, {
        "business_id": "ncpc07-business", "business_product_ref": "NCPC07-UI-001",
        "idempotency_key": "ncpc07-ui-workflow-001", "canonical_name": "NCPC07 UI Canonical",
        "variant_name": "NCPC07 UI Canonical 500 ml", "source": "synthetic_ncpc07_ui",
    }), 201)
    review = success(request("GET", f"/v1/admin/reviews/{submission['review_id']}", ADMIN_TOKEN), 200)
    assert review["state"] == "OPEN"
    approved = success(request("POST", f"/v1/admin/reviews/{submission['review_id']}/decisions", ADMIN_TOKEN, {
        "outcome": "APPROVE_NEW", "rationale": "synthetic UI workflow identity verified",
    }), 200)
    product_id, variant_id = approved["ncpc_product_id"], approved["ncpc_variant_id"]
    release = success(
        request(
            "POST",
            "/v1/admin/publications",
            ADMIN_TOKEN,
            {"version": "NCPC07-UI-R1", "rationale": "Synthetic UI workflow publication"},
        ),
        201,
    )
    candidates = success(request("GET", f"/v1/catalogue/candidates?query={product_id}", ADMIN_TOKEN), 200)["candidates"]
    assert candidates and candidates[0]["ncpc_product_id"] == product_id
    verified = success(request("POST", "/v1/catalogue/variants/verify", ADMIN_TOKEN, {
        "ncpc_product_id": product_id, "ncpc_variant_id": variant_id, "release_version": release["version"],
    }), 200)
    assert verified["ncpc_variant_id"] == variant_id
    assert success(request("GET", "/v1/admin/barcodes", ADMIN_TOKEN), 200)["barcode_claims"] == []
    assert success(request("GET", f"/v1/admin/audit?entity_id={submission['review_id']}", ADMIN_TOKEN), 200)["events"]
    print(f"NCPC_SERVICE_ALIGNED_ADMIN_UI_RUNTIME_READY {product_id} {variant_id}")


if __name__ == "__main__":
    prove()
