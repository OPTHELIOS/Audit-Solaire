"""Comparaison d'un audit avec un audit antérieur du même site : indicateurs
de conformité/complétion et relevés de mesure communs (rapprochés par
libellé). Lecture seule : ne modifie ni ne sauvegarde aucun des deux audits.
"""

from __future__ import annotations

from typing import Any

from domain.control_service import summarize_controls
from domain.models import Audit


def _context_from_installation(installation: Any) -> dict[str, Any]:
    classification = installation.classification
    return {
        "systeme_capteurs": classification.systeme_capteurs,
        "type_echangeur": classification.type_echangeur,
        "type_stockage_solaire": classification.type_stockage,
        "type_comptage": classification.type_comptage or [],
        "requires_monitoring": bool(
            installation.telegestion_presente or installation.equipements.compteur_energie
        ),
        "requires_telecontrole": bool(installation.telegestion_presente),
    }


def _summary_for_audit(audit: Audit) -> dict[str, Any]:
    # `summarize_controls` attend un objet "session_state"-like avec une clé
    # "audit" ; on lui fournit un dict minimal, il n'y a pas de vraie session
    # Streamlit pour l'audit antérieur (juste chargé en mémoire pour lecture).
    fake_session = {"audit": audit}
    context = _context_from_installation(audit.installation)
    return summarize_controls(fake_session, contexte_technique=context)


def compare_audits(current: Audit, previous: Audit) -> dict[str, Any]:
    current_summary = _summary_for_audit(current)
    previous_summary = _summary_for_audit(previous)

    audit_indicators = []
    for label, key, unit in [
        ("Taux de complétion", "taux_completion_pct", "%"),
        ("Taux de conformité", "taux_conformite_pct", "%"),
    ]:
        current_value = current_summary.get(key, 0)
        previous_value = previous_summary.get(key, 0)
        audit_indicators.append(
            {
                "indicateur": label,
                "actuel": current_value,
                "precedent": previous_value,
                "ecart": round(current_value - previous_value, 1),
                "unite": unit,
            }
        )

    for label, key in [
        ("Non-conformités critiques", "critique"),
        ("Non-conformités majeures", "majeure"),
    ]:
        current_value = current_summary["criticites_nc"].get(key, 0)
        previous_value = previous_summary["criticites_nc"].get(key, 0)
        audit_indicators.append(
            {
                "indicateur": label,
                "actuel": current_value,
                "precedent": previous_value,
                "ecart": current_value - previous_value,
                "unite": "",
            }
        )

    current_by_label = {r.libelle: r for r in current.releves}
    previous_by_label = {r.libelle: r for r in previous.releves}
    common_labels = sorted(set(current_by_label) & set(previous_by_label))

    measure_indicators = []
    for label in common_labels:
        current_releve = current_by_label[label]
        previous_releve = previous_by_label[label]
        measure_indicators.append(
            {
                "indicateur": label,
                "actuel": current_releve.valeur,
                "precedent": previous_releve.valeur,
                "ecart": round(current_releve.valeur - previous_releve.valeur, 2),
                "unite": current_releve.unite,
            }
        )

    return {
        "audit_indicators": audit_indicators,
        "measure_indicators": measure_indicators,
        "previous_meta": {
            "numero_audit": previous.meta.numero_audit,
            "date_audit": str(previous.meta.date_audit),
        },
    }
