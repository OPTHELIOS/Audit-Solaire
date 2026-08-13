from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from domain.enums import TypePreuve
from domain.models import Audit, Preuve
from repositories.file_repository import get_audit_dir, get_cover_photo_dir


TYPE_TO_FOLDER = {
    TypePreuve.PHOTO: "photos",
    TypePreuve.DOCUMENT: "documents",
    TypePreuve.MESURE: "mesures",
    TypePreuve.CAPTURE: "captures",
    TypePreuve.PLAQUE_SIGNALETIQUE: "plaques",
}

# Redimensionnement/compression automatique des photos a l'upload : evite que
# des photos de tablette en plein format (souvent 4-10 Mo) alourdissent
# inutilement le stockage local, les sauvegardes cloud et les exports
# DOCX/JSON.
COMPRESSIBLE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_DIMENSION_PX = 1600
JPEG_QUALITY = 85


def get_evidence_type_dir(audit_id: str, type_preuve: TypePreuve) -> Path:
    audit_dir = get_audit_dir(audit_id)
    evidences_dir = audit_dir / "evidences"
    evidences_dir.mkdir(parents=True, exist_ok=True)

    folder_name = TYPE_TO_FOLDER[type_preuve]
    target_dir = evidences_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    return target_dir


def _compress_image_if_possible(uploaded_file, suffix: str) -> tuple[bytes, str]:
    """Redimensionne/recompresse une image envoyee, sans jamais faire echouer l'upload.

    Retourne les octets a ecrire sur disque et le suffixe de fichier a utiliser.
    En cas d'erreur (format non supporte par Pillow, image corrompue...), on
    revient silencieusement au fichier original tel quel.
    """
    if suffix not in COMPRESSIBLE_EXTENSIONS:
        return bytes(uploaded_file.getbuffer()), suffix

    try:
        from PIL import Image

        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "P", "LA"):
            image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_DIMENSION_PX, MAX_IMAGE_DIMENSION_PX))

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue(), ".jpg"
    except Exception:
        return bytes(uploaded_file.getbuffer()), suffix


def _try_cloud_backup(audit: Audit, type_preuve: TypePreuve, target_path: Path) -> str | None:
    """Tentative best-effort d'envoi du fichier vers SharePoint, juste apres
    l'ecriture locale. `upload_evidence_file` est deja defensive (elle
    avale ses propres exceptions et renvoie None si la sauvegarde cloud
    n'est pas configuree) : ce wrapper ajoute juste un filet supplementaire
    au cas ou l'import lui-meme echouerait (ex. module absent).

    CORRECTIF : utilise `get_cloud_folder_name(audit)` (le meme nom de
    dossier lisible que celui utilise par `sharepoint_repository.save_audit`)
    et non `audit.meta.audit_id` brut, sinon les preuves atterrissent dans un
    dossier SharePoint different de celui contenant `audit.json`."""
    try:
        from repositories.sharepoint_repository import get_cloud_folder_name, upload_evidence_file

        folder_name = get_cloud_folder_name(audit)
        type_folder = TYPE_TO_FOLDER[type_preuve]
        relative_name = f"{type_folder}/{target_path.name}"
        return upload_evidence_file(folder_name, str(target_path), relative_name)
    except Exception:
        return None


def save_uploaded_file(
    audit: Audit,
    uploaded_file,
    type_preuve: TypePreuve,
    section: str | None = None,
    controle_id: str | None = None,
    legende: str | None = None,
    auteur: str | None = None,
) -> Preuve:
    audit_id = audit.meta.audit_id
    suffix = Path(uploaded_file.name).suffix.lower()
    preuve_id = str(uuid4())

    target_dir = get_evidence_type_dir(audit_id, type_preuve)

    data, suffix = _compress_image_if_possible(uploaded_file, suffix)
    target_path = target_dir / f"{preuve_id}{suffix}"

    with open(target_path, "wb") as f:
        f.write(data)

    # La copie locale est ecrite en premier (toujours disponible immediatement,
    # meme hors ligne). L'envoi cloud est une couche de securite en plus, pas
    # une dependance bloquante : si le reseau chantier est mauvais, l'upload
    # local reussit quand meme et la preuve est utilisable tout de suite.
    cloud_url = _try_cloud_backup(audit, type_preuve, target_path)

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
        cloud_url=cloud_url,
    )


