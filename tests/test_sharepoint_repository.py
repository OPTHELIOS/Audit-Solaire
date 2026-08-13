"""Tests de repositories/sharepoint_repository.py.

Volontairement limites a la logique PURE (calcul du nom de dossier, slug) :
les fonctions qui appellent reellement l'API Graph (`save_audit`,
`load_audit`, `upload_evidence_file`) necessitent soit un vrai site
SharePoint configure, soit un mock HTTP complet, ce qui deborderait du cadre
d'un test unitaire simple. Ces fonctions-la restent verifiees manuellement
via l'application (voir CHANGES.md)."""

from domain.models import Audit
from repositories.sharepoint_repository import _slugify, get_cloud_folder_name


def test_slugify_strips_special_characters():
    result = _slugify("Résidence Les Tilleuls (Bât. C)!!")
    assert " " not in result
    assert "(" not in result
    assert ")" not in result
    assert "!" not in result


def test_slugify_empty_falls_back_to_audit():
    assert _slugify("") == "audit"
    assert _slugify("   ") == "audit"


def test_get_cloud_folder_name_is_computed_once_and_stable():
    audit = Audit()
    audit.projet.operation = "Résidence Les Tilleuls"

    folder1 = get_cloud_folder_name(audit)
    assert folder1.endswith(audit.meta.audit_id[:8])
    assert audit.meta.dossier_cloud == folder1

    # Modifier le nom d'operation APRES le premier calcul ne doit rien
    # changer : le dossier SharePoint doit rester stable pour la vie de
    # l'audit, sinon les preuves et le JSON finissent dans des dossiers
    # differents au fil des sauvegardes.
    audit.projet.operation = "Autre nom"
    folder2 = get_cloud_folder_name(audit)
    assert folder2 == folder1


def test_get_cloud_folder_name_falls_back_to_commune_then_generic():
    audit = Audit()
    audit.projet.adresse.commune = "Grand-Champ"
    folder = get_cloud_folder_name(audit)
    assert folder.lower().startswith("grand-champ")

    audit2 = Audit()
    folder2 = get_cloud_folder_name(audit2)
    assert folder2.startswith("audit-")
