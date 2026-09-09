"""Tests du modele de donnees (domain/models.py).

Couvre en particulier les points qui ont deja cause des bugs par le passe :
- `AuditMeta.audit_id` doit toujours exister (sinon tout ajout de preuve
  plante, voir CHANGES.md) ;
- `Preuve` doit accepter les champs reellement envoyes par
  `services/evidence_service.py` ;
- `ConstatControle.preuve_ids` (pas `preuves_ids`).
"""

from domain.models import Audit, ConstatControle, Criticite, Preuve


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


def test_criticite_information_survives_json_roundtrip():
    # Regression : domain/control_catalog.py::Criticite (utilise par le
    # selecteur "Criticite retenue" de la page Controles techniques) propose
    # 4 niveaux dont "information", mais domain.models.Criticite n'en avait
    # que 3. Un point marque "Information" s'enregistrait en session sans
    # erreur (assignation Python non validee) puis devenait impossible a
    # recharger via Audit.model_validate(). Voir CHANGES.md.
    audit = Audit()
    audit.constats.append(
        ConstatControle(
            controle_id="X",
            section="S",
            libelle="L",
            criticite=Criticite.information,
            criticite_finale=Criticite.information,
        )
    )

    payload = audit.model_dump(mode="json")
    reloaded = Audit.model_validate(payload)

    assert reloaded.constats[0].criticite == Criticite.information
    assert reloaded.constats[0].criticite_finale == Criticite.information


def test_dimensionnement_et_schema_reference_socol_survivent_au_roundtrip():
    # AJOUT (sept. 2026, axes d'analyse réglementaire SOCOL/SOLO2018, voir
    # CHANGES.md) : Installation.dimensionnement et
    # ClassificationInstallation.schema_reference_socol sont de nouveaux
    # champs — vérifie qu'ils survivent bien à un cycle JSON complet, comme
    # le reste du modèle (voir le bug historique sur Criticite ci-dessus).
    audit = Audit()
    audit.installation.classification.schema_reference_socol = "REF1-SSC1"
    audit.installation.dimensionnement.zone_climatique = "centre"
    audit.installation.dimensionnement.besoins_ecs_l_jour = 1500.0
    audit.installation.dimensionnement.taux_couverture_vise_pct = 55.0
    audit.installation.dimensionnement.productible_theorique_kwh_m2_an = 400.0
    audit.installation.dimensionnement.surface_capteurs_etude_m2 = 25.0
    audit.installation.dimensionnement.source_etude = "Note SOLO2018 - test"

    payload = audit.model_dump(mode="json")
    reloaded = Audit.model_validate(payload)

    assert reloaded.installation.classification.schema_reference_socol == "REF1-SSC1"
    assert reloaded.installation.dimensionnement.zone_climatique == "centre"
    assert reloaded.installation.dimensionnement.besoins_ecs_l_jour == 1500.0
    assert reloaded.installation.dimensionnement.taux_couverture_vise_pct == 55.0
    assert reloaded.installation.dimensionnement.productible_theorique_kwh_m2_an == 400.0
    assert reloaded.installation.dimensionnement.surface_capteurs_etude_m2 == 25.0
    assert reloaded.installation.dimensionnement.source_etude == "Note SOLO2018 - test"


def test_dimensionnement_absent_par_defaut():
    audit = Audit()
    assert audit.installation.dimensionnement.zone_climatique is None
    assert audit.installation.classification.schema_reference_socol is None
