from datetime import datetime
from pathlib import Path
from uuid import uuid4

from domain.enums import TypePreuve
from domain.models import Audit, Preuve
from repositories.file_repository import get_audit_dir


TYPE_TO_FOLDER = {
    TypePreuve.PHOTO: "photos",
    TypePreuve.DOCUMENT: "documents",
    TypePreuve.MESURE: "mesures",
    TypePreuve.CAPTURE: "captures",
    TypePreuve.PLAQUE_SIGNALETIQUE: "plaques",
}


def get_evidence_type_dir(audit_id: str, type_preuve: TypePreuve) -> Path:
    audit_dir = get_audit_dir(audit_id)
    evidences_dir = audit_dir / "evidences"
    evidences_dir.mkdir(parents=True, exist_ok=True)

    folder_name = TYPE_TO_FOLDER[type_preuve]
    target_dir = evidences_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    return target_dir


def save_uploaded_file(
    audit_id: str,
    uploaded_file,
    type_preuve: TypePreuve,
    section: str | None = None,
    controle_id: str | None = None,
    legende: str | None = None,
    auteur: str | None = None,
) -> Preuve:
    suffix = Path(uploaded_file.name).suffix.lower()
    preuve_id = str(uuid4())

    target_dir = get_evidence_type_dir(audit_id, type_preuve)
    target_path = target_dir / f"{preuve_id}{suffix}"

    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return Preuve(
        preuve_id=preuve_id,
        type_preuve=type_preuve,
        fichier_path=str(target_path),
        nom_original=uploaded_file.name,
        legende=legende,
        section=section,
        controle_id=controle_id,
        date_capture=datetime.now(),
        auteur=auteur,
    )


def attach_preuve_to_audit(audit: Audit, preuve: Preuve) -> Audit:
    audit.preuves.append(preuve)
    return audit


def attach_preuve_to_constat(audit: Audit, controle_id: str, preuve_id: str) -> Audit:
    for constat in audit.constats:
        if constat.controle_id == controle_id:
            if preuve_id not in constat.preuves_ids:
                constat.preuves_ids.append(preuve_id)
            break
    return audit