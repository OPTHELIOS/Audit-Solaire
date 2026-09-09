"""Tests de domain/socol_reference.py : rattachement de l'installation à la
nomenclature des schémas de référence SOCOL et bibliothèque associée (voir
CHANGES.md, section "Axes d'analyse réglementaire SOCOL/SOLO2018")."""

from pathlib import Path

from domain.socol_reference import SOCOL_SCHEMA_LIBRARY, get_schema_ref, suggest_schema_reference


def test_suggest_schema_reference_eau_technique_donne_ref3():
    assert suggest_schema_reference("sous_pression", "echangeur_externe", "eau_technique") == "REF3-SSC1"


def test_suggest_schema_reference_echangeur_immerge_donne_ref1_ssc2():
    assert suggest_schema_reference("sous_pression", "echangeur_immerge", "eau_sanitaire") == "REF1-SSC2"


def test_suggest_schema_reference_echangeur_externe_donne_ref1_ssc1():
    assert suggest_schema_reference("sous_pression", "echangeur_externe", "eau_sanitaire") == "REF1-SSC1"


def test_suggest_schema_reference_donnees_insuffisantes_rend_none():
    assert suggest_schema_reference(None, None, None) is None


def test_get_schema_ref_valeur_inconnue_ne_plante_pas():
    assert get_schema_ref("CODE_INEXISTANT") is None
    assert get_schema_ref(None) is None


def test_chaque_schema_de_la_bibliotheque_a_une_image_presente_sur_le_disque():
    # Regression : un code de la bibliothèque sans image associée sur le
    # disque ferait échouer silencieusement l'insertion dans le DOCX (voir
    # domain/docx_service.py::_add_schema_appendix, qui utilise
    # _add_picture_if_exists — pas d'exception, mais un rapport incomplet).
    assets_dir = Path("assets") / "schemas_socol"
    for code, schema in SOCOL_SCHEMA_LIBRARY.items():
        image_path = assets_dir / schema.image_filename
        assert image_path.exists(), f"Image manquante pour {code} : {image_path}"


def test_get_schema_ref_retourne_le_bon_libelle():
    schema = get_schema_ref("REF1-SSC1")
    assert schema is not None
    assert schema.code == "REF1-SSC1"
    assert "échangeur externe" in schema.libelle.lower()
    assert len(schema.points_vigilance) >= 1
