"""Sauvegarde automatique (best-effort) du dossier d'audit en cours vers le
site SharePoint partage d'OPT'HELIOS.

Version app-only : contrairement a la premiere version de ce module (qui
s'appuyait sur une session OneDrive personnelle, disponible seulement si
l'auditeur s'etait deja connecte interactivement pendant la session en
cours), l'authentification "app-only" (`services/sharepoint_auth.py`) ne
depend d'aucune connexion utilisateur. Consequence : cette sauvegarde
automatique fonctionne des la premiere ouverture de l'appli, sur n'importe
quel appareil, tant que les secrets `microsoft_app` sont configures.

Toute erreur (secrets absents, reseau indisponible, permissions Azure AD
non accordees...) est avalee : l'autosave ne doit jamais faire planter une
page ni interrompre la saisie de l'auditeur. CORRECTIF (visibilite de
l'echec, sept. 2026 — retour utilisateur : reseau mobile faible en
chaufferie) : cette fonction renvoyait un simple bool, et le SEUL retour
utilisateur etait un toast affiche UNIQUEMENT en cas de succes. En cas
d'echec (reseau indisponible, ce qui est precisement le scenario "mauvaise
reception en chaufferie"), rien n'etait affiche : l'auditeur n'avait aucun
moyen de savoir que ses saisies ne partaient plus vers le cloud, avec un
risque de croire a tort que tout est sauvegarde. Le retour est desormais un
tri-etat (True = synchronise, False = cloud configure mais tentative
echouee, None = cloud non configure / rien a tenter) : voir `ui/state.py`
pour l'affichage (indicateur permanent dans la barre laterale + notification
uniquement sur changement d'etat, pour ne pas spammer de toasts d'echec
toutes les 20 secondes en zone blanche).
"""

from __future__ import annotations

from domain.models import Audit
from services.sharepoint_auth import is_configured


def try_autosave_to_cloud(audit: Audit) -> bool | None:
    """True = sauvegarde cloud reussie. False = cloud configure mais la
    tentative a echoue (reseau, permissions...). None = cloud non
    configure, aucune tentative faite."""
    if not is_configured():
        return None

    try:
        from repositories.sharepoint_repository import save_audit as save_audit_sharepoint

        save_audit_sharepoint(audit)
    except Exception:
        return False

    return True


def try_autosave_evidence_file(audit_id: str, local_path: str, relative_name: str) -> bool:
    """Pendant a `try_autosave_to_cloud`, mais pour un fichier de preuve deja
    ecrit localement (photo, PDF...). A appeler juste apres
    `services/evidence_service.save_uploaded_file`."""

    if not is_configured():
        return False

    try:
        from repositories.sharepoint_repository import upload_evidence_file

        url = upload_evidence_file(audit_id, local_path, relative_name)
        return url is not None
    except Exception:
        return False
