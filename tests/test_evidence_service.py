"""Tests de services/evidence_service.py : ecriture locale des preuves et
rattachement a un point de controle.

La sauvegarde cloud (SharePoint) est volontairement laissee "best effort" ici
(aucun secret configure dans l'environnement de test) : on verifie juste
qu'elle ne leve jamais d'exception, pas qu'elle reussit reellement (ca, seul
un test manuel avec un vrai site SharePoint configure peut le confirmer)."""

from pathlib import Path

from domain.control_catalog import CONTROL_CATALOG
from domain.control_service import get_or_create_constat
from domain.enums import TypePreuve
from domain.models import Audit, Preuve
from services.evidence_service import (
    attach_preuve_to_audit,
    attach_preuve_to_constat,
    save_uploaded_file,
)


class _FakeUploadedFile:
    def __init__(self, name: str, content: bytes = b"contenu de test"):
        self.name = name
        self._content = content

    def getbuffer(self):
        return self._content


def test_save_uploaded_file_writes_local_and_fills_preuve_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    audit = Audit()
    audit.projet.operation = "Site Test"

    preuve = save_uploaded_file(
        audit=audit,
        uploaded_file=_FakeUploadedFile("plaque.pdf"),
        type_preuve=TypePreuve.DOCUMENT,
        section="Documentation",
        controle_id=None,
        legende="Plaque signalétique",
        auteur="Auditeur test",
    )

    assert preuve.fichier_path is not None
    assert Path(preuve.fichier_path).exists()
    assert preuve.nom_original == "plaque.pdf"
    assert preuve.legende == "Plaque signalétique"
    # Sans secrets SharePoint configures dans l'environnement de test,
    # cloud_url doit rester None SANS lever d'exception (comportement
    # "best effort" attendu, voir services/evidence_service.py).
    assert preuve.cloud_url is None


def test_attach_preuve_to_constat_links_ids_and_photos():
    audit = Audit()
    item = CONTROL_CATALOG[0]
    constat = get_or_create_constat(audit, item)

    preuve = Preuve(fichier_path="/tmp/photo.jpg", controle_id=item.controle_id)
    audit = attach_preuve_to_audit(audit, preuve)
    audit = attach_preuve_to_constat(audit, item.controle_id, preuve.preuve_id)

    assert preuve.preuve_id in constat.preuve_ids
    assert "/tmp/photo.jpg" in constat.photos
