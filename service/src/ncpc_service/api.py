from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .auth import Principal, get_principal, token_digest
from .catalogue import CatalogueService
from .config import get_settings
from .database import SessionFactory, get_session, seed_api_client, transaction
from .enums import PrincipalRole, SnapshotState
from .errors import NcpcError
from .merge import MergeService
from .models import (
    ApiClient,
    AuditEvent,
    BarcodeClaim,
    Product,
    PublicationEntry,
    PublicationSnapshot,
    Variant,
)
from .publication import PublicationService
from .review import ReviewService
from .schemas import (
    CorrectionSubmissionRequest,
    CoverageLookupRequest,
    ExistingVariantCoverageLinkRequest,
    ExposurePreferenceRequest,
    MergeVariantRequest,
    NewProductSubmissionRequest,
    PublicationRequest,
    ReviewDecisionRequest,
    TradeFlowRpcRequest,
    VerifyVariantRequest,
)
from .submissions import SubmissionService
from .visibility import VisibilityService

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class RequestBodyLimitMiddleware:
    """Reject oversized streamed request bodies without trusting Content-Length."""
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = Headers(scope=scope).get("x-request-id", "")
        request_id = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid.uuid4())
        declared = Headers(scope=scope).get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send, request_id)
            return
        buffered: list[Message] = []
        body_size = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                break
            body_size += len(message.get("body", b""))
            if body_size > self.max_bytes:
                await self._reject(send, request_id)
                return
            if not message.get("more_body", False):
                break
        position = 0
        async def replay_receive() -> Message:
            nonlocal position
            if position < len(buffered):
                message = buffered[position]
                position += 1
                return message
            return {"type": "http.disconnect"}
        await self.app(scope, replay_receive, send)

    async def _reject(self, send: Send, request_id: str) -> None:
        body = json.dumps({"version": "v1", "request_id": request_id, "success": False, "data": None, "error": {"code": "REQUEST_TOO_LARGE", "message": "request body exceeds the configured limit"}}).encode("utf-8")
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"x-request-id", request_id.encode("ascii")), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": body})


def envelope(request: Request, data: Any, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "version": "v1",
            "request_id": request.state.request_id,
            "success": True,
            "data": data,
            "error": None,
        },
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.admin_bootstrap_token:
        with SessionFactory() as session, transaction(session):
            seed_api_client(
                session,
                ApiClient(
                    client_id=settings.admin_bootstrap_client_id,
                    token_digest=token_digest(settings.admin_bootstrap_token),
                    role=PrincipalRole.ADMIN,
                    scopes=["*"],
                    active=True,
                ),
            )
    yield


app = FastAPI(
    title="Ntheemba Central Product Catalogue",
    version="0.2.8",
    lifespan=lifespan,
    docs_url="/docs" if get_settings().environment != "production" else None,
    redoc_url=None,
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=get_settings().max_request_bytes)

if get_settings().cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next: Any) -> Any:
    supplied = request.headers.get("X-Request-ID", "")
    request.state.request_id = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid.uuid4())
    content_length = request.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        if int(content_length) > get_settings().max_request_bytes:
            return JSONResponse(
                status_code=413,
                headers={"X-Request-ID": request.state.request_id, "Cache-Control": "no-store"},
                content={
                    "version": "v1",
                    "request_id": request.state.request_id,
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": "request body exceeds the configured limit",
                    },
                },
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(NcpcError)
async def handle_ncpc_error(request: Request, exc: NcpcError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "version": "v1",
            "request_id": request.state.request_id,
            "success": False,
            "data": None,
            "error": {"code": exc.code, "message": str(exc)},
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "version": "v1",
            "request_id": request.state.request_id,
            "success": False,
            "data": None,
            "error": {"code": "INVALID_REQUEST", "message": "request validation failed"},
        },
    )


@app.get("/health")
def health(request: Request) -> JSONResponse:
    return envelope(
        request,
        {
            "service": "ncpc",
            "status": "ok",
            "api_version": "v1",
            "phases": ["02.2", "02.3", "02.4", "02.5", "02.6", "02.7", "02.8"],
        },
    )


