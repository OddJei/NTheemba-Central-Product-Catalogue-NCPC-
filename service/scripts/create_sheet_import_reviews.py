#!/usr/bin/env python3
"""Create one local review case for each names-only sheet-imported product."""
from sqlalchemy import select

from ncpc_service.database import SessionFactory, next_public_id, transaction
from ncpc_service.enums import ReviewState, SubmissionState, SubmissionType
from ncpc_service.models import Product, ReviewCase, Submission


def main() -> None:
    created = skipped = 0
    with SessionFactory() as session, transaction(session):
        products = session.scalars(select(Product).where(Product.provenance["migration_source"].as_string() == "approved_ncpc_apps_script_sheet")).all()
        for product in products:
            existing = session.scalar(select(Submission).where(Submission.target_product_id == product.id, Submission.source == "sheet_identity_import"))
            if existing is not None:
                skipped += 1; continue
            submission = Submission(public_id=next_public_id(session, "SUB"), submission_type=SubmissionType.NEW_PRODUCT, state=SubmissionState.PENDING_REVIEW, business_id=None, business_product_ref=None, target_product_id=product.id, target_variant_id=None, source="sheet_identity_import", submitter_client_id="bootstrap-admin", idempotency_key=f"sheet-import:{product.public_id}")
            session.add(submission); session.flush()
            session.add(ReviewCase(public_id=next_public_id(session, "REV"), submission_id=submission.id, reason="SHEET_IDENTITY_IMPORT", state=ReviewState.OPEN))
            created += 1
    print({"review_cases_created": created, "already_present": skipped})


if __name__ == "__main__": main()
