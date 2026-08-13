"""Tests de domain/report_service.py : construction des donnees de rapport
et du rendu Markdown a partir d'un audit contenant au moins un ecart."""

from domain.control_service import get_applicable_controls, update_response
from domain.models import Audit
from domain.report_service import build_report_data, build_report_markdown


def _make_session_with_one_critical_finding():
    audit = Audit()
    session_state = {"audit": audit}
    controle_id = get_applicable_controls(audit)[0].controle_id

    update_response(
        session_state,
        controle_id,
        verdict="non_conforme",
        observation="Défaut constaté sur site",
        criticite_finale="critique",
        recommandation_personnalisee="Corriger le défaut sans délai",
    )
    return session_state


def test_build_report_data_contains_the_recorded_finding():
    session_state = _make_session_with_one_critical_finding()
    payload = build_report_data(session_state)

    assert payload["counts"]["total_findings"] >= 1
    assert payload["counts"]["critical_findings"] >= 1
    assert payload["global_assessment"]["statut_global"] == "défavorable"


def test_build_report_markdown_produces_non_empty_text():
    session_state = _make_session_with_one_critical_finding()
    markdown = build_report_markdown(session_state)

    assert "Rapport d" in markdown
    assert "Plan d" in markdown
    assert len(markdown) > 200
