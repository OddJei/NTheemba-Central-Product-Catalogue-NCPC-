from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ncpc_service.auth import token_digest
from ncpc_service.enums import PrincipalRole
from ncpc_service.models import ApiClient, AuditEvent

from .conftest import ADMIN_TOKEN, BUSINESS_A_TOKEN


def auth(token: str, request_id: str = "ncpc08-request-001") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Request-ID": request_id}


def add_client(
    session: Session,
    *,
    client_id: str,
    token: str,
    role: PrincipalRole,
    scopes: list[str],
    business_id: str | None = None,
) -> None:
    session.add(
        ApiClient(
            client_id=client_id,
            token_digest=token_digest(token),
            role=role,
            business_id=business_id,
            scopes=scopes,
        )
    )
    session.commit()


def test_role_ceiling_blocks_over_scoped_business_and_reviewer_principals(
    client: TestClient, session: Session
):
    over_scoped_business = "over-scoped-business-token"
    reviewer_token = "reviewer-token-for-ncpc08"
    add_client(
        session,
        client_id="business-over-scoped",
        token=over_scoped_business,
        role=PrincipalRole.BUSINESS,
        business_id="business-a",
        scopes=["*"],
    )
    add_client(
        session,
        client_id="reviewer-ncpc08",
        token=reviewer_token,
        role=PrincipalRole.REVIEWER,
        scopes=["reviews:read", "reviews:decide", "publications:write"],
    )

    assert client.get("/v1/admin/reviews", headers=auth(over_scoped_business)).status_code == 403
    assert client.get("/v1/admin/reviews", headers=auth(reviewer_token)).status_code == 200
    denied = client.post(
        "/v1/admin/publications",
        json={"version": "NCPC-08-DENIED", "rationale": "Reviewer must not publish"},
        headers=auth(reviewer_token),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"


def test_forged_actor_is_ignored_and_audit_identity_is_server_derived(
    client: TestClient, session: Session
):
    submitted = client.post(
        "/v1/submissions/products",
        json={
            "business_id": "business-a",
            "business_product_ref": "shop-ncpc08:NCPC08-ACTOR-001",
            "shop_id": "shop-ncpc08",
            "idempotency_key": "ncpc08-forged-actor-001",
            "canonical_name": "Synthetic actor boundary product",
            "actor_client_id": "admin",
        },
        headers=auth(BUSINESS_A_TOKEN, "ncpc08-forged-actor-request"),
    )
    assert submitted.status_code == 201
    submission_id = submitted.json()["data"]["submission_id"]
    audit = session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == submission_id, AuditEvent.event_type == "SUBMISSION_CREATED"
        )
    )
    assert audit is not None
    assert audit.actor_client_id == "business-a"
    assert audit.request_id == "ncpc08-forged-actor-request"
    assert audit.occurred_at is not None


def test_missing_invalid_auth_and_admin_ui_do_not_expose_tokens(client: TestClient):
    missing = client.get("/v1/admin/audit")
    invalid = client.get("/v1/admin/audit", headers=auth("not-a-valid-token"))
    page = client.get("/admin")

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert ADMIN_TOKEN not in missing.text
    assert ADMIN_TOKEN not in invalid.text
    assert ADMIN_TOKEN not in page.text
    assert "Local/development authentication only" in page.text


def test_publication_requires_rationale_and_never_uses_a_caller_actor_field(client: TestClient):
    invalid = client.post(
        "/v1/admin/publications",
        json={"version": "NCPC-08-RATIONALE", "actor_client_id": "business-a"},
        headers=auth(ADMIN_TOKEN),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_REQUEST"
