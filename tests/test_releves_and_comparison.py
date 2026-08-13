"""Tests de services/releves_service.py (relevés de mesure) et
services/comparison_service.py (comparaison avec un audit antérieur)."""

from domain.control_service import get_applicable_controls, update_response
from domain.models import Audit
from services.comparison_service import compare_audits
from services.releves_service import add_releve, list_releves_sorted, remove_releve


def test_add_and_remove_releve():
    audit = Audit()

    releve1 = add_releve(
        audit,
        libelle="Température départ capteurs",
        valeur=68.5,
        unite="°C",
        type_mesure="temperature",
    )
    add_releve(audit, libelle="Pression circuit primaire", valeur=1.8, unite="bar", type_mesure="pression")

    assert len(audit.releves) == 2
    assert list_releves_sorted(audit)[0].releve_id in {r.releve_id for r in audit.releves}

    removed = remove_releve(audit, releve1.releve_id)
    assert removed is True
    assert len(audit.releves) == 1
    assert audit.releves[0].libelle == "Pression circuit primaire"


def test_releves_survive_json_roundtrip():
    audit = Audit()
    add_releve(audit, libelle="Débit primaire", valeur=12.0, unite="L/min", type_mesure="debit")

    payload = audit.model_dump(mode="json")
    reloaded = Audit.model_validate(payload)

    assert len(reloaded.releves) == 1
    assert reloaded.releves[0].libelle == "Débit primaire"
    assert reloaded.releves[0].valeur == 12.0


def test_compare_audits_reports_deltas_on_indicators_and_measures():
    current = Audit()
    current.projet.operation = "Site A"
    previous = Audit()
    previous.projet.operation = "Site A"
    previous.meta.numero_audit = "AUD-OLD-001"

    controle_id = get_applicable_controls(current)[0].controle_id
    update_response({"audit": current}, controle_id, verdict="non_conforme", criticite_finale="critique")

    controle_id_prev = get_applicable_controls(previous)[0].controle_id
    update_response({"audit": previous}, controle_id_prev, verdict="conforme", criticite_finale="mineure")

    add_releve(current, libelle="Température départ capteurs", valeur=70.0, unite="°C")
    add_releve(previous, libelle="Température départ capteurs", valeur=65.0, unite="°C")
    add_releve(current, libelle="Mesure seulement côté actuel", valeur=1.0, unite="x")

    result = compare_audits(current, previous)

    critical_row = next(
        row for row in result["audit_indicators"] if row["indicateur"] == "Non-conformités critiques"
    )
    assert critical_row["actuel"] == 1
    assert critical_row["precedent"] == 0
    assert critical_row["ecart"] == 1

    # Un seul relevé est présent dans les DEUX audits (même libellé) : c'est
    # le seul qui doit apparaître dans la comparaison, l'autre (présent
    # seulement côté "current") ne doit pas y figurer.
    assert len(result["measure_indicators"]) == 1
    measure = result["measure_indicators"][0]
    assert measure["indicateur"] == "Température départ capteurs"
    assert measure["ecart"] == 5.0

    assert result["previous_meta"]["numero_audit"] == "AUD-OLD-001"


def test_compare_audits_with_no_common_measures():
    current = Audit()
    previous = Audit()
    add_releve(current, libelle="Mesure A", valeur=1.0, unite="x")
    add_releve(previous, libelle="Mesure B", valeur=2.0, unite="x")

    result = compare_audits(current, previous)
    assert result["measure_indicators"] == []
