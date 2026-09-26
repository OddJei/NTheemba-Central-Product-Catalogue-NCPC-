#!/usr/bin/env python3
"""Import a sanitized NCPC Sheet extract using fresh local PRD/VAR IDs.

The extract may include controlled identity attributes (brand, category, pack,
aliases and barcode claims).  It must never include TradeFlow business facts.
"""
import argparse
import json
from pathlib import Path

from sqlalchemy import select

from ncpc_service.database import SessionFactory, next_public_id, transaction
from ncpc_service.enums import AliasState, ApprovalState, BarcodeState, LifecycleState
from ncpc_service.models import Alias, BarcodeClaim, Brand, Category, Product, Variant
from ncpc_service.normalization import normalize_barcode, normalize_text


def _reference(session, model, name: str | None):
    if not name:
        return None
    normalized = normalize_text(name)
    entity = session.scalar(select(model).where(model.normalized_name == normalized))
    if entity is None:
        entity = model(canonical_name=name, normalized_name=normalized)
        session.add(entity); session.flush()
    return entity


def _pack(row: dict) -> dict:
    pack = dict(row.get("pack_definition") or {})
    if row.get("size_value") not in (None, "") and row.get("size_unit"):
        pack.setdefault("primary_measure", {"value": row["size_value"], "unit": row["size_unit"]})
    if row.get("packaging_type"):
        pack.setdefault("packaging", row["packaging_type"])
    if pack and "display_text" not in pack:
        pack["display_text"] = " ".join(str(item) for item in (row.get("size_value"), row.get("size_unit"), row.get("packaging_type")) if item not in (None, ""))
    return pack


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding="utf-8"))
    products = {row["legacy_product_id"]: row for row in data["products"]}
    variants = [row for row in data["variants"] if row["legacy_product_id"] in products]
    if not args.apply:
        print(json.dumps({"dry_run": True, "source_products": len(products), "source_variants": len(variants), "policy": "fresh PRD/VAR IDs; drafts only; identity attributes only"}, indent=2))
        return
    report = {"products_created": 0, "variants_created": 0, "products_enriched": 0, "variants_enriched": 0, "aliases_created": 0, "barcodes_created": 0, "duplicate_products": 0, "duplicate_variants": 0}
    with SessionFactory() as session, transaction(session):
        imported = {}
        for legacy_id, row in products.items():
            name = row["canonical_name"]
            normalized = normalize_text(name)
            product = session.scalar(select(Product).where(Product.normalized_name == normalized))
            brand = _reference(session, Brand, row.get("brand"))
            category = _reference(session, Category, row.get("category"))
            if product is None:
                product = Product(public_id=next_public_id(session, "PRD"), canonical_name=name, normalized_name=normalized, brand_id=brand.id if brand else None, category_id=category.id if category else None, lifecycle=LifecycleState.ACTIVE, approval_state=ApprovalState.DRAFT, provenance={"migration_source": "approved_ncpc_apps_script_sheet", "identity_only": True})
                session.add(product); session.flush(); report["products_created"] += 1
            else:
                product.brand_id = brand.id if brand else product.brand_id
                product.category_id = category.id if category else product.category_id
                product.provenance = {key: value for key, value in (product.provenance or {}).items() if key not in {"legacy_product_id", "source_record_ref"}}
                product.provenance.update({"migration_source": "approved_ncpc_apps_script_sheet", "identity_only": True})
                report["duplicate_products"] += 1; report["products_enriched"] += 1
            for alias in row.get("aliases", []):
                text = str(alias).strip()
                if text and session.scalar(select(Alias).where(Alias.product_id == product.id, Alias.normalized_text == normalize_text(text))) is None:
                    session.add(Alias(display_text=text, normalized_text=normalize_text(text), product_id=product.id, variant_id=None, alias_kind="SOURCE_ALIAS", language=None, state=AliasState.PROPOSED, source="sheet_import", provenance={"migration_source": "approved_ncpc_apps_script_sheet"})); report["aliases_created"] += 1
            imported[legacy_id] = product
        for row in variants:
            product = imported[row["legacy_product_id"]]; name = row["variant_name"]; normalized = normalize_text(name)
            variant = session.scalar(select(Variant).where(Variant.product_id == product.id, Variant.normalized_name == normalized))
            pack = _pack(row)
            attributes = {key: row[key] for key in ("sales_unit", "inventory_type") if row.get(key) not in (None, "")}
            if variant is None:
                variant = Variant(public_id=next_public_id(session, "VAR"), product_id=product.id, canonical_name=name, normalized_name=normalized, pack_definition=pack, attributes=attributes, lifecycle=LifecycleState.ACTIVE, approval_state=ApprovalState.DRAFT, provenance={"migration_source": "approved_ncpc_apps_script_sheet", "identity_only": True})
                session.add(variant); session.flush(); report["variants_created"] += 1
            else:
                variant.pack_definition = pack or variant.pack_definition; variant.attributes = attributes or variant.attributes
                variant.provenance = {key: value for key, value in (variant.provenance or {}).items() if key not in {"legacy_variant_id", "source_record_ref"}}
                variant.provenance.update({"migration_source": "approved_ncpc_apps_script_sheet", "identity_only": True})
                report["duplicate_variants"] += 1; report["variants_enriched"] += 1
            for alias in row.get("aliases", []):
                text = str(alias).strip()
                if text and session.scalar(select(Alias).where(Alias.variant_id == variant.id, Alias.normalized_text == normalize_text(text))) is None:
                    session.add(Alias(display_text=text, normalized_text=normalize_text(text), product_id=None, variant_id=variant.id, alias_kind="SOURCE_ALIAS", language=None, state=AliasState.PROPOSED, source="sheet_import", provenance={"migration_source": "approved_ncpc_apps_script_sheet"})); report["aliases_created"] += 1
            for barcode in row.get("barcodes", []):
                raw = str(barcode).strip(); normalized_barcode = normalize_barcode(raw) if raw else ""
                if raw and session.scalar(select(BarcodeClaim).where(BarcodeClaim.variant_id == variant.id, BarcodeClaim.normalized_value == normalized_barcode)) is None:
                    session.add(BarcodeClaim(variant_id=variant.id, original_value=raw, normalized_value=normalized_barcode, symbology=None, state=BarcodeState.PENDING_VERIFICATION, source="sheet_import", source_ref=None, provenance={"imported_claim_requires_verification": True}, active=True)); report["barcodes_created"] += 1
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
