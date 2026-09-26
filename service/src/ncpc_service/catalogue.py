from __future__ import annotations

from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from .enums import SnapshotState
from .errors import NotFoundError
from .models import PublicationEntry, PublicationSnapshot
from .normalization import normalize_barcode, normalize_text
from .public_projection import project_public_identity_payload
from .schemas import CandidateDto, VariantDto


class CatalogueService:
    def __init__(self, session: Session):
        self.session = session

    def latest_snapshot(self) -> PublicationSnapshot | None:
        return self.session.scalar(
            select(PublicationSnapshot)
            .where(PublicationSnapshot.state.in_([SnapshotState.PUBLISHED, SnapshotState.SUPERSEDED]))
            .order_by(desc(PublicationSnapshot.published_at))
            .limit(1)
        )

    def _entry_query(self, snapshot_id: str) -> Select[tuple[PublicationEntry]]:
        return select(PublicationEntry).where(PublicationEntry.snapshot_id == snapshot_id)

    def search_candidates(
        self, *, query: str | None = None, barcode: str | None = None, limit: int = 20
    ) -> list[CandidateDto]:
        snapshot = self.latest_snapshot()
        if snapshot is None:
            return []

        bounded_limit = min(max(limit, 1), 50)
        normalized_query = normalize_text(query or "")
        normalized_barcode = normalize_barcode(barcode) if barcode else None
        ranked: list[tuple[int, str, dict[str, Any], str]] = []

        for entry in self.session.scalars(self._entry_query(snapshot.id)):
            payload = project_public_identity_payload(entry.payload)
            identifiers = payload.get("identifiers", [])
            aliases = payload.get("aliases", [])
            searchable = " ".join(
                [
                    payload.get("canonical_name", ""),
                    payload.get("variant_name", ""),
                    payload.get("brand") or "",
                    payload.get("category") or "",
                    *aliases,
                ]
            )
            match_type = "name"
            if normalized_barcode:
                if normalized_barcode not in identifiers:
                    continue
                score = 100
                match_type = "barcode"
            elif normalized_query:
                normalized_searchable = normalize_text(searchable)
                if normalized_query == normalize_text(payload.get("canonical_name", "")):
                    score = 90
                    match_type = "exact_product_name"
                elif normalized_query == normalize_text(payload.get("variant_name", "")):
                    score = 88
                    match_type = "exact_variant_name"
                elif any(normalized_query == normalize_text(alias) for alias in aliases):
                    score = 85
                    match_type = "exact_alias"
                elif normalized_query in normalized_searchable:
                    score = 60
                else:
                    tokens = [token for token in normalized_query.split() if len(token) >= 2]
                    matched = sum(token in normalized_searchable for token in tokens)
                    if not tokens or matched == 0:
                        continue
                    score = 30 + int(30 * matched / len(tokens))
                    match_type = "token"
            else:
                score = 1

            ranked.append((score, payload["ncpc_variant_id"], payload, match_type))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [
            CandidateDto(
                **payload,
                catalogue_version=snapshot.content_hash[:16],
                release_version=snapshot.version,
                match_type=match_type,
            )
            for _, _, payload, match_type in ranked[:bounded_limit]
        ]

    def get_variant(self, ncpc_variant_id: str) -> VariantDto:
        snapshot = self.latest_snapshot()
        if snapshot is None:
            raise NotFoundError("published variant not found")
        entry = self.session.scalar(
            self._entry_query(snapshot.id).where(
                PublicationEntry.payload["ncpc_variant_id"].as_string() == ncpc_variant_id
            )
        )
        if entry is None:
            # JSON expression support differs between providers; retain a safe fallback.
            entry = next(
                (
                    item
                    for item in self.session.scalars(self._entry_query(snapshot.id))
                    if item.payload.get("ncpc_variant_id") == ncpc_variant_id
                ),
                None,
            )
        if entry is None:
            raise NotFoundError("published variant not found")
        return VariantDto(
            **project_public_identity_payload(entry.payload),
            catalogue_version=snapshot.content_hash[:16],
            release_version=snapshot.version,
        )

    def verify_variant(
        self, *, ncpc_product_id: str, ncpc_variant_id: str, release_version: str | None = None
    ) -> VariantDto:
        dto = self.get_variant(ncpc_variant_id)
        if dto.ncpc_product_id != ncpc_product_id:
            raise NotFoundError("published product/variant pair not found")
        if release_version is not None and dto.release_version != release_version:
            raise NotFoundError("variant is not present in the requested release")
        return dto
