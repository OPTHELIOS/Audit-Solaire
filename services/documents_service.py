"""Gestion des documents administratifs/techniques attendus pour le dossier
(DOE, schémas, garanties...), voir `domain/documents_catalog.py` pour la
liste et `domain/models.py::DocumentFourni` pour le modèle.

Suit le même esprit que `services/evidence_service.py` (écriture locale
d'abord, envoi cloud SharePoint best-effort ensuite, jamais bloquant)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from domain.documents_catalog import DOCUMENTS_CATALOG
from domain.models import Audit, DocumentFourni
from repositories.file_repository import get_audit_dir


def ensure_documents_state(audit: Audit) -> None:
    """Complète `audit.documents_fournis` avec les entrées manquantes du
    catalogue, sans jamais écraser une entrée déjà renseignée (même logique
    que `domain.control_service.ensure_control_state`)."""
    existing_codes = {doc.code for doc in audit.documents_fournis}

    for item in DOCUMENTS_CATALOG:
        if item["code"] not in existing_codes:
            audit.documents_fournis.append(
                DocumentFourni(code=item["code"], libelle=item["libelle"])
            )


def get_document(audit: Audit, code: str) -> DocumentFourni | None:
    return next((d for d in audit.documents_fournis if d.code == code), None)


def get_documents_dir(audit_id: str) -> Path:
    path = get_audit_dir(audit_id) / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_document_file(audit: Audit, code: str, uploaded_file: Any) -> str:
    """Écrit localement le fichier fourni pour ce document, tente un envoi
    cloud best-effort, retourne le chemin local (à stocker sur
    `DocumentFourni.fichier_path`)."""
    audit_id = audit.meta.audit_id
    suffix = Path(uploaded_file.name).suffix.lower() or ".pdf"

    target_dir = get_documents_dir(audit_id)
    target_path = target_dir / f"{code}{suffix}"

    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        from repositories.sharepoint_repository import get_cloud_folder_name, upload_evidence_file

        folder_name = get_cloud_folder_name(audit)
        upload_evidence_file(folder_name, str(target_path), f"documents/{target_path.name}")
    except Exception:
        pass

    return str(target_path)


def update_document(
    audit: Audit,
    code: str,
    *,
    fourni: bool,
    commentaire: str | None = None,
    fichier_path: str | None = None,
) -> None:
    document = get_document(audit, code)
    if document is None:
        return

    document.fourni = fourni
    document.commentaire = commentaire or None
    if fichier_path is not None:
        document.fichier_path = fichier_path


def completion_stats(audit: Audit) -> dict[str, int]:
    total = len(audit.documents_fournis)
    fournis = sum(1 for d in audit.documents_fournis if d.fourni)
    return {"total": total, "fournis": fournis, "manquants": total - fournis}
