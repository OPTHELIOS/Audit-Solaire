from __future__ import annotations

from datetime import datetime

from domain.models import Audit


def create_empty_audit() -> Audit:
    audit = Audit()
    audit.meta.updated_at = datetime.now()
    return audit


def touch_audit(audit: Audit) -> Audit:
    audit.meta.updated_at = datetime.now()
    return audit


def reset_audit() -> Audit:
    return create_empty_audit()


def audit_to_dict(audit: Audit) -> dict:
    return audit.model_dump()


def load_audit_from_dict(data: dict) -> Audit:
    return Audit(**data)