def attach_preuve_to_audit(audit: Audit, preuve: Preuve) -> Audit:
    audit.preuves.append(preuve)
    return audit


def attach_preuve_to_constat(audit: Audit, controle_id: str, preuve_id: str) -> Audit:
    """Rattache une preuve a un point de controle.

    Correctifs par rapport a la version precedente :
    - le champ du modele `ConstatControle` s'appelle `preuve_ids` (et non
      `preuves_ids`) : l'ancien code plantait systematiquement des qu'on
      tentait de rattacher une preuve a un controle precis ;
    - le chemin du fichier est en plus recopie dans `constat.photos`, qui est
      le champ effectivement lu par la generation de rapport (DOCX/Markdown).
      Sans cela, une preuve ajoutee depuis la page "Preuves et annexes"
      n'apparaissait jamais dans le rapport final, seules les photos
      uploadees directement depuis la page "Controles techniques" l'etaient.
    """

    preuve = next((p for p in audit.preuves if p.preuve_id == preuve_id), None)

    for constat in audit.constats:
        if constat.controle_id != controle_id:
            continue

        if preuve_id not in constat.preuve_ids:
            constat.preuve_ids.append(preuve_id)

        if preuve is not None and preuve.fichier_path and preuve.fichier_path not in constat.photos:
            constat.photos.append(preuve.fichier_path)

        break

    return audit


def save_cover_photo(audit: Audit, uploaded_file) -> str:
    """Enregistre la photo de couverture choisie sur la page Dossier, pour
    la page de garde du rapport DOCX. Distincte des preuves de "Preuves et
    annexes" : c'est une image "vitrine" du site, pas une preuve d'un
    constat precis. Retourne le chemin local du fichier ecrit ; l'appelant
    est responsable de stocker ce chemin sur `audit.projet.photo_couverture_path`.

    Comme pour les preuves, tentative d'envoi cloud best-effort en plus de
    l'ecriture locale (voir `_try_cloud_backup`)."""
    audit_id = audit.meta.audit_id
    suffix = Path(uploaded_file.name).suffix.lower()

    target_dir = get_cover_photo_dir(audit_id)
    data, suffix = _compress_image_if_possible(uploaded_file, suffix)
    target_path = target_dir / f"couverture{suffix}"

    with open(target_path, "wb") as f:
        f.write(data)

    try:
        from repositories.sharepoint_repository import get_cloud_folder_name, upload_evidence_file

        folder_name = get_cloud_folder_name(audit)
        upload_evidence_file(folder_name, str(target_path), f"couverture/{target_path.name}")
    except Exception:
        pass

    return str(target_path)


def backup_control_evidence_file(audit: Audit, controle_id: str, local_path: str) -> str | None:
    """Envoi best-effort vers SharePoint d'un fichier de preuve ajoute depuis
    la page "Contrôles techniques" (`domain.control_service.append_uploaded_evidences`,
    qui n'ecrit que localement dans `data/evidences/{controle_id}/`).

    CORRECTIF : jusque-la, seules les preuves ajoutees depuis la page
    "Preuves et annexes" etaient sauvegardees dans le cloud ; celles ajoutees
    directement sur un point de controle restaient uniquement locales, donc
    perdues en cas de changement de machine/hebergement. Ne leve jamais
    d'exception (meme logique defensive que `_try_cloud_backup`)."""
    try:
        from repositories.sharepoint_repository import get_cloud_folder_name, upload_evidence_file

        folder_name = get_cloud_folder_name(audit)
        filename = Path(local_path).name
        relative_name = f"controles/{controle_id}/{filename}"
        return upload_evidence_file(folder_name, local_path, relative_name)
    except Exception:
        return None
