"""Tests du modele de donnees (domain/models.py).

Couvre en particulier les points qui ont deja cause des bugs par le passe :
- `AuditMeta.audit_id` doit toujours exister (sinon tout ajout de preuve
  plante, voir CHANGES.md) ;
- `Preuve` doit accepter les champs reellement envoyes par
  `services/evidence_service.py` ;
- `ConstatControle.preuve_ids` (pas `preuves_ids`).
"""

from domain.models import Audit, ConstatControle, Preuve


def test_audit_default_creation():
    audit = Audit()
    assert audit.meta.audit_id
    assert audit.meta.dossier_cloud is None
    assert audit.meta.numero_audit.startswith("AUD-")
    assert audit.constats == []
    assert audit.preuves == []


def test_audit_id_is_unique_per_instance():
    a1, a2 = Audit(), Audit()
    assert a1.meta.audit_id != a2.meta.audit_id


def test_preuve_accepts_fields_used_by_evidence_service():
    preuve = Preuve(
        fichier_path="/tmp/x.jpg",
        nom_original="x.jpg",
        section="Hydraulique",
        controle_id="HYD_001",
        legende="Test",
        auteur="Auditeur",
    )
    assert preuve.fichier_path == "/tmp/x.jpg"
    assert preuve.nom_original == "x.jpg"
    assert preuve.cloud_url is None


def test_constat_controle_preuve_ids_field_name():
    constat = ConstatControle(controle_id="X", section="S", libelle="L")
    assert constat.preuve_ids == []
    constat.preuve_ids.append("PRV-1")
    assert "PRV-1" in constat.preuve_ids


def test_audit_json_roundtrip():
    audit = Audit()
    audit.projet.operation = "Test Site"

    payload = audit.model_dump(mode="json")
    reloaded = Audit.model_validate(payload)

    assert reloaded.meta.audit_id == audit.meta.audit_id
    assert reloaded.projet.operation == "Test Site"
