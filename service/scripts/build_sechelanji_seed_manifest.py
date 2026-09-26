#!/usr/bin/env python3
"""Build a deterministic, identity-only NCPC seed manifest from the owner-supplied workbook.

The script is intentionally a generator, not an importer: it never connects to
NCPC, Google Drive, Sheets, or TradeFlow.  Rows held by the workbook remain
outside the publishable manifest with their stated reason intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openpyxl


SOURCE_KEY = "SECHELANJI_PHYSICAL_CATALOGUE_2026_09_10"
SOURCE_TITLE = "Sechelanji NCPC Publication Ready Catalogue"
DECISION_TYPE = "INITIAL_OWNER_AUTHORIZED_PUBLICATION"
MEASURE_RE = re.compile(r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b", re.IGNORECASE)
MULTIPACK_RE = re.compile(r"\b(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b", re.IGNORECASE)
PACKAGING_RE = re.compile(r"\b(PET|bottle|can|box|bag|carton|jar|tube|sachet|pouch)\b", re.IGNORECASE)
OFFICIAL_SOURCE_KEY = "TRADE_KINGS_BOOM_PRODUCT_2026_09_10"
OFFICIAL_ORGANIZATION_SOURCE_KEY = "TRADE_KINGS_ZAMBIA_ORGANIZATION_2026_09_10"


def _rows(workbook: Any, sheet_name: str) -> list[dict[str, Any]]:
    sheet = workbook[sheet_name]
    header: list[str] | None = None
    result: list[dict[str, Any]] = []
    for cells in sheet.iter_rows(values_only=True):
        if header is None:
            if cells and cells[0] == "ref":
                header = [str(cell) if cell is not None else "" for cell in cells]
            continue
        if cells and cells[0]:
            result.append({key: value for key, value in zip(header, cells)})
    return result


def _identity(name: str) -> tuple[str, str]:
    """Do not invent a family split when the physical record lacks one.

    The exact printed name is always retained as the VAR identity.  A clearly
    delimited pack suffix is removed only from the PRD display family; this is
    deliberately conservative and can be reconciled/merged later without
    changing the VAR identity.
    """
    marker = " - "
    product = name.rsplit(marker, 1)[0] if marker in name else name
    # A terminal pack description defines the VAR, not a distinct PRD. Only
    # remove an unambiguous terminal measure and optional packaging word; do
    # not guess at family names embedded in the middle of a description.
    product = re.sub(
        r"\s+\d+(?:\.\d+)?\s*(?:kg|g|ml|l)(?:\s+(?:PET|bottle|can|box|bag|carton|jar|tube|sachet|pouch))?\s*$",
        "",
        product,
        flags=re.IGNORECASE,
    )
    return product.strip(), name.strip()


def _pack_definition(name: str) -> dict[str, Any]:
    """Extract only measures and packaging literally present in the source name."""
    result: dict[str, Any] = {}
    multipack = MULTIPACK_RE.search(name)
    measure = MEASURE_RE.search(name)
    if multipack:
        result["count"] = int(multipack.group(1))
        result["each_measure"] = {"value": float(multipack.group(2)), "unit": multipack.group(3).lower()}
        result["primary_measure"] = dict(result["each_measure"])
        result["display_text"] = multipack.group(0)
    elif measure:
        value = float(measure.group(1))
        result["primary_measure"] = {"value": int(value) if value.is_integer() else value, "unit": measure.group(2).lower()}
        result["display_text"] = measure.group(0)
    packaging = PACKAGING_RE.search(name)
    if packaging:
        result["packaging"] = packaging.group(1).upper() if packaging.group(1).upper() == "PET" else packaging.group(1).lower()
    return result


def _evidence(row: dict[str, Any], *, barcode: str | None) -> list[dict[str, str]]:
    claims = [
        ("canonical_name", row["canonical_product_name"]),
        ("variant_identity", row["canonical_product_name"]),
        ("market_presence_zambia", "Observed in Sechelanji physical catalogue"),
    ]
    if barcode:
        claims.append(("barcode_identity", barcode))
    return [
        {
            "source_key": SOURCE_KEY,
            "claim_type": kind,
            "claim_value": str(value),
            "evidence_tier": "PHYSICAL_PACKAGE",
            "confidence": "HIGH",
            "verification_status": "VERIFIED" if barcode or kind != "barcode_identity" else "MISSING",
            "notes": f"Sechelanji reference {row['ref']}; {row['publication_notes']}",
        }
        for kind, value in claims
    ]


def _product_only_evidence(row: dict[str, Any]) -> list[dict[str, str]]:
    """Class-B evidence establishes a family, never an inferred variant or pack."""
    return [
        {
            "source_key": SOURCE_KEY,
            "claim_type": kind,
            "claim_value": value,
            "evidence_tier": "PHYSICAL_PACKAGE",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "notes": f"Sechelanji reference {row['ref']}; {row['publication_notes']}",
        }
        for kind, value in (
            ("canonical_name", str(row["canonical_product_name"])),
            ("market_presence_zambia", "Observed in Sechelanji physical catalogue"),
        )
    ]


def _official_candidates() -> list[dict[str, Any]]:
    """Current authoritative additions that do not need a physical barcode.

    Keep this deliberately small: every item needs an exact product, exact pack,
    and Zambia relevance from the manufacturer itself.  Do not promote older
    research rows merely because they have a plausible family match.
    """
    name = "Boom Detergent Paste 20 g Pouch"
    return [{
        "source_ref": "OFFICIAL-TRADE-KINGS-BOOM-20G-POUCH",
        "classification": "CLASS_A_PUBLISH",
        "product": {"canonical_name": "Boom Detergent Paste", "brand": "Boom", "category": "HOUSEHOLD_CLEANING"},
        "variant": {
            "canonical_name": name,
            "pack_definition": _pack_definition(name),
            "attributes": {},
            "barcode": None,
            "barcode_status": "MISSING_OR_UNVERIFIED",
        },
        "evidence": [
            {
                "source_key": OFFICIAL_SOURCE_KEY, "claim_type": "canonical_name",
                "claim_value": "Boom Detergent Paste", "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "Trade Kings official product page names Boom Detergent Paste.",
            },
            {
                "source_key": OFFICIAL_SOURCE_KEY, "claim_type": "variant_identity",
                "claim_value": name, "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "Trade Kings official product page lists a 20g pouch.",
            },
            {
                "source_key": OFFICIAL_SOURCE_KEY, "claim_type": "pack_size",
                "claim_value": "20 g", "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "Literal pack size from the official product page.",
            },
            {
                "source_key": OFFICIAL_SOURCE_KEY, "claim_type": "packaging",
                "claim_value": "pouch", "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "Literal packaging from the official product page.",
            },
            {
                "source_key": OFFICIAL_ORGANIZATION_SOURCE_KEY, "claim_type": "manufacturer_identity",
                "claim_value": "Trade Kings Group", "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "The official organization page identifies Trade Kings as Zambian.",
            },
            {
                "source_key": OFFICIAL_ORGANIZATION_SOURCE_KEY, "claim_type": "market_presence_zambia",
                "claim_value": "Zambia", "evidence_tier": "OFFICIAL_MANUFACTURER",
                "confidence": "HIGH", "verification_status": "VERIFIED",
                "notes": "Trade Kings describes its business and origins in Zambia.",
            },
        ],
        "aliases": [{"display_text": "Blue Boom", "alias_kind": "alternative_name", "source_key": OFFICIAL_ORGANIZATION_SOURCE_KEY}],
        "organization_relationship": {
            "organization_name": "Trade Kings Group",
            "relationship_type": "MANUFACTURER",
            "source_key": OFFICIAL_ORGANIZATION_SOURCE_KEY,
        },
        "decision_type": DECISION_TYPE,
    }]
def build_manifest(workbook_path: Path) -> dict[str, Any]:
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    source_accessed_at = datetime.fromtimestamp(workbook_path.stat().st_mtime, UTC).isoformat()
    ready = _rows(workbook, "Publish Ready")
    identity_only = _rows(workbook, "Identity Only")
    review = _rows(workbook, "Needs Review")
    candidates = []
    for row in ready:
        barcode = str(row["barcode"]).strip() if row.get("barcode") else None
        product_name, variant_name = _identity(str(row["canonical_product_name"]))
        candidates.append(
            {
                "source_ref": row["ref"],
                "classification": "CLASS_A_PUBLISH",
                "product": {"canonical_name": product_name, "category": row["category"]},
                "variant": {
                    "canonical_name": variant_name,
                    "pack_definition": _pack_definition(variant_name),
                    "attributes": {},
                    "barcode": barcode,
                    "barcode_status": "VERIFIED" if barcode else "MISSING_OR_UNVERIFIED",
                },
                "evidence": _evidence(row, barcode=barcode),
                "decision_type": DECISION_TYPE,
            }
        )
    candidates.extend(_official_candidates())
    product_only_candidates = [
        {
            "source_ref": row["ref"], "classification": "CLASS_B_PUBLISH_PRODUCT_HOLD_VARIANT",
            "product": {"canonical_name": str(row["canonical_product_name"]), "category": row["category"]},
            "evidence": _product_only_evidence(row),
            "decision_type": DECISION_TYPE,
        }
        for row in identity_only
    ]
    held = [
        {
            "source_ref": row["ref"], "classification": "CLASS_C_REVIEW_REQUIRED",
            "canonical_product_name": row["canonical_product_name"], "reason": row["publication_notes"],
        }
        for row in review
    ]
    manifest = {
        "schema_version": "ncpc-initial-seed-manifest-v1",
        "source_fingerprint": hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
        "decision_type": DECISION_TYPE,
        "actor_label": "NCPC initial catalogue seeding operation / owner-authorized import",
        "sources": [
            {
                "source_key": SOURCE_KEY, "title": SOURCE_TITLE, "source_type": "PHYSICAL_REVIEW",
                "authority": "OWNER_SUPPLIED_PHYSICAL_EVIDENCE", "accessed_at": source_accessed_at,
                "notes": "Reference-only physical evidence; contains no TradeFlow prices, stock, or local SKU.",
            },
            {
                "source_key": OFFICIAL_SOURCE_KEY, "title": "Boom Detergent Paste - Trade Kings Group",
                "source_url": "https://www.tradekings.co.zm/product/product-main-template/",
                "source_type": "OFFICIAL_MANUFACTURER", "authority": "TRADE_KINGS_GROUP",
                "accessed_at": "2026-09-10T00:00:00+02:00",
                "notes": "Official manufacturer page; evidence reference only, not public catalogue artwork.",
            },
            {
                "source_key": OFFICIAL_ORGANIZATION_SOURCE_KEY, "title": "About Trade Kings Group",
                "source_url": "https://www.tradekings.co.zm/about-us/",
                "source_type": "OFFICIAL_MANUFACTURER", "authority": "TRADE_KINGS_GROUP",
                "accessed_at": "2026-09-10T00:00:00+02:00",
                "notes": "Official organization page supporting Zambia manufacturer and market relevance.",
            },
        ],
        "candidates": candidates,
        "product_only_candidates": product_only_candidates,
        "held_for_review": held,
        "summary": {
            "publishable_variants": len(candidates), "verified_barcodes": sum(bool(x["variant"]["barcode"]) for x in candidates),
            "published_without_barcode": sum(not bool(x["variant"]["barcode"]) for x in candidates),
            "published_product_families": len(product_only_candidates), "held_review_required": len(review),
        },
    }
    # The receipt time is useful operational metadata but must not make a
    # rerun of identical evidence look like a new authorisation batch.
    hash_input = {key: value for key, value in manifest.items() if key != "generated_at"}
    canonical = json.dumps(hash_input, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["manifest_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "manifest_hash": manifest["manifest_hash"], **manifest["summary"]}, indent=2))


if __name__ == "__main__":
    main()
