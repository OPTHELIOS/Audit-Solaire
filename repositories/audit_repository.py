import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from domain.models import Audit
from repositories.file_repository import (
    get_audit_json_path,
    get_metadata_json_path,
)


def save_audit_to_disk(audit: Audit) -> Path:
    audit_path = get_audit_json_path(audit.meta.audit_id)
    metadata_path = get_metadata_json_path(audit.meta.audit_id)

    payload = audit.model_dump(mode="json")

    audit_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata = {
        "audit_id": audit.meta.audit_id,
        "numero_audit": audit.meta.numero_audit,
        "operation": audit.projet.operation,
        "commune": audit.projet.adresse.commune,
        "date_audit": str(audit.meta.date_audit),
        "date_modification": datetime.now().isoformat(),
        "auditeur": audit.meta.auditeur,
        "statut": audit.meta.statut.value,
    }

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return audit_path


def load_audit_from_disk(audit_id: str) -> Optional[Audit]:
    audit_path = get_audit_json_path(audit_id)

    if not audit_path.exists():
        return None

    raw = json.loads(audit_path.read_text(encoding="utf-8"))
    return Audit.model_validate(raw)