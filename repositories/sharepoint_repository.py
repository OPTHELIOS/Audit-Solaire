"""Persistance des dossiers d'audit et des pieces jointes sur un site
SharePoint partage, via l'authentification "app-only" (voir
`services/sharepoint_auth.py`).

Remplace `repositories/onedrive_repository.py`, qui n'ecrivait que le JSON
de l'audit (`audit.json` / `metadata.json`) dans le OneDrive personnel de
l'auditeur connecte, et ne sauvegardait JAMAIS les fichiers de preuves
(photos, PDF...). Ici :

- tout est ecrit dans la bibliotheque de documents par defaut du site
  SharePoint configure (`microsoft_app.site_id`), sous un dossier racine
  commun (`microsoft_app.root_folder`, par defaut "AuditsOPTHELIOS") ;
- les fichiers de preuves sont eux aussi envoyes (voir `upload_evidence_file`),
  ce qui comble la lacune identifiee precedemment : une photo prise sur le
  terrain est desormais sauvegardee dans le cloud, pas seulement sur le
  disque local (ephemere en cas d'hebergement) de la machine qui fait
  tourner Streamlit.

Toutes les fonctions de ce module sont appelees en mode "best effort" par
`services/autosave_service.py` : elles peuvent lever des exceptions
(reseau, permissions...), c'est a l'appelant de les avaler proprement.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests

from domain.models import Audit
from services.sharepoint_auth import get_app_only_token, get_root_folder, get_site_id

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

_SLUG_MAX_LEN = 40


def _slugify(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:_SLUG_MAX_LEN] or "audit"


def get_cloud_folder_name(audit: Audit) -> str:
    """Nom de dossier SharePoint lisible pour cet audit.

    Calcule une seule fois (a partir du nom d'operation ou, a defaut, de la
    commune) puis memorise sur `audit.meta.dossier_cloud` : tous les appels
    suivants (sauvegarde de l'audit, upload de preuves) reutilisent ce meme
    nom, meme si le nom d'operation est modifie ensuite en cours de saisie.
    Un suffixe derive de `audit_id` garantit l'unicite (deux audits avec le
    meme nom d'operation ne se marchent pas dessus).
    """
    existing = getattr(audit.meta, "dossier_cloud", None)
    if existing:
        return existing

    label = audit.projet.operation or audit.projet.adresse.commune or "audit"
    suffix = audit.meta.audit_id[:8]
    folder_name = f"{_slugify(label)}-{suffix}"
    audit.meta.dossier_cloud = folder_name
    return folder_name

# Au-dela de ce seuil, Graph API impose une session d'upload par blocs plutot
# qu'un simple PUT. 4 Mo est la limite documentee pour l'upload direct.
SIMPLE_UPLOAD_MAX_BYTES = 4 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024  # doit etre un multiple de 320 Ko ; 5 Mo convient


class SharePointNotConfigured(RuntimeError):
    pass


def _require_context() -> tuple[str, str, str]:
    token = get_app_only_token()
    site_id = get_site_id()
    if not token or not site_id:
        raise SharePointNotConfigured(
            "Sauvegarde SharePoint non configuree (secrets microsoft_app manquants "
            "ou incomplets, ou consentement admin Azure non accorde)."
        )
    return token, site_id, get_root_folder()


def _headers(token: str, content_type: str = "application/json") -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": content_type}


def _drive_item_url(site_id: str, relative_path: str) -> str:
    # Bibliotheque de documents par defaut du site (`/sites/{id}/drive`).
    return f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{relative_path}"


def _upload_small_file(token: str, site_id: str, relative_path: str, data: bytes) -> dict:
    url = f"{_drive_item_url(site_id, relative_path)}:/content"
    response = requests.put(url, headers=_headers(token, "application/octet-stream"), data=data, timeout=60)
    response.raise_for_status()
    return response.json()


def _upload_large_file(token: str, site_id: str, relative_path: str, data: bytes) -> dict:
    session_url = f"{_drive_item_url(site_id, relative_path)}:/createUploadSession"
    session_resp = requests.post(session_url, headers=_headers(token), timeout=30)
    session_resp.raise_for_status()
    upload_url = session_resp.json()["uploadUrl"]

    total = len(data)
    result: dict = {}

    for start in range(0, total, UPLOAD_CHUNK_SIZE):
        end = min(start + UPLOAD_CHUNK_SIZE, total)
        chunk = data[start:end]
        chunk_headers = {
            "Content-Length": str(len(chunk)),
            "Content-Range": f"bytes {start}-{end - 1}/{total}",
        }
        chunk_resp = requests.put(upload_url, headers=chunk_headers, data=chunk, timeout=120)
        chunk_resp.raise_for_status()
        if chunk_resp.text:
            result = chunk_resp.json()

    return result


def _upload_bytes(token: str, site_id: str, relative_path: str, data: bytes) -> dict:
    if len(data) <= SIMPLE_UPLOAD_MAX_BYTES:
        return _upload_small_file(token, site_id, relative_path, data)
    return _upload_large_file(token, site_id, relative_path, data)


def _download_text(token: str, site_id: str, relative_path: str) -> Optional[str]:
    url = f"{_drive_item_url(site_id, relative_path)}"
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


def _list_children(token: str, site_id: str, relative_path: str) -> List[Dict]:
    url = f"{_drive_item_url(site_id, relative_path)}:/children"
    response = requests.get(url, headers=_headers(token), timeout=30)

    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json().get("value", [])


def save_audit(audit: Audit) -> str:
    """Sauvegarde le JSON de l'audit (pas les fichiers de preuves, voir
    `upload_evidence_file` pour ca) dans SharePoint. Retourne le nom de
    dossier SharePoint utilise (voir `get_cloud_folder_name` : un slug
    lisible, pas l'UUID technique de `audit.meta.audit_id`)."""

    token, site_id, root_folder = _require_context()

    # Calcule (ou reutilise) le nom de dossier lisible AVANT de serialiser
    # l'audit : `get_cloud_folder_name` peut muter `audit.meta.dossier_cloud`
    # au premier appel, et on veut que cette valeur soit bien incluse dans le
    # JSON sauvegarde (sinon un rechargement ulterieur ne saurait plus dans
    # quel dossier chercher).
    folder_name = get_cloud_folder_name(audit)
    audit_id = audit.meta.audit_id
    base_path = f"{root_folder}/{folder_name}"

    payload = audit.model_dump(mode="json")
    audit_json = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    metadata = {
        "audit_id": audit_id,
        "dossier_cloud": folder_name,
        "numero_audit": getattr(audit.meta, "numero_audit", ""),
        "operation": getattr(audit.projet, "operation", ""),
        "commune": getattr(audit.projet.adresse, "commune", ""),
        "date_audit": str(getattr(audit.meta, "date_audit", "")),
        "date_modification": datetime.now().isoformat(),
        "auditeur": getattr(audit.meta, "auditeur", ""),
        "statut": getattr(audit.meta.statut, "value", str(getattr(audit.meta, "statut", ""))),
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")

    _upload_bytes(token, site_id, f"{base_path}/audit.json", audit_json)
    _upload_bytes(token, site_id, f"{base_path}/metadata.json", metadata_json)

    return folder_name


def load_audit(folder_name: str) -> Optional[Audit]:
    """Charge un audit depuis SharePoint. `folder_name` doit etre le nom de
    dossier reel (celui renvoye par `list_audits()` / `save_audit()`), pas
    forcement `audit.meta.audit_id` (les deux different depuis le nommage
    lisible des dossiers, sauf pour les tout premiers audits sauvegardes
    avant ce correctif, ou ils coincident encore)."""
    token, site_id, root_folder = _require_context()

    raw_text = _download_text(token, site_id, f"{root_folder}/{folder_name}/audit.json")
    if raw_text is None:
        return None

    raw = json.loads(raw_text)
    return Audit.model_validate(raw)


def list_audits() -> List[Dict]:
    token, site_id, root_folder = _require_context()

    folders = _list_children(token, site_id, root_folder)
    results = []

    empty_metadata = {
        "numero_audit": "", "operation": "", "commune": "",
        "date_audit": "", "date_modification": "", "auditeur": "", "statut": "",
    }

    for item in folders:
        if "folder" not in item:
            continue

        folder_name = item["name"]
        metadata_text = _download_text(token, site_id, f"{root_folder}/{folder_name}/metadata.json")

        if metadata_text is None:
            metadata = dict(empty_metadata)
        else:
            try:
                metadata = {**empty_metadata, **json.loads(metadata_text)}
            except Exception:
                metadata = dict(empty_metadata)

        # La cle "audit_id" retournee ici est volontairement forcee au NOM DE
        # DOSSIER SharePoint reel (utilisable tel quel par `load_audit`), pas
        # a la valeur eventuellement presente dans metadata.json : les deux
        # peuvent differer (ex. metadata.json corrompu/partiel, ou audit
        # sauvegarde avant l'introduction du nommage lisible).
        metadata["audit_id"] = folder_name
        results.append(metadata)

    results.sort(key=lambda x: x.get("date_modification", ""), reverse=True)
    return results


def upload_evidence_file(folder_name: str, local_path: str, relative_name: str) -> Optional[str]:
    """Envoie un fichier de preuve (photo, PDF...) deja ecrit localement vers
    SharePoint, sous `{root_folder}/{folder_name}/evidences/{relative_name}`.

    IMPORTANT : `folder_name` doit etre le meme nom de dossier que celui
    utilise par `save_audit` pour cet audit (voir `get_cloud_folder_name`),
    PAS forcement `audit.meta.audit_id` brut : sinon les preuves atterrissent
    dans un dossier different de celui contenant `audit.json`. Les appelants
    doivent donc passer `get_cloud_folder_name(audit)`, pas l'UUID.

    Retourne l'URL web du fichier sur SharePoint en cas de succes (utile pour
    l'afficher/le lier dans l'appli), ou None en cas d'echec silencieux.
    Cette fonction ne leve pas d'exception : elle est faite pour etre
    appelee en best-effort juste apres l'ecriture locale du fichier, sans
    jamais bloquer l'upload local qui, lui, reste la copie de reference
    immediate pendant la saisie terrain.
    """
    try:
        token, site_id, root_folder = _require_context()

        with open(local_path, "rb") as f:
            data = f.read()

        target_path = f"{root_folder}/{folder_name}/evidences/{relative_name}"
        result = _upload_bytes(token, site_id, target_path, data)
        return result.get("webUrl")
    except Exception:
        return None
