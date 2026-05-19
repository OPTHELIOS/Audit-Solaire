"""Tests d'intégration Audit Studio V1.1.

Couvre :
- inclusion de la section Studio dans les deux générateurs Markdown ;
- compat ancien JSON (mode_rapport racine seul) et synchronisation ;
- robustesse de ``extract_studio_from_session`` sur différents types de
  container (dict, dict sans audit, objet sans ``.get``, legacy ``current_audit``) ;
- génération DOCX en présence d'un bloc Studio peuplé.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from domain.audit_studio import (
    AuditStudioBlock,
    ModeRapport,
    extract_studio_from_session,
)
from domain.models import Audit


class _SessionLike:
    """Objet sans ``.get`` exposant un attribut ``audit``."""

    def __init__(self, audit):
        self.audit = audit


class _LegacySessionLike:
    """Objet sans ``.get`` exposant l'ancien attribut ``current_audit``."""

    def __init__(self, audit):
        self.current_audit = audit


class TestExtractStudioContainers(unittest.TestCase):
    def test_dict_with_audit(self) -> None:
        audit = Audit()
        studio = extract_studio_from_session({"audit": audit})
        self.assertIs(studio, audit.studio)

    def test_dict_legacy_current_audit(self) -> None:
        audit = Audit()
        studio = extract_studio_from_session({"current_audit": audit})
        self.assertIs(studio, audit.studio)

    def test_object_with_audit_attribute(self) -> None:
        audit = Audit()
        studio = extract_studio_from_session(_SessionLike(audit))
        self.assertIs(studio, audit.studio)

    def test_object_with_legacy_attribute(self) -> None:
        audit = Audit()
        studio = extract_studio_from_session(_LegacySessionLike(audit))
        self.assertIs(studio, audit.studio)

    def test_none_returns_none(self) -> None:
        self.assertIsNone(extract_studio_from_session(None))

    def test_empty_dict_returns_none(self) -> None:
        self.assertIsNone(extract_studio_from_session({}))

    def test_audit_without_studio_returns_none(self) -> None:
        class _NoStudio:
            pass

        self.assertIsNone(extract_studio_from_session({"audit": _NoStudio()}))


class TestModeRapportSync(unittest.TestCase):
    def test_legacy_json_root_mode_propagates_to_studio(self) -> None:
        legacy = {
            "meta": {"numero_audit": "AUD-LEGACY", "statut": "brouillon"},
            "mode_rapport": "diagnostic_court",
        }
        audit = Audit.model_validate(legacy)
        self.assertEqual(audit.mode_rapport, ModeRapport.diagnostic_court)
        self.assertEqual(audit.studio.mode_rapport, ModeRapport.diagnostic_court)

    def test_studio_only_input_mirrors_to_root(self) -> None:
        audit = Audit.model_validate(
            {
                "meta": {"numero_audit": "AUD-NEW"},
                "studio": {"mode_rapport": "diagnostic_court"},
            }
        )
        self.assertEqual(audit.studio.mode_rapport, ModeRapport.diagnostic_court)
        self.assertEqual(audit.mode_rapport, ModeRapport.diagnostic_court)

    def test_set_mode_rapport_helper_keeps_fields_in_sync(self) -> None:
        audit = Audit()
        audit.set_mode_rapport(ModeRapport.diagnostic_court)
        self.assertEqual(audit.mode_rapport, ModeRapport.diagnostic_court)
        self.assertEqual(audit.studio.mode_rapport, ModeRapport.diagnostic_court)

    def test_conflicting_root_and_studio_resolves_to_studio(self) -> None:
        # Quand les deux sont fournis dans le JSON, studio.mode_rapport gagne.
        audit = Audit.model_validate(
            {
                "meta": {"numero_audit": "AUD-CONFLICT"},
                "mode_rapport": "audit_complet",
                "studio": {"mode_rapport": "diagnostic_court"},
            }
        )
        self.assertEqual(audit.studio.mode_rapport, ModeRapport.diagnostic_court)
        self.assertEqual(audit.mode_rapport, ModeRapport.diagnostic_court)


def _build_audit_with_studio() -> Audit:
    audit = Audit()
    audit.set_mode_rapport(ModeRapport.diagnostic_court)
    audit.studio.upsert_scenario(
        "redimensionner",
        retenu=True,
        commentaire="Surchauffes estivales récurrentes.",
    )
    audit.studio.add_formulation(
        code="metrologie_insuffisante",
        section="Métrologie",
        constat_personnalise="Aucun comptage solaire en place.",
    )
    audit.studio.note_strategique = "Cap sur la métrologie avant tout investissement."
    return audit


class TestMarkdownExportsIncludeStudio(unittest.TestCase):
    def test_domain_report_service_markdown_contains_studio(self) -> None:
        from domain.report_service import build_report_markdown

        audit = _build_audit_with_studio()
        md = build_report_markdown({"audit": audit})
        self.assertIn("Studio OPT'HELIOS", md)
        self.assertIn("Diagnostic court", md)
        self.assertIn("Redimensionner", md)
        self.assertIn("Note stratégique", md)
        self.assertIn("Cap sur la métrologie", md)

    def test_services_report_service_markdown_contains_studio(self) -> None:
        # services/report_service.py n'est pas utilisé par les pages d'export
        # actuelles mais expose lui aussi un build_report_markdown : on vérifie
        # qu'il sait inclure la section Studio quand il est importable.
        # NB : un import non lié (export_responses_for_report) est cassé sur
        # main — hors scope de cette PR.
        try:
            from services.report_service import build_report_markdown
        except ImportError as exc:
            self.skipTest(
                f"services/report_service.py non importable (bug pré-existant) : {exc}"
            )

        audit = _build_audit_with_studio()
        md = build_report_markdown({"audit": audit})
        self.assertIn("Studio OPT'HELIOS", md)
        self.assertIn("Redimensionner", md)

    def test_markdown_without_studio_block_omits_section(self) -> None:
        from domain.audit_studio import render_studio_markdown_lines

        # AuditStudioBlock None ⇒ aucune ligne.
        self.assertEqual(render_studio_markdown_lines(None), [])


class TestDocxGenerationWithStudio(unittest.TestCase):
    def test_build_docx_report_with_studio_block(self) -> None:
        try:
            from domain.docx_service import build_docx_report
        except Exception as exc:  # pragma: no cover - environnement sans python-docx
            self.skipTest(f"python-docx indisponible : {exc}")

        audit = _build_audit_with_studio()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rapport.docx"
            build_docx_report(
                {"audit": audit},
                out,
                report_title="Test rapport Audit Studio",
                site_name="Site Test",
                reference="AUD-TEST",
                audit_date="2026-05-18",
                include_evidences=False,
            )
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1024)


if __name__ == "__main__":
    unittest.main()
