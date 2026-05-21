import json
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import requests

from domain.models import Audit, Preuve
from services.onedrive_auth import get_access_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
APP_ROOT = f"{GRAPH_BASE}/me/drive/special/approot"

# OneDrive interdit ces caractères dans les noms de fichiers ou de dossiers.
_FORBIDDEN_PATH_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


def _sanitize_path_segment(segment: str, fallback: str = "audit") -> str:
    """Nettoie un segment de chemin OneDrive.

    - élimine ``..`` et séparateurs de chemin pour éviter toute remontée ;
    - remplace les caractères interdits par ``_`` ;
    - replie les espaces ;
    - garantit une valeur non vide.
    """
    if not segment:
        return fallback
    cleaned = str(segment).replace("\\", "/").replace("..", "_")
    cleaned = cleaned.replace("/", "-")
    cleaned = _FORBIDDEN_PATH_CHARS.sub("_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or fallback


def _headers(token: str, content_type: str = "application/json") -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
    }


def _upload_text(token: str, relative_path: str, content: str) -> None:
    url = f"{APP_ROOT}:/{relative_path}:/content"
    response = requests.put(
        url,
        headers=_headers(token, "text/plain; charset=utf-8"),
        data=content.encode("utf-8"),
        timeout=60,
    )
    response.raise_for_status()


def _upload_binary(token: str, relative_path: str, content: bytes, mime_type: str) -> None:
    url = f"{APP_ROOT}:/{relative_path}:/content"
    response = requests.put(
        url,
        headers=_headers(token, mime_type),
        data=content,
        timeout=120,
    )
    response.raise_for_status()


def _download_text(token: str, relative_path: str) -> Optional[str]:
    url = f"{APP_ROOT}:/{relative_path}"
    response = requests.get(url, headers=_headers(token), timeout=30)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    download_url = response.json().get("@microsoft.graph.downloadUrl")

    if not download_url:
        return None

    file_response = requests.get(download_url, timeout=60)
    file_response.raise_for_status()
    return file_response.text


def _list_children(token: str, relative_path: str) -> List[Dict]:
    url = f"{APP_ROOT}:/{relative_path}:/children"
    response = requests.get(url, headers=_headers(token), timeout=30)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    return response.json().get("value", [])


