"""Tests unitaires pour le module domain.energy."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from domain.energy import (
    COUVERTURE_MAX,
    COUVERTURE_MIN,
    PRODUCTIBLE_INDICATIF_DEFAUT,
    PRODUCTIBLE_INDICATIF_ZONES,
    RATIO_STOCKAGE_MAX_LM2,
    RATIO_STOCKAGE_MIN_LM2,
    EnergyInputs,
    compute_energy,
    energie_ecs_annuelle_kwh,
    evaluer_redimensionnement,
    format_results_markdown,
    inputs_have_payload,
    productible_retenu_kwh_m2_an,
    productivite_kwh_m2_an,
    ratio_stockage_l_m2,
    taux_couverture,
)
from domain.models import Audit, EnergyBlock


class TestEnergieECS(unittest.TestCase):
    def test_returns_none_when_inputs_missing(self) -> None:
        self.assertIsNone(energie_ecs_annuelle_kwh(None, 40))
        self.assertIsNone(energie_ecs_annuelle_kwh(1000, None))

    def test_zero_volume_returns_zero(self) -> None:
        self.assertEqual(energie_ecs_annuelle_kwh(0, 40), 0.0)
        self.assertEqual(energie_ecs_annuelle_kwh(1000, 0), 0.0)

    def test_classic_case_matches_formula(self) -> None:
        # 1000 L/jour * 40 K * 365 jours * 4.186 / 3600
        v = 1000.0
        dt = 40.0
        expected_kwh = round(1.0 * 4.186 * v * dt * 365 / 3600, 1)
        self.assertAlmostEqual(
            energie_ecs_annuelle_kwh(v, dt),
            expected_kwh,
            places=1,
        )

    def test_partial_year_reduces_energy(self) -> None:
        full = energie_ecs_annuelle_kwh(1000, 40, jours=365)
        half = energie_ecs_annuelle_kwh(1000, 40, jours=183)
        self.assertIsNotNone(full)
        self.assertIsNotNone(half)
        assert full is not None and half is not None  # type narrowing
        self.assertLess(half, full)


class TestProductible(unittest.TestCase):
    def test_explicit_value_wins(self) -> None:
        self.assertEqual(
            productible_retenu_kwh_m2_an(500.0, "H1"),
            500.0,
        )

    def test_zone_lookup(self) -> None:
        self.assertEqual(
            productible_retenu_kwh_m2_an(None, "H3"),
            PRODUCTIBLE_INDICATIF_ZONES["H3"],
        )
        self.assertEqual(
            productible_retenu_kwh_m2_an(None, "h1"),
            PRODUCTIBLE_INDICATIF_ZONES["H1"],
        )

    def test_default_when_unknown(self) -> None:
        self.assertEqual(
            productible_retenu_kwh_m2_an(None, "ZZ"),
            PRODUCTIBLE_INDICATIF_DEFAUT,
        )
        self.assertEqual(
            productible_retenu_kwh_m2_an(None, None),
            PRODUCTIBLE_INDICATIF_DEFAUT,
        )


class TestProductiviteEtRatios(unittest.TestCase):
    def test_productivite_basic(self) -> None:
        self.assertEqual(productivite_kwh_m2_an(4000.0, 10.0), 400.0)

    def test_productivite_zero_surface(self) -> None:
        self.assertIsNone(productivite_kwh_m2_an(4000.0, 0))
        self.assertIsNone(productivite_kwh_m2_an(4000.0, None))
        self.assertIsNone(productivite_kwh_m2_an(None, 10.0))

    def test_taux_couverture(self) -> None:
        self.assertAlmostEqual(taux_couverture(2500, 10000), 0.25, places=2)

    def test_taux_couverture_zero_ecs(self) -> None:
        self.assertIsNone(taux_couverture(2500, 0))
        self.assertIsNone(taux_couverture(None, 1000))

    def test_ratio_stockage(self) -> None:
        self.assertEqual(ratio_stockage_l_m2(1000.0, 15.0), 66.7)
        self.assertIsNone(ratio_stockage_l_m2(None, 10))
        self.assertIsNone(ratio_stockage_l_m2(500, 0))


class TestRedimensionnement(unittest.TestCase):
    def test_balanced(self) -> None:
        label, msgs = evaluer_redimensionnement(
            (COUVERTURE_MIN + COUVERTURE_MAX) / 2,
            (RATIO_STOCKAGE_MIN_LM2 + RATIO_STOCKAGE_MAX_LM2) / 2,
        )
        self.assertEqual(label, "équilibré")
        self.assertTrue(any("cohérent" in m for m in msgs))

    def test_oversized(self) -> None:
        label, msgs = evaluer_redimensionnement(COUVERTURE_MAX + 0.2, 70.0)
        self.assertEqual(label, "surdimensionné")
        self.assertTrue(any("surchauffe" in m for m in msgs))

    def test_undersized(self) -> None:
        label, _ = evaluer_redimensionnement(COUVERTURE_MIN - 0.05, 70.0)
        self.assertEqual(label, "sous-dimensionné")

    def test_storage_too_low(self) -> None:
        label, msgs = evaluer_redimensionnement(0.4, RATIO_STOCKAGE_MIN_LM2 - 10)
        # base label was équilibré, downgraded for stockage trop bas
        self.assertEqual(label, "stockage à augmenter")
        self.assertTrue(any("L/m²" in m for m in msgs))

    def test_storage_too_high(self) -> None:
        label, _ = evaluer_redimensionnement(0.4, RATIO_STOCKAGE_MAX_LM2 + 30)
        self.assertEqual(label, "stockage à réduire")

    def test_missing_data_indetermine(self) -> None:
        label, msgs = evaluer_redimensionnement(None, None)
        self.assertEqual(label, "indeterminé")
        self.assertGreaterEqual(len(msgs), 2)


class TestComputeEnergyEndToEnd(unittest.TestCase):
    def test_typical_collectif(self) -> None:
        inputs = EnergyInputs(
            volume_ecs_jour_litres=2000,
            delta_t_kelvin=40,
            surface_capteurs_m2=30,
            volume_stockage_solaire_litres=2000,
            zone_climatique="H2",
        )
        results = compute_energy(inputs)
        self.assertIsNotNone(results.energie_ecs_kwh_an)
        self.assertIsNotNone(results.productivite_kwh_m2_an)
        self.assertIsNotNone(results.taux_couverture)
        self.assertEqual(results.ratio_stockage_l_m2, round(2000 / 30, 1))
        self.assertTrue(results.proposition_redimensionnement)
        self.assertGreaterEqual(len(results.messages), 1)

    def test_partial_inputs_dont_crash(self) -> None:
        results = compute_energy(EnergyInputs())
        self.assertIsNone(results.energie_ecs_kwh_an)
        self.assertIsNone(results.productivite_kwh_m2_an)
        self.assertEqual(results.proposition_redimensionnement, "indeterminé")

    def test_format_markdown_contains_keywords(self) -> None:
        inputs = EnergyInputs(
            volume_ecs_jour_litres=2000,
            delta_t_kelvin=40,
            surface_capteurs_m2=30,
            volume_stockage_solaire_litres=2000,
            zone_climatique="H2",
        )
        lines = format_results_markdown(compute_energy(inputs))
        joined = "\n".join(lines)
        self.assertIn("Énergie ECS annuelle", joined)
        self.assertIn("Taux de couverture", joined)
        self.assertIn("Ratio stockage", joined)


class TestEnergyAuditIntegration(unittest.TestCase):
    def test_audit_default_carries_energy_block(self) -> None:
        audit = Audit()
        self.assertIsInstance(audit.energy, EnergyBlock)
        self.assertIsNone(audit.energy.results)

    def test_legacy_json_without_energy_block(self) -> None:
        legacy = {
            "meta": {"numero_audit": "AUD-LEGACY", "statut": "brouillon"},
            "projet": {},
            "installation": {},
            "constats": [],
            "preuves": [],
            "synthese": {},
        }
        audit = Audit.model_validate(legacy)
        self.assertIsInstance(audit.energy, EnergyBlock)

    def test_audit_roundtrip_preserves_energy(self) -> None:
        audit = Audit()
        audit.energy.inputs.volume_ecs_jour_litres = 1500
        audit.energy.inputs.delta_t_kelvin = 35
        audit.energy.inputs.surface_capteurs_m2 = 25
        audit.energy.results = compute_energy(audit.energy.inputs)

        dumped = audit.model_dump(mode="json")
        rebuilt = Audit.model_validate(dumped)

        self.assertEqual(rebuilt.energy.inputs.volume_ecs_jour_litres, 1500)
        self.assertIsNotNone(rebuilt.energy.results)
        assert rebuilt.energy.results is not None  # type narrowing
        self.assertIsNotNone(rebuilt.energy.results.energie_ecs_kwh_an)


class TestEnergyInputsBounds(unittest.TestCase):
    def test_rendement_must_be_within_zero_one(self) -> None:
        EnergyInputs(rendement_utile=0.0)
        EnergyInputs(rendement_utile=1.0)
        with self.assertRaises(ValidationError):
            EnergyInputs(rendement_utile=1.5)
        with self.assertRaises(ValidationError):
            EnergyInputs(rendement_utile=-0.1)

    def test_delta_t_within_zero_hundred(self) -> None:
        EnergyInputs(delta_t_kelvin=0)
        EnergyInputs(delta_t_kelvin=100)
        with self.assertRaises(ValidationError):
            EnergyInputs(delta_t_kelvin=150)
        with self.assertRaises(ValidationError):
            EnergyInputs(delta_t_kelvin=-1)

    def test_jours_within_zero_366(self) -> None:
        EnergyInputs(jours_fonctionnement=0)
        EnergyInputs(jours_fonctionnement=366)
        with self.assertRaises(ValidationError):
            EnergyInputs(jours_fonctionnement=400)
        with self.assertRaises(ValidationError):
            EnergyInputs(jours_fonctionnement=-1)

    def test_volumes_and_surface_must_be_non_negative(self) -> None:
        with self.assertRaises(ValidationError):
            EnergyInputs(volume_ecs_jour_litres=-10)
        with self.assertRaises(ValidationError):
            EnergyInputs(surface_capteurs_m2=-1)
        with self.assertRaises(ValidationError):
            EnergyInputs(volume_stockage_solaire_litres=-50)
        with self.assertRaises(ValidationError):
            EnergyInputs(productible_indicatif_kwh_m2_an=-1)


class TestCoverageOverOneHundred(unittest.TestCase):
    def test_label_incoherent_above_100_percent(self) -> None:
        label, msgs = evaluer_redimensionnement(1.5, 70.0)
        self.assertEqual(label, "incoherent")
        self.assertTrue(any("100" in m and "vérifier" in m.lower() for m in msgs))

    def test_markdown_flags_over_100_percent(self) -> None:
        inputs = EnergyInputs(
            volume_ecs_jour_litres=100,
            delta_t_kelvin=40,
            surface_capteurs_m2=200,  # surface absurdement grande -> couverture > 100%
            zone_climatique="H3",
        )
        results = compute_energy(inputs)
        self.assertIsNotNone(results.taux_couverture)
        assert results.taux_couverture is not None
        self.assertGreater(results.taux_couverture, 1.0)
        lines = format_results_markdown(results)
        joined = "\n".join(lines)
        self.assertIn("> 100", joined)
        self.assertIn("vérifier", joined.lower())

    def test_label_stays_oversized_just_above_max(self) -> None:
        # Au-dessus de COUVERTURE_MAX mais sous 100 % -> garde surdimensionné
        label, _ = evaluer_redimensionnement(0.75, 70.0)
        self.assertEqual(label, "surdimensionné")


class TestInputsHavePayload(unittest.TestCase):
    def test_empty_inputs_is_no_payload(self) -> None:
        self.assertFalse(inputs_have_payload(EnergyInputs()))

    def test_volume_alone_counts_as_payload(self) -> None:
        self.assertTrue(inputs_have_payload(EnergyInputs(volume_ecs_jour_litres=500)))

    def test_surface_alone_counts_as_payload(self) -> None:
        self.assertTrue(inputs_have_payload(EnergyInputs(surface_capteurs_m2=10)))

    def test_none_inputs(self) -> None:
        self.assertFalse(inputs_have_payload(None))


if __name__ == "__main__":
    unittest.main()
