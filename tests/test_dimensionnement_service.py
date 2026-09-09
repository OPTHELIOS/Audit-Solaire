"""Tests de domain/dimensionnement_service.py : ratios de pré-dimensionnement
de contrôle de la fiche technique SOCOL 2021 (voir CHANGES.md)."""

from domain.dimensionnement_service import check_surface_vs_besoins, check_volume_stockage


def test_check_volume_stockage_sanitaire_dans_la_fourchette():
    # 25 m² x 80 l/m² = 2000 L, dans la fourchette SOCOL 75-100 l/m².
    result = check_volume_stockage(2000, 25, "eau_sanitaire")
    assert result.valeur == 80.0
    assert result.dans_la_plage is True


def test_check_volume_stockage_sanitaire_hors_fourchette():
    # 25 m² x 40 l/m² = 1000 L, hors fourchette 75-100 l/m².
    result = check_volume_stockage(1000, 25, "eau_sanitaire")
    assert result.valeur == 40.0
    assert result.dans_la_plage is False


def test_check_volume_stockage_eau_technique_minimum():
    result_ok = check_volume_stockage(1500, 25, "eau_technique")  # 60 l/m² >= 50
    assert result_ok.dans_la_plage is True

    result_ko = check_volume_stockage(1000, 25, "eau_technique")  # 40 l/m² < 50
    assert result_ko.dans_la_plage is False


def test_check_volume_stockage_donnees_manquantes():
    result = check_volume_stockage(None, 25, "eau_sanitaire")
    assert result.valeur is None
    assert result.dans_la_plage is None


def test_check_surface_vs_besoins_zone_centre_dans_la_fourchette():
    # 1500 L/j / 25 m² = 60 l/m², dans la fourchette centre 50-75 l/m².
    result = check_surface_vs_besoins(25, 1500, "centre")
    assert result.valeur == 60.0
    assert result.dans_la_plage is True


def test_check_surface_vs_besoins_zone_nord_hors_fourchette():
    # 1500 L/j / 25 m² = 60 l/m², hors fourchette nord 40-45 l/m².
    result = check_surface_vs_besoins(25, 1500, "nord")
    assert result.valeur == 60.0
    assert result.dans_la_plage is False


def test_check_surface_vs_besoins_zone_inconnue_rend_non_calculable():
    result = check_surface_vs_besoins(25, 1500, "zone_inexistante")
    assert result.valeur is None
    assert result.dans_la_plage is None
