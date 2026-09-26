#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from ncpc_service.database import SessionFactory, transaction
from ncpc_service.legacy_import import import_legacy_export, validate_legacy_export


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or import an NCPC Apps Script v2 export")
    parser.add_argument("export", type=Path)
    parser.add_argument("--apply", action="store_true", help="commit the import to NCPC_DATABASE_URL")
    args = parser.parse_args()
    payload = json.loads(args.export.read_text(encoding="utf-8"))
    data = validate_legacy_export(payload)
    if not args.apply:
        print(
            json.dumps(
                {
                    "valid": True,
                    "apply": False,
                    "catalogue_version": data.get("catalogueVersion"),
                    "products": len(data.get("products", [])),
                    "variants": len(data.get("productVariants", [])),
                    "warning": "Dry run only; legacy releases are not claimed as reproducible snapshots.",
                },
                indent=2,
            )
        )
        return
    with SessionFactory() as session, transaction(session):
        report = import_legacy_export(session, payload)
    print(json.dumps(report.__dict__, indent=2))


if __name__ == "__main__":
    main()
