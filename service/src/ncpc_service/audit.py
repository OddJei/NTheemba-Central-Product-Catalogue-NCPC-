from typing import Any

from sqlalchemy.orm import Session

from .models import AuditEvent


def record_audit(
    session: Session,
    *,
    event_type: str,
    entity_kind: str,
    entity_id: str,
    actor_client_id: str,
    request_id: str | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    rationale: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_kind=entity_kind,
        entity_id=entity_id,
        actor_client_id=actor_client_id,
        request_id=request_id,
        old_value=old_value,
        new_value=new_value,
        rationale=rationale,
    )
    session.add(event)
    return event
