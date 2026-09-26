#!/usr/bin/env python3
"""Convert the v1 NCPC Google Sheets export into a safe local import payload.

Input is an XLSX export supplied by the owner.  The output intentionally omits
legacy IDs, user emails, timestamps, descriptions, source URLs and every
TradeFlow operational field.  Legacy IDs are used only while joining rows and
are never imported as local NCPC public IDs.
"""
import argparse
import json
from pathlib import Path

from openpyxl import load_workbook


def rows(book, name):
    sheet = book[name]
    values = list(sheet.iter_rows(values_only=True))
    headers = [str(value or "").strip() for value in values[0]]
    return [dict(zip(headers, row)) for row in values[1:] if any(cell is not None for cell in row)]


def text(value):
    return str(value).strip() if value not in (None, "") else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    book = load_workbook(args.xlsx, read_only=True, data_only=True)
    required = {"Products", "ProductVariants", "Brands", "Categories", "Identifiers", "ProductAliases"}
    missing = sorted(required - set(book.sheetnames))
    if missing:
        raise SystemExit("missing required tabs: " + ", ".join(missing))
    brands = {text(row.get("id")): text(row.get("name")) for row in rows(book, "Brands")}
    categories = {text(row.get("id")): text(row.get("name")) for row in rows(book, "Categories")}
    identifiers = {}
    for row in rows(book, "Identifiers"):
        variant_id, barcode = text(row.get("variantId")), text(row.get("identifierValue"))
        if variant_id and barcode and text(row.get("status")) == "active":
            identifiers.setdefault(variant_id, []).append(barcode)
    aliases = {}
    for row in rows(book, "ProductAliases"):
        target, alias = text(row.get("variantId")), text(row.get("alias"))
        if target and alias and text(row.get("status")) == "active":
            aliases.setdefault(target, []).append(alias)
    products = []
    for row in rows(book, "Products"):
        product_id, name = text(row.get("id")), text(row.get("canonicalName"))
        if product_id and name and text(row.get("status")) == "active":
            products.append({"legacy_product_id": product_id, "canonical_name": name, "brand": brands.get(text(row.get("brandId"))), "category": categories.get(text(row.get("categoryId")))})
    variants = []
    for row in rows(book, "ProductVariants"):
        variant_id, product_id, name = text(row.get("id")), text(row.get("productId")), text(row.get("variantName"))
        if variant_id and product_id and name and text(row.get("status")) == "active":
            variants.append({"legacy_variant_id": variant_id, "legacy_product_id": product_id, "variant_name": name, "size_value": text(row.get("sizeValue")), "size_unit": text(row.get("sizeUnit")), "packaging_type": text(row.get("packagingType")), "sales_unit": text(row.get("salesUnit")), "inventory_type": text(row.get("inventoryType")), "barcodes": identifiers.get(variant_id, []), "aliases": aliases.get(variant_id, [])})
    payload = {"source": "approved_ncpc_apps_script_sheet", "identity_only": True, "products": products, "variants": variants}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"products": len(products), "variants": len(variants), "output": str(args.output)}))


if __name__ == "__main__":
    main()
