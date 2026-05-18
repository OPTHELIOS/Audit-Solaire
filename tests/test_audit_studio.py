"""Tests minimaux pour le module OPT'HELIOS Audit Studio."""

from __future__ import annotations

import unittest

from domain.audit_studio import (
    FORMULATIONS_BY_CODE,
    FORMULATIONS_CATALOG,
    MODE_RAPPORT_LABELS,
    SCENARIOS_BY_CODE,
    SCENARIOS_CATALOG,
    AuditStudioBlock,
    ModeRapport,
    extract_studio_from_session,
    search_formulations,
)
from domain.models import Audit


EXPECTED_SCENARIO_CODES = {
    "conserver_optimiser",
    "rehabiliter_court_terme",
    "rehabiliter_lourdement",
    "redimensionner",
    "remplacer",
    "abandonner",
    "portefeuille_multi_batiments",
}

EXPECTED_FORMULATION_CODES = {
    "schema_hydraulique_incoherent",
    "surdimensionnement",
    "metrologie_insuffisante",
    "maintenance_insuffisante",
    "capteurs_integres_fabricant_disparu",
    "autovidangeable_recuperable",
    "sportive_peu_utilisee_ete",
    "diagnostic_multi_batiments",
    "corrosion_liaison_equipotentielle",
    "traceur_electrique",
}


class TestCatalogs(unittest.TestCase):
    def test_scenarios_present(self) -> None:
        codes = {sc.code for sc in SCENARIOS_CATALOG}
        self.assertEqual(codes, EXPECTED_SCENARIO_CODES)
        self.assertEqual(len(SCENARIOS_CATALOG), len(SCENARIOS_BY_CODE))

    def test_formulations_present(self) -> None:
        codes = {f.code for f in FORMULATIONS_CATALOG}
        self.assertEqual(codes, EXPECTED_FORMULATION_CODES)
        self.assertEqual(len(FORMULATIONS_CATALOG), len(FORMULATIONS_BY_CODE))

    def test_mode_rapport_labels_cover_enum(self) -> None:
        for mode in ModeRapport:
            self.assertIn(mode.value, MODE_RAPPORT_LABELS)

    def test_search_formulations_returns_all_when_empty(self) -> None:
        self.assertEqual(len(search_formulations("")), len(FORMULATIONS_CATALOG))

    def test_search_formulations_filters_on_keyword(self) -> None:
        matches = search_formulations("traceur")
        codes = [m.code for m in matches]
        self.assertIn("traceur_electrique", codes)
        self.assertGreaterEqual(len(matches), 1)


class TestStudioBlock(unittest.TestCase):
    def test_default_block_is_audit_complet(self) -> None:
        block = AuditStudioBlock()
        self.assertEqual(block.mode_rapport, ModeRapport.audit_complet)
        self.assertEqual(block.scenarios, [])
        self.assertEqual(block.formulations, [])

    def test_upsert_scenario_creates_then_updates(self) -> None:
        block = AuditStudioBlock()
        block.upsert_scenario("redimensionner", True, "Surchauffes répétées")
        self.assertEqual(len(block.scenarios), 1)
        self.assertTrue(block.scenarios[0].retenu)

        block.upsert_scenario("redimensionner", False, "Finalement non")
        self.assertEqual(len(block.scenarios), 1)
        self.assertFalse(block.scenarios[0].retenu)
        self.assertEqual(block.scenarios[0].commentaire, "Finalement non")

    def test_selected_scenarios_only_returns_retained(self) -> None:
        block = AuditStudioBlock()
        block.upsert_scenario("redimensionner", True)
        block.upsert_scenario("abandonner", False)
        retained = block.selected_scenarios()
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].code, "redimensionner")

    def test_add_and_remove_formulation(self) -> None:
        block = AuditStudioBlock()
        block.add_formulation(
            code="metrologie_insuffisante",
            section="Métrologie",
            constat_personnalise="Pas de comptage solaire en place.",
        )
        self.assertEqual(len(block.formulations), 1)
        block.remove_formulation(0)
        self.assertEqual(len(block.formulations), 0)


class TestAuditIntegration(unittest.TestCase):
    def test_audit_default_carries_studio_block(self) -> None:
        audit = Audit()
        self.assertIsInstance(audit.studio, AuditStudioBlock)
        self.assertEqual(audit.mode_rapport, ModeRapport.audit_complet)

    def test_audit_roundtrip_preserves_studio(self) -> None:
        audit = Audit()
        audit.studio.upsert_scenario("conserver_optimiser", True, "OK")
        audit.studio.add_formulation(code="surdimensionnement", section="Champ capteurs")
        audit.studio.note_strategique = "Note stratégique de test."

        dumped = audit.model_dump(mode="json")
        rebuilt = Audit.model_validate(dumped)

        self.assertEqual(len(rebuilt.studio.scenarios), 1)
        self.assertEqual(rebuilt.studio.scenarios[0].code, "conserver_optimiser")
        self.assertTrue(rebuilt.studio.scenarios[0].retenu)
        self.assertEqual(len(rebuilt.studio.formulations), 1)
        self.assertEqual(rebuilt.studio.formulations[0].code, "surdimensionnement")
        self.assertEqual(rebuilt.studio.note_strategique, "Note stratégique de test.")

    def test_legacy_audit_without_studio_still_loads(self) -> None:
        # Simule un JSON ancien : champ studio absent, champ mode_rapport absent.
        legacy = {
            "meta": {"numero_audit": "AUD-LEGACY", "statut": "brouillon"},
            "projet": {},
            "installation": {},
            "constats": [],
            "preuves": [],
            "synthese": {},
        }
        audit = Audit.model_validate(legacy)
        self.assertEqual(audit.mode_rapport, ModeRapport.audit_complet)
        self.assertIsInstance(audit.studio, AuditStudioBlock)

    def test_extract_studio_from_session_handles_missing_audit(self) -> None:
        self.assertIsNone(extract_studio_from_session({}))
        self.assertIsNone(extract_studio_from_session({"audit": None}))

    def test_extract_studio_from_session_returns_block(self) -> None:
        audit = Audit()
        studio = extract_studio_from_session({"audit": audit})
        self.assertIs(studio, audit.studio)


if __name__ == "__main__":
    unittest.main()