@app.get("/admin", include_in_schema=False)
def admin_ui() -> FileResponse:
    if get_settings().environment not in {"development", "test"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(Path(__file__).with_name("admin.html"), headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"})


@app.get("/v1/catalogue/candidates")
def search_candidates(
    request: Request,
    query: str | None = Query(default=None, max_length=320),
    barcode: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=20, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    principal.require_scope("catalogue:read")
    items = CatalogueService(session).search_candidates(query=query, barcode=barcode, limit=limit)
    return envelope(request, {"candidates": [item.model_dump(mode="json") for item in items]})


@app.get("/v1/catalogue/variants/{ncpc_variant_id}")
def get_variant(
    ncpc_variant_id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    principal.require_scope("catalogue:read")
    item = CatalogueService(session).get_variant(ncpc_variant_id)
    return envelope(request, item.model_dump(mode="json"))


@app.post("/v1/catalogue/variants/verify")
def verify_variant(
    body: VerifyVariantRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    principal.require_scope("catalogue:read")
    item = CatalogueService(session).verify_variant(**body.model_dump())
    return envelope(request, item.model_dump(mode="json"))


@app.post("/v1/submissions/products")
def submit_product(
    body: NewProductSubmissionRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = SubmissionService(session).submit_product(
            body, principal, request_id=request.state.request_id
        )
    return envelope(request, result.model_dump(mode="json"), status_code=201)


@app.post("/v1/businesses/{business_id}/coverage")
def link_existing_coverage(
    business_id: str,
    body: ExistingVariantCoverageLinkRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = SubmissionService(session).link_existing_variant(
            business_id,
            body,
            principal,
            request_id=request.state.request_id,
        )
    return envelope(request, result.model_dump(mode="json"), status_code=201)


@app.post("/v1/submissions/corrections")
def submit_correction(
    body: CorrectionSubmissionRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = SubmissionService(session).submit_correction(
            body, principal, request_id=request.state.request_id
        )
    return envelope(request, result.model_dump(mode="json"), status_code=201)


@app.get("/v1/submissions/{submission_id}")
def get_submission_status(
    submission_id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    result = SubmissionService(session).get_status(submission_id, principal)
    return envelope(request, result.model_dump(mode="json"))


@app.get("/v1/admin/reviews")
def list_reviews(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    items = ReviewService(session).list_open(principal, limit)
    return envelope(request, {"reviews": [item.model_dump(mode="json") for item in items]})


@app.get("/v1/admin/audit")
def list_audit_events(
    request: Request,
    entity_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=200),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    principal.require_scope("reviews:read")
    query = select(AuditEvent).order_by(AuditEvent.occurred_at.desc())
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    events = session.scalars(query.limit(limit)).all()
    return envelope(request, {"events": [{"event_type": item.event_type, "entity_kind": item.entity_kind, "entity_id": item.entity_id, "actor_client_id": item.actor_client_id, "request_id": item.request_id, "rationale": item.rationale, "occurred_at": item.occurred_at.isoformat()} for item in events]})


def _admin_product_payload(session: Session, product: Product) -> dict[str, Any]:
    variants = session.scalars(select(Variant).where(Variant.product_id == product.id).order_by(Variant.public_id)).all()
    snapshot = session.scalar(select(PublicationSnapshot).where(PublicationSnapshot.state == SnapshotState.PUBLISHED).order_by(PublicationSnapshot.published_at.desc()).limit(1))
    published_ids = set()
    if snapshot is not None:
        published_ids = set(session.scalars(select(PublicationEntry.variant_id).where(PublicationEntry.snapshot_id == snapshot.id)))
    rows = []
    for variant in variants:
        barcodes = session.scalars(select(BarcodeClaim).where(BarcodeClaim.variant_id == variant.id, BarcodeClaim.active.is_(True))).all()
        rows.append({"ncpc_variant_id": variant.public_id, "canonical_name": variant.canonical_name, "published": variant.id in published_ids, "barcodes": [{"value": item.original_value} for item in barcodes]})
    return {"ncpc_product_id": product.public_id, "canonical_name": product.canonical_name, "variant_count": len(rows), "published_variant_count": sum(1 for row in rows if row["published"]), "barcode_count": sum(len(row["barcodes"]) for row in rows), "published": any(row["published"] for row in rows), "release_version": snapshot.version if snapshot and any(row["published"] for row in rows) else None, "variants": rows}


@app.get("/v1/admin/products")
def list_admin_products(request: Request, query: str | None = Query(default=None, max_length=320), principal: Principal = Depends(get_principal), session: Session = Depends(get_session)) -> JSONResponse:
    principal.require_scope("reviews:read")
    statement = select(Product).order_by(Product.public_id)
    if query:
        statement = statement.where(Product.canonical_name.ilike(f"%{query.strip()}%"))
    return envelope(request, {"products": [_admin_product_payload(session, product) for product in session.scalars(statement.limit(100)).all()]})


@app.get("/v1/admin/products/{product_id}")
def get_admin_product(product_id: str, request: Request, principal: Principal = Depends(get_principal), session: Session = Depends(get_session)) -> JSONResponse:
    principal.require_scope("reviews:read")
    product = session.scalar(select(Product).where(Product.public_id == product_id))
    if product is None:
        from .errors import NotFoundError
        raise NotFoundError("product not found")
    return envelope(request, _admin_product_payload(session, product))


@app.get("/v1/admin/reviews/{review_id}")
def get_review(
    review_id: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    item = ReviewService(session).get(review_id, principal)
    return envelope(request, item.model_dump(mode="json"))


@app.post("/v1/admin/reviews/{review_id}/decisions")
def decide_review(
    review_id: str,
    body: ReviewDecisionRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = ReviewService(session).decide(
            review_id, body, principal, request_id=request.state.request_id
        )
    return envelope(request, result.model_dump(mode="json"))


@app.post("/v1/admin/publications")
def publish(
    body: PublicationRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = PublicationService(session).publish(
            principal,
            requested_version=body.version,
            rationale=body.rationale,
            request_id=request.state.request_id,
        )
    return envelope(request, result.model_dump(mode="json"), status_code=201)


@app.get("/v1/admin/publications")
def list_publications(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    items = PublicationService(session).list_publications(principal, limit)
    return envelope(request, {"publications": [item.model_dump(mode="json") for item in items]})


@app.post("/v1/admin/variants/{source_variant_id}/merge")
def merge_variant(
    source_variant_id: str,
    body: MergeVariantRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = MergeService(session).merge_variant(
            source_variant_id, body, principal, request_id=request.state.request_id
        )
    return envelope(request, result.model_dump(mode="json"))


@app.get("/v1/businesses/{business_id}/coverage/{business_product_ref}/visibility")
def get_visibility(
    business_id: str,
    business_product_ref: str,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    result = VisibilityService(session).get(business_id, business_product_ref, principal)
    return envelope(request, result.model_dump(mode="json"))


@app.patch("/v1/businesses/{business_id}/coverage/{business_product_ref}/preference")
def set_visibility_preference(
    business_id: str,
    business_product_ref: str,
    body: ExposurePreferenceRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    with transaction(session):
        result = VisibilityService(session).set_preference(
            business_id,
            business_product_ref,
            body.preference,
            principal,
            request_id=request.state.request_id,
        )
    return envelope(request, result.model_dump(mode="json"))


@app.post("/v1/discovery/coverage/by-variants")
def discover_coverage(
    body: CoverageLookupRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    items = VisibilityService(session).discover_by_variants(body.ncpc_variant_ids, principal)
    return envelope(request, {"coverage": [item.model_dump(mode="json") for item in items]})


@app.post("/v1/tradeflow")
def tradeflow_rpc(
    body: TradeFlowRpcRequest,
    request: Request,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> JSONResponse:
    """Compatibility surface for Sprint 01's seven-method NCPC client port."""

    catalogue = CatalogueService(session)
    submissions = SubmissionService(session)
    action = body.action
    if action == "searchCandidates":
        principal.require_scope("catalogue:read")
        result = catalogue.search_candidates(
            query=body.data.get("query"),
            barcode=body.data.get("barcode"),
            limit=int(body.data.get("limit", 20)),
        )
        data: Any = {"candidates": [item.model_dump(mode="json") for item in result]}
    elif action == "getVariant":
        principal.require_scope("catalogue:read")
        data = catalogue.get_variant(str(body.data.get("ncpc_variant_id", ""))).model_dump(mode="json")
    elif action == "verifyVariant":
        principal.require_scope("catalogue:read")
        verified = VerifyVariantRequest.model_validate(body.data)
        data = catalogue.verify_variant(**verified.model_dump()).model_dump(mode="json")
    elif action == "submitProduct":
        product_request = NewProductSubmissionRequest.model_validate(body.data)
        with transaction(session):
            data = submissions.submit_product(
                product_request, principal, request_id=request.state.request_id
            ).model_dump(mode="json")
    elif action == "submitCorrection":
        correction_request = CorrectionSubmissionRequest.model_validate(body.data)
        with transaction(session):
            data = submissions.submit_correction(
                correction_request, principal, request_id=request.state.request_id
            ).model_dump(mode="json")
    elif action in ("getSubmissionStatus", "getCorrectionStatus"):
        data = submissions.get_status(str(body.data.get("submission_id", "")), principal).model_dump(
            mode="json"
        )
    else:
        from .errors import NcpcError

        error = NcpcError("unknown action")
        error.code = "UNKNOWN_ACTION"
        raise error
    return envelope(request, data)
