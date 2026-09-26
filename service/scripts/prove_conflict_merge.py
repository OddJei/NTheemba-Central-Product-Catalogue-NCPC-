"""NCPC-05 synthetic HTTP conflict and merge proof for an isolated local runtime."""

from __future__ import annotations

import concurrent.futures
import json
import sys
import threading
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8080"
ADMIN_TOKEN = "ncpc-proof-bootstrap-token-local-only"
BUSINESS_TOKEN = "ncpc05-business-token-local-only"


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
    assert status == expected and envelope["success"] is True, envelope
    return cast(dict[str, Any], envelope["data"])


def submit(ref: str, key: str, name: str, barcode: str) -> dict[str, Any]:
    return success(
        request(
            "POST",
            "/v1/submissions/products",
            BUSINESS_TOKEN,
            {
                "business_id": "ncpc05-business",
                "business_product_ref": ref,
                "idempotency_key": key,
                "canonical_name": name,
                "variant_name": f"{name} 500 ml",
                "barcodes": [{"value": barcode, "source": "synthetic_ncpc05"}],
                "source": "synthetic_ncpc05",
            },
        ),
        201,
    )


def approve(submission: dict[str, Any]) -> dict[str, Any]:
    return success(
        request(
            "POST",
            f"/v1/admin/reviews/{submission['review_id']}/decisions",
            ADMIN_TOKEN,
            {"outcome": "APPROVE_NEW", "rationale": "synthetic identity evidence verified"},
        ),
        200,
    )


def prove() -> None:
    first = approve(submit("NCPC05-SOURCE", "ncpc05-source-001", "NCPC05 Source", "0012345678905"))
    source_variant = first["ncpc_variant_id"]
    survivor = approve(submit("NCPC05-SURVIVOR", "ncpc05-survivor-001", "NCPC05 Survivor", "0012345678906"))
    survivor_variant = survivor["ncpc_variant_id"]
    duplicate_product = submit(
        "NCPC05-DUPLICATE-PRODUCT", "ncpc05-duplicate-product-001", "NCPC05 Source", "0012345678907"
    )
    duplicate_variant = submit(
        "NCPC05-DUPLICATE-VARIANT", "ncpc05-duplicate-variant-001", "NCPC05 Survivor", "0012345678908"
    )
    assert duplicate_product["state"] == duplicate_variant["state"] == "PENDING_REVIEW"

    def conflicting_submission(index: int) -> dict[str, Any]:
        return submit(
            f"NCPC05-CONFLICT-{index}",
            f"ncpc05-conflict-{index:03d}",
            f"NCPC05 Conflict {index}",
            "0012345678905",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending = list(pool.map(conflicting_submission, (1, 2)))
    approval_barrier = threading.Barrier(2)

    def concurrent_approve(item: dict[str, Any]) -> dict[str, Any]:
        approval_barrier.wait(timeout=10)
        return approve(item)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        conflicted = list(pool.map(concurrent_approve, pending))
    assert all(item["state"] == "APPROVED" for item in conflicted)

    merge_body = {
        "surviving_variant_id": survivor_variant,
        "rationale": "synthetic duplicate identities confirmed by operator",
        "idempotency_key": "ncpc05-merge-001",
    }
    merged = success(
        request("POST", f"/v1/admin/variants/{source_variant}/merge", ADMIN_TOKEN, merge_body), 200
    )
    retry = success(
        request("POST", f"/v1/admin/variants/{source_variant}/merge", ADMIN_TOKEN, merge_body), 200
    )
    assert merged == retry and merged["source_variant_id"] == source_variant
    assert merged["remapped_coverage_count"] == 1
    product_merge = success(
        request(
            "POST",
            f"/v1/admin/products/{first['ncpc_product_id']}/merge",
            ADMIN_TOKEN,
            {
                "surviving_product_id": survivor["ncpc_product_id"],
                "rationale": "variants were explicitly reviewed before product shell merge",
                "idempotency_key": "ncpc05-product-merge-001",
            },
        ),
        200,
    )
    assert product_merge["source_product_id"] == first["ncpc_product_id"]
    status, self_merge = request(
        "POST",
        f"/v1/admin/variants/{survivor_variant}/merge",
        ADMIN_TOKEN,
        {**merge_body, "surviving_variant_id": survivor_variant, "idempotency_key": "ncpc05-self-merge"},
    )
    assert status == 409 and self_merge["error"]["code"] == "CONFLICT", self_merge
    print(
        "NCPC_CONFLICT_MERGE_RUNTIME_PROVED "
        f"{first['ncpc_product_id']} {source_variant} {survivor['ncpc_product_id']} {survivor_variant}"
    )


def verify(source_variant: str, survivor_variant: str) -> None:
    result = success(
        request(
            "POST",
            f"/v1/admin/variants/{source_variant}/merge",
            ADMIN_TOKEN,
            {
                "surviving_variant_id": survivor_variant,
                "rationale": "synthetic duplicate identities confirmed by operator",
                "idempotency_key": "ncpc05-merge-001",
            },
        ),
        200,
    )
    assert result["source_variant_id"] == source_variant
    assert result["surviving_variant_id"] == survivor_variant
    print("NCPC_CONFLICT_MERGE_RESTART_PERSISTENCE_PROVED")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--verify"]:
        assert len(sys.argv) == 4
        verify(sys.argv[2], sys.argv[3])
    else:
        prove()
