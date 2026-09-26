# Central Catalogue Product Instructions

The Central Catalogue is a controlled, versioned reusable product and service catalogue. It supports records, categories, tags, barcodes, units, images, services, validation, duplicate detection, and controlled publishing.

- Maintain a strict separation between global canonical fields and business-specific overrides. Global synchronisation must never silently overwrite business price, stock, private description, or private business information.
- Require tenant/business identity for reads and writes. Use explicit publish/review/version states and retain provenance for imported or modified records.
- Validate barcodes, units, package sizes, images, duplicate candidates, and references. Test schema migrations and sync rules against protected overrides and partial failure/retry scenarios.
- Do not expose cost snapshots or inventory visibility unless the calling business is authorised and the data contract permits it.
- Document schema, publishing, compatibility, rollback, and reconciliation impact for every change.
