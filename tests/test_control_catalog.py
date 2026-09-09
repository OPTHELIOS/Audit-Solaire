"""Tests de domain/control_catalog.py : validité globale du catalogue et,
en particulier, des sous-contrôles de sécurité surchauffe/stagnation
détaillés (REG_005 à REG_008, voir CHANGES.md, section "Axes d'analyse
réglementaire SOCOL/SOLO2018")."""

from domain.control_catalog import CONTROL_CATALOG, validate_catalog


def test_catalog_is_valid():
    # Ne doit lever aucune ControlCatalogError (identifiants uniques,
    # prefixes autorises, coherence section/prefixe...).
    validate_catalog(CONTROL_CATALOG)


def _get(controle_id: str):
    item = next((i for i in CONTROL_CATALOG if i.controle_id == controle_id), None)
    assert item is not None, f"{controle_id} introuvable dans le catalogue"
    return item


def test_reg_005_a_008_couvrent_les_seuils_surchauffe_socol():
    reg_ids = sorted(i.controle_id for i in CONTROL_CATALOG if i.controle_id.startswith("REG_"))
    assert reg_ids == ["REG_001", "REG_002", "REG_003", "REG_004", "REG_005", "REG_006", "REG_007", "REG_008"]

    for controle_id in ("REG_005", "REG_006", "REG_007", "REG_008"):
        item = _get(controle_id)
        assert "surchauffe" in item.tags or "securite" in item.tags


def test_reg_006_et_008_conditionnes_au_systeme_sous_pression():
    # Le seuil de stagnation capteur et le vase d'expansion/soupape ne
    # concernent que les circuits primaires sous pression, pas les
    # installations autovidangeables (drain-back) — voir le commentaire de
    # REG_006/REG_008 dans domain/control_catalog.py.
    reg_006 = _get("REG_006")
    reg_008 = _get("REG_008")

    assert reg_006.condition_applicabilite == {"systeme_capteurs_in": ["sous_pression"]}
    assert reg_008.condition_applicabilite == {"systeme_capteurs_in": ["sous_pression"]}

    assert reg_006.is_applicable({"systeme_capteurs": "sous_pression"}) is True
    assert reg_006.is_applicable({"systeme_capteurs": "autovidangeable"}) is False


def test_reg_005_et_007_toujours_applicables():
    # Le seuil de bascule et les consignes de température concernent tous
    # les systèmes de capteurs, pas seulement les circuits sous pression.
    reg_005 = _get("REG_005")
    reg_007 = _get("REG_007")

    assert reg_005.condition_applicabilite is None
    assert reg_007.condition_applicabilite is None
