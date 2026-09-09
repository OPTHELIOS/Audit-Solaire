"""Tests de domain/performance_service.py : indicateurs de performance
FSAV/Prod/Taux (nomenclature SOCOL) et ratio réel/théorique (voir
CHANGES.md, section "Axes d'analyse réglementaire SOCOL/SOLO2018")."""

from domain.models import Audit, ReleveMesure, TypeMesure
from domain.performance_service import (
    compute_fsav,
    compute_performance_indicators,
    compute_productivite,
    compute_taux_auxiliaires,
    evaluate_ratio_reel_theorique,
    evaluate_taux_auxiliaires,
)
from domain.releves_catalog import (
    LIBELLE_CONSO_ELEC_AUX_PERIODE,
    LIBELLE_ENERGIE_APPOINT_PERIODE,
    LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
)


def test_compute_fsav_formule_iso_9488():
    # FSAV = QSTU / (QApp + QSTU)
    assert compute_fsav(9000, 6000) == 60.0


def test_compute_fsav_donnees_manquantes():
    assert compute_fsav(None, 6000) is None
    assert compute_fsav(9000, None) is None


def test_compute_productivite():
    assert compute_productivite(9000, 25) == 360.0
    assert compute_productivite(9000, None) is None
    assert compute_productivite(9000, 0) is None


def test_compute_taux_auxiliaires():
    assert compute_taux_auxiliaires(90, 9000) == 1.0
    assert compute_taux_auxiliaires(None, 9000) is None


def test_evaluate_taux_auxiliaires_seuil_socol_1_5_pct():
    assert evaluate_taux_auxiliaires(1.0).couleur is not None
    assert evaluate_taux_auxiliaires(1.0).valeur == 1.0
    # sous le seuil SOCOL -> statut favorable
    ok = evaluate_taux_auxiliaires(1.0)
    ko = evaluate_taux_auxiliaires(4.0)
    assert ok.couleur != ko.couleur


def test_evaluate_taux_auxiliaires_non_calculable():
    result = evaluate_taux_auxiliaires(None)
    assert result.valeur is None
    assert result.label == "Non calculable"


def test_evaluate_ratio_reel_theorique_bornes():
    conforme = evaluate_ratio_reel_theorique(95, 100, "Test")
    leger = evaluate_ratio_reel_theorique(80, 100, "Test")
    significatif = evaluate_ratio_reel_theorique(60, 100, "Test")
    majeur = evaluate_ratio_reel_theorique(30, 100, "Test")

    assert conforme.valeur == 0.95
    assert leger.valeur == 0.8
    assert significatif.valeur == 0.6
    assert majeur.valeur == 0.3
    # 4 statuts differents attendus sur ces 4 tranches
    assert len({conforme.couleur, leger.couleur, significatif.couleur, majeur.couleur}) == 4


def test_evaluate_ratio_reel_theorique_donnees_manquantes():
    result = evaluate_ratio_reel_theorique(None, 100, "Test")
    assert result.valeur is None
    result2 = evaluate_ratio_reel_theorique(50, None, "Test")
    assert result2.valeur is None
    result3 = evaluate_ratio_reel_theorique(50, 0, "Test")
    assert result3.valeur is None


def test_compute_performance_indicators_sans_releves_est_non_calculable():
    audit = Audit()
    indicators = compute_performance_indicators(audit)

    assert indicators["fsav_pct"] is None
    assert indicators["prod_kwh_m2_an"] is None
    assert indicators["taux_aux_pct"] is None


def test_compute_performance_indicators_avec_releves_complets():
    audit = Audit()
    audit.installation.champ_capteurs.surface_totale_m2 = 25.0
    audit.installation.dimensionnement.productible_theorique_kwh_m2_an = 400.0
    audit.installation.dimensionnement.taux_couverture_vise_pct = 60.0

    audit.releves.append(
        ReleveMesure(
            type_mesure=TypeMesure.energie,
            libelle=LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
            valeur=9000,
            unite="kWh",
        )
    )
    audit.releves.append(
        ReleveMesure(
            type_mesure=TypeMesure.energie,
            libelle=LIBELLE_ENERGIE_APPOINT_PERIODE,
            valeur=6000,
            unite="kWh",
        )
    )
    audit.releves.append(
        ReleveMesure(
            type_mesure=TypeMesure.energie,
            libelle=LIBELLE_CONSO_ELEC_AUX_PERIODE,
            valeur=90,
            unite="kWh",
        )
    )

    indicators = compute_performance_indicators(audit)

    assert indicators["fsav_pct"] == 60.0
    assert indicators["prod_kwh_m2_an"] == 360.0
    assert indicators["taux_aux_pct"] == 1.0
    assert indicators["prod_statut"].valeur is not None
    assert indicators["fsav_statut"].valeur is not None
    assert indicators["taux_statut"].valeur == 1.0


def test_compute_performance_indicators_prend_le_releve_le_plus_recent():
    # Si plusieurs relevés portent le même libellé (ex. plusieurs saisies au
    # fil de l'audit), le calcul doit se baser sur le plus récent, pas sur
    # le premier trouvé.
    from datetime import datetime, timedelta

    audit = Audit()
    ancien = ReleveMesure(
        type_mesure=TypeMesure.energie,
        libelle=LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
        valeur=1000,
        unite="kWh",
        date_mesure=datetime.now() - timedelta(days=10),
    )
    recent = ReleveMesure(
        type_mesure=TypeMesure.energie,
        libelle=LIBELLE_ENERGIE_SOLAIRE_UTILE_PERIODE,
        valeur=9000,
        unite="kWh",
        date_mesure=datetime.now(),
    )
    audit.releves.append(ancien)
    audit.releves.append(recent)

    indicators = compute_performance_indicators(audit)
    assert indicators["qstu_kwh"] == 9000
