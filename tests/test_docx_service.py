"""Tests de domain/docx_service.py : génération du rapport DOCX et de la
checklist terrain avec la charte graphique OPT'HELIOS (voir CHANGES.md).

Couvre en particulier :
- le rapport se génère sans erreur avec un audit contenant plusieurs
  criticités, dont "information" (voir le bug corrigé sur ce niveau,
  tests/test_models.py) ;
- le logo officiel OPT'HELIOS existe bien à l'emplacement attendu (il
  était absent du dépôt jusqu'ici, ce qui faisait que ni le rapport ni la
  barre latérale de l'appli n'affichaient de logo) ;
- le module de style expose bien les couleurs de la charte.
"""

from pathlib import Path

from domain.control_service import get_applicable_controls, update_response
from domain.docx_service import LOGO_PATH, build_checklist_docx, build_docx_report
from domain.models import Audit
import domain.opthelios_style as opthelios_style


def _make_session_with_varied_findings():
    audit = Audit()
    session_state = {"audit": audit}
    controls = get_applicable_controls(audit)

    criticites = ["critique", "majeure", "mineure", "information"]
    for item, criticite in zip(controls[:4], criticites):
        update_response(
            session_state,
            item.controle_id,
            verdict="non_conforme",
            observation="Défaut constaté sur site",
            criticite_finale=criticite,
        )
    return session_state


def test_logo_officiel_present_dans_le_depot():
    # Regression : ce fichier etait absent (voir CHANGES.md), si bien que
    # ni le rapport DOCX ni la barre laterale Streamlit (app.py) n'avaient
    # de logo — un des points signales par l'utilisateur.
    assert Path(LOGO_PATH).exists(), (
        f"Logo OPT'HELIOS manquant a {LOGO_PATH} : le rapport et la barre "
        "laterale de l'appli n'afficheront aucun logo."
    )


def test_build_docx_report_generates_a_file(tmp_path):
    session_state = _make_session_with_varied_findings()
    output_path = tmp_path / "rapport.docx"

    result = build_docx_report(
        session_state,
        output_path,
        site_name="Site de test",
        reference="AUD-TEST-0001",
        audit_date="01/09/2026",
    )

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_build_checklist_docx_generates_a_file(tmp_path):
    audit = Audit()
    audit.projet.operation = "Site de test"
    output_path = tmp_path / "checklist.docx"

    result = build_checklist_docx(audit, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_style_module_exposes_charte_colors():
    # Codes exacts de la charte OPT'HELIOS (voir compétence
    # opthelios-notes-techniques) : verrouille ces valeurs pour éviter
    # qu'elles dérivent silencieusement d'un futur refactoring.
    assert opthelios_style.NAVY == "1C1E3D"
    assert opthelios_style.GOLD == "F9B13A"
    assert opthelios_style.SKY == "8FC4E4"
    assert opthelios_style.CREAM == "FAEAB6"


def test_status_badge_covers_every_verdict_and_criticite_value():
    # Regression : le code couleur feu tricolore (demande utilisateur,
    # sept. 2026) doit couvrir TOUTES les valeurs reellement produites par
    # domain/models.py::VerdictControle et Criticite (dont "information",
    # cf. le bug corrige sur ce niveau) — une valeur manquante dans les
    # dicts de couleurs ne doit pas faire planter le rapport (repli gris
    # neutre) mais on verrouille ici la couverture complete plutot que de
    # compter sur le repli.
    from domain.control_catalog import Criticite as CatalogueCriticite
    from domain.models import VerdictControle

    for verdict in VerdictControle:
        assert verdict.value in opthelios_style.VERDICT_COLORS
        assert verdict.value in opthelios_style.VERDICT_LABELS

    for criticite in CatalogueCriticite:
        assert criticite.value in opthelios_style.CRITICITE_COLORS
        assert criticite.value in opthelios_style.CRITICITE_LABELS


def test_add_status_badge_does_not_crash_on_unknown_value():
    from docx import Document

    document = Document()
    p = document.add_paragraph()
    opthelios_style.add_status_badge(p, "valeur_inconnue", kind="verdict")
    assert "valeur_inconnue" in p.text


def test_build_docx_report_sans_donnees_socol_ne_plante_pas(tmp_path):
    # Regression : un audit sans dimensionnement ni schéma de référence
    # SOCOL renseigné (cas de la grande majorité des audits existants avant
    # cette fonctionnalité) doit toujours générer un rapport complet, avec
    # les sections 8/9 présentes mais informatives plutôt que vides/en erreur.
    session_state = _make_session_with_varied_findings()
    output_path = tmp_path / "rapport_sans_socol.docx"

    result = build_docx_report(session_state, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_build_docx_report_avec_dimensionnement_et_schema_socol(tmp_path):
    # Couvre le chemin complet : dimensionnement renseigné + relevés
    # d'énergie sur la période + schéma de référence SOCOL rattaché (voir
    # CHANGES.md, section "Axes d'analyse réglementaire SOCOL/SOLO2018").
    from domain.models import ReleveMesure, TypeMesure
    from domain.releves_catalog import (
        LIBELLE_CONSO_ELEC_AUX_PERIODE,
        LIBELLE_ENERGIE_APPOINT_PERIODE,
        LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
    )

    session_state = _make_session_with_varied_findings()
    audit = session_state["audit"]

    audit.installation.champ_capteurs.surface_totale_m2 = 25.0
    audit.installation.classification.schema_reference_socol = "REF1-SSC1"
    audit.installation.dimensionnement.zone_climatique = "centre"
    audit.installation.dimensionnement.besoins_ecs_l_jour = 1500.0
    audit.installation.dimensionnement.taux_couverture_vise_pct = 55.0
    audit.installation.dimensionnement.productible_theorique_kwh_m2_an = 400.0
    audit.installation.dimensionnement.source_etude = "Note SOLO2018 - test"

    audit.releves.append(
        ReleveMesure(type_mesure=TypeMesure.energie, libelle=LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE, valeur=9000, unite="kWh")
    )
    audit.releves.append(
        ReleveMesure(type_mesure=TypeMesure.energie, libelle=LIBELLE_ENERGIE_APPOINT_PERIODE, valeur=6000, unite="kWh")
    )
    audit.releves.append(
        ReleveMesure(type_mesure=TypeMesure.energie, libelle=LIBELLE_CONSO_ELEC_AUX_PERIODE, valeur=90, unite="kWh")
    )

    output_path = tmp_path / "rapport_avec_socol.docx"
    result = build_docx_report(session_state, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