def save_audit(audit: Audit) -> str:
    token = get_access_token()

    numero_audit = getattr(audit.meta, "numero_audit", None)
    date_audit = getattr(audit.meta, "date_audit", None)

    fallback = f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    audit_id = _sanitize_path_segment(numero_audit or "", fallback=fallback)

    base_path = f"audits/{audit_id}"

    payload = audit.model_dump(mode="json")
    audit_json = json.dumps(payload, ensure_ascii=False, indent=2)

    metadata = {
        "audit_id": audit_id,
        "numero_audit": getattr(audit.meta, "numero_audit", ""),
        "operation": getattr(audit.projet, "operation", ""),
        "commune": getattr(audit.projet.adresse, "commune", ""),
        "date_audit": str(getattr(audit.meta, "date_audit", "")),
        "date_modification": datetime.now().isoformat(),
        "auditeur": getattr(audit.meta, "auditeur", ""),
        "statut": getattr(audit.meta.statut, "value", str(getattr(audit.meta, "statut", ""))),
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    _upload_text(token, f"{base_path}/audit.json", audit_json)
    _upload_text(token, f"{base_path}/metadata.json", metadata_json)

    return audit_id


def _resolve_audit_id(audit: Audit) -> str:
    numero_audit = getattr(audit.meta, "numero_audit", None)
    fallback = f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return _sanitize_path_segment(numero_audit or "", fallback=fallback)


def _build_evidence_remote_name(preuve: Preuve, index: int, local_path: Path) -> str:
    """Génère un nom de fichier distant stable et sans collision.

    Préfixe ``<index>-<preuve_id sanitized>__<basename>`` pour garantir
    qu'aucun upload n'en écrase un autre quand deux preuves partagent
    le même nom de fichier local (ex. plusieurs ``photo.jpg``).
    """
    base_name = _sanitize_path_segment(local_path.name, fallback="preuve.bin")
    preuve_slug = _sanitize_path_segment(preuve.preuve_id or "", fallback="preuve")
    ordre = preuve.ordre if isinstance(preuve.ordre, int) and preuve.ordre > 0 else index
    return f"{ordre:03d}-{preuve_slug}__{base_name}"


def upload_audit_evidences(
    audit: Audit,
    *,
    token: Optional[str] = None,
    on_progress=None,
) -> List[Dict]:
    """Synchronise les preuves (photos / documents) d'un audit sur OneDrive.

    Pour chaque preuve disposant d'un fichier local existant, le contenu est
    uploadé sous ``audits/<audit_id>/evidences/<type>/<nom>``. Le champ
    ``onedrive_path`` de la preuve est mis à jour avec le chemin distant relatif.
    Les preuves sans fichier local exploitable sont ignorées sans erreur.

    Args:
        audit: Audit dont les preuves doivent être synchronisées.
        token: token OAuth déjà obtenu (utile pour les tests / les appels en
            boucle). Si ``None``, ``get_access_token`` est invoqué.
        on_progress: callback optionnel ``(index, total, preuve)`` appelé après
            chaque upload.

    Returns:
        Liste de dictionnaires décrivant chaque preuve traitée
        (``preuve_id``, ``status``, ``onedrive_path``, ``reason``).
    """

    token = token or get_access_token()
    audit_id = _resolve_audit_id(audit)
    base_path = f"audits/{audit_id}/evidences"
    results: List[Dict] = []
    total = len(audit.preuves)

    for index, preuve in enumerate(audit.preuves, start=1):
        local_path = preuve.chemin_fichier
        if not local_path:
            results.append({
                "preuve_id": preuve.preuve_id,
                "status": "skipped",
                "reason": "Aucun chemin local renseigné.",
                "onedrive_path": None,
            })
            continue

        path_obj = Path(local_path)
        if not path_obj.exists() or not path_obj.is_file():
            results.append({
                "preuve_id": preuve.preuve_id,
                "status": "skipped",
                "reason": f"Fichier local introuvable : {local_path}",
                "onedrive_path": None,
            })
            continue

        type_value = getattr(preuve.type_preuve, "value", str(preuve.type_preuve))
        type_segment = _sanitize_path_segment(str(type_value), fallback="autre")
        remote_name = _build_evidence_remote_name(preuve, index, path_obj)
        relative = f"{base_path}/{type_segment}/{remote_name}"
        mime_type, _ = mimetypes.guess_type(path_obj.name)
        mime_type = mime_type or "application/octet-stream"

        try:
            _upload_binary(token, relative, path_obj.read_bytes(), mime_type)
        except Exception as exc:
            results.append({
                "preuve_id": preuve.preuve_id,
                "status": "error",
                "reason": str(exc),
                "onedrive_path": None,
            })
            if callable(on_progress):
                on_progress(index, total, preuve)
            continue

        preuve.onedrive_path = relative
        results.append({
            "preuve_id": preuve.preuve_id,
            "status": "uploaded",
            "reason": "",
            "onedrive_path": relative,
        })

        if callable(on_progress):
            on_progress(index, total, preuve)

    return results


def load_audit(audit_id: str) -> Optional[Audit]:
    token = get_access_token()
    raw_text = _download_text(token, f"audits/{audit_id}/audit.json")

    if raw_text is None:
        return None

    raw = json.loads(raw_text)
    return Audit.model_validate(raw)


def list_audits() -> List[Dict]:
    token = get_access_token()
    audit_folders = _list_children(token, "audits")

    results = []

    for item in audit_folders:
        if "folder" not in item:
            continue

        audit_id = item["name"]
        metadata_text = _download_text(token, f"audits/{audit_id}/metadata.json")

        if metadata_text is None:
            results.append({
                "audit_id": audit_id,
                "numero_audit": "",
                "operation": "",
                "commune": "",
                "date_audit": "",
                "date_modification": "",
                "auditeur": "",
                "statut": "",
            })
            continue

        try:
            meta = json.loads(metadata_text)
            results.append(meta)
        except Exception:
            results.append({
                "audit_id": audit_id,
                "numero_audit": "",
                "operation": "",
                "commune": "",
                "date_audit": "",
                "date_modification": "",
                "auditeur": "",
                "statut": "",
            })

    results.sort(key=lambda x: x.get("date_modification", ""), reverse=True)
    return results