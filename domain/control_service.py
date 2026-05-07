from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from domain.control_catalog import CONTROL_CATALOG, Criticite, VerdictControle
from domain.models import Audit, ConstatControle, ControleCatalogueItem, Installation


class ControlServiceError(Exception):
    pass


def is_applicable(control: ControleCatalogueItem, installation: Installation) -> bool:
    classification = getattr(installation, "classification", None)
    if classification is None:
        return True

    cond = control.condition_applicabilite or {}

    systeme = getattr(classification, "systeme_capteurs", None)
    echangeur = getattr(classification, "type_echangeur", None)
    comptages = set(getattr(classification, "type_comptage", []) or [])

    if "systeme_capteurs_in" in cond and systeme not in cond["systeme_capteurs_in"]:
        return False
    if "systeme_capteurs_not_in" in cond and systeme in cond["systeme_capteurs_not_in"]:
        return False
    if "type_echangeur_in" in cond and echangeur not in cond["type_echangeur_in"]:
        return False
    if "type_echangeur_not_in" in cond and echangeur in cond["type_echangeur_not_in"]:
        return False
    if "type_comptage_any_in" in cond and not comptages.intersection(set(cond["type_comptage_any_in"])):
        return False

    return True


def get_applicable_controls(audit: Audit) -> List[ControleCatalogueItem]:
    return [control for control in CONTROL_CATALOG if is_applicable(control, audit.installation)]


def group_controls_by_section(audit: Audit) -> Dict[str, List[ControleCatalogueItem]]:
    grouped = defaultdict(list)
    for item in get_applicable_controls(audit):
        grouped[item.section].append(item)
    return dict(grouped)


def index_constats(audit: Audit) -> Dict[str, ConstatControle]:
    return {constat.controle_id: constat for constat in audit.constats}


def get_constat(audit: Audit, controle_id: str) -> ConstatControle | None:
    return index_constats(audit).get(controle_id)


def get_or_create_constat(audit: Audit, item: ControleCatalogueItem) -> ConstatControle:
    existing = get_constat(audit, item.controle_id)
    if existing is not None:
        return existing

    constat = ConstatControle(
        controle_id=item.controle_id,
        section=item.section,
        libelle=item.libelle,
        verdict=None,
        criticite=item.criticite_par_defaut,
        criticite_finale=item.criticite_par_defaut,
        observation=None,
        recommandation=item.recommandation_type,
        recommandation_personnalisee=None,
        preuve_documentaire=None,
        photos=[],
        non_verifiable_raison=None,
    )
    audit.constats.append(constat)
    return constat


def remove_non_applicable_constats(audit: Audit) -> None:
    applicable_ids = {item.controle_id for item in get_applicable_controls(audit)}
    audit.constats = [constat for constat in audit.constats if constat.controle_id in applicable_ids]


def _get_audit(session_state: Any) -> Audit:
    audit = session_state.get("audit")
    if audit is None:
        raise ControlServiceError("Aucun audit actif en session.")
    return audit


def _find_catalog_item(audit: Audit, controle_id: str) -> ControleCatalogueItem:
    for item in get_applicable_controls(audit):
        if item.controle_id == controle_id:
            return item
    raise ControlServiceError(f"Contrôle introuvable ou non applicable : {controle_id}")


def ensure_control_state(session_state: Any, contexte_technique: dict[str, Any] | None = None) -> None:
    audit = _get_audit(session_state)
    applicable = get_applicable_controls(audit)
    existing_ids = {c.controle_id for c in audit.constats}

    for item in applicable:
        if item.controle_id not in existing_ids:
            audit.constats.append(
                ConstatControle(
                    controle_id=item.controle_id,
                    section=item.section,
                    libelle=item.libelle,
                    verdict=None,
                    criticite=item.criticite_par_defaut,
                    criticite_finale=item.criticite_par_defaut,
                    observation=None,
                    recommandation=item.recommandation_type,
                    recommandation_personnalisee=None,
                    preuve_documentaire=None,
                    photos=[],
                    non_verifiable_raison=None,
                )
            )

    remove_non_applicable_constats(audit)
    session_state["audit"] = audit


def get_section_responses(
    session_state: Any,
    section: str,
    contexte_technique: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    audit = _get_audit(session_state)
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    constats_index = index_constats(audit)

    rows = []
    for item in get_applicable_controls(audit):
        if item.section != section:
            continue
        constat = constats_index.get(item.controle_id) or get_or_create_constat(audit, item)
        rows.append({"control": item, "response": constat})
    return rows


def get_progress_by_section(
    session_state: Any,
    contexte_technique: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    audit = _get_audit(session_state)
    ensure_control_state(session_state, contexte_technique=contexte_technique)

    grouped = group_controls_by_section(audit)
    constats_index = index_constats(audit)
    output = []

    for section, controls in grouped.items():
        total = len(controls)
        completed = sum(
            1
            for item in controls
            if item.controle_id in constats_index and constats_index[item.controle_id].verdict is not None
        )
        pct = round((completed / total) * 100) if total else 0
        output.append(
            {
                "section": section,
                "total": total,
                "completed": completed,
                "completion_pct": pct,
            }
        )

    output.sort(key=lambda x: x["section"])
    return output


def summarize_controls(
    session_state: Any,
    contexte_technique: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit = _get_audit(session_state)
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    controls = get_applicable_controls(audit)
    constats_index = index_constats(audit)

    total = len(controls)
    compteurs = Counter(
        {
            "conforme": 0,
            "non_conforme": 0,
            "non_present": 0,
            "non_verifiable": 0,
            "sans_objet": 0,
            "non_renseigne": 0,
        }
    )
    criticites_nc = Counter()
    applicable_for_conformity = 0
    conformes = 0

    for item in controls:
        constat = constats_index.get(item.controle_id)
        verdict = constat.verdict if constat else None

        if verdict is None:
            compteurs["non_renseigne"] += 1
            continue

        verdict_value = verdict.value if hasattr(verdict, "value") else str(verdict)
        compteurs[verdict_value] += 1

        if verdict_value != VerdictControle.sans_objet.value:
            applicable_for_conformity += 1
            if verdict_value == VerdictControle.conforme.value:
                conformes += 1

        if verdict_value in {
            VerdictControle.non_conforme.value,
            VerdictControle.non_present.value,
            VerdictControle.non_verifiable.value,
        }:
            criticite = getattr(constat, "criticite_finale", getattr(constat, "criticite", item.criticite_par_defaut))
            criticite_value = criticite.value if hasattr(criticite, "value") else str(criticite)
            criticites_nc[criticite_value] += 1

    completed = total - compteurs["non_renseigne"]
    taux_completion = round((completed / total) * 100) if total else 0
    taux_conformite = round((conformes / applicable_for_conformity) * 100) if applicable_for_conformity else 0

    return {
        "total_applicables": total,
        "compteurs": dict(compteurs),
        "criticites_nc": dict(criticites_nc),
        "taux_completion_pct": taux_completion,
        "taux_conformite_pct": taux_conformite,
    }


def count_open_critical_findings(
    session_state: Any,
    contexte_technique: dict[str, Any] | None = None,
) -> int:
    audit = _get_audit(session_state)
    ensure_control_state(session_state, contexte_technique=contexte_technique)

    total = 0
    for constat in audit.constats:
        verdict = constat.verdict
        if verdict not in {
            VerdictControle.non_conforme,
            VerdictControle.non_present,
            VerdictControle.non_verifiable,
        }:
            continue

        criticite = getattr(constat, "criticite_finale", getattr(constat, "criticite", None))
        if criticite == Criticite.critique:
            total += 1
    return total


def append_uploaded_evidences(
    uploaded_files: list[Any],
    controle_id: str,
    session_state: Any,
    existing_paths: list[str] | None = None,
    base_dir: str = "data/evidences",
) -> list[str]:
    target_dir = Path(base_dir) / controle_id
    target_dir.mkdir(parents=True, exist_ok=True)

    paths = list(existing_paths or [])
    for uploaded in uploaded_files:
        filename = Path(uploaded.name).name
        out_path = target_dir / filename
        out_path.write_bytes(uploaded.getbuffer())
        paths.append(str(out_path))

    return paths


def update_response(
    session_state: Any,
    controle_id: str,
    *,
    verdict: str | None,
    observation: str = "",
    criticite_finale: str | None = None,
    recommandation_personnalisee: str = "",
    preuve_documentaire: str = "",
    photos: list[str] | None = None,
    non_verifiable_raison: str = "",
) -> None:
    audit = _get_audit(session_state)
    item = _find_catalog_item(audit, controle_id)
    constat = get_or_create_constat(audit, item)

    constat.verdict = VerdictControle(verdict) if verdict else None
    constat.observation = observation or None
    constat.recommandation = recommandation_personnalisee or item.recommandation_type
    constat.recommandation_personnalisee = recommandation_personnalisee or None
    constat.preuve_documentaire = preuve_documentaire or None
    constat.photos = list(photos or [])
    constat.non_verifiable_raison = non_verifiable_raison or None

    if criticite_finale:
        constat.criticite_finale = Criticite(criticite_finale)
        constat.criticite = Criticite(criticite_finale)
    else:
        constat.criticite_finale = constat.criticite

    session_state["audit"] = audit


def reset_response(
    session_state: Any,
    controle_id: str,
    contexte_technique: dict[str, Any] | None = None,
) -> None:
    audit = _get_audit(session_state)
    item = _find_catalog_item(audit, controle_id)
    constat = get_or_create_constat(audit, item)

    constat.verdict = None
    constat.observation = None
    constat.recommandation = item.recommandation_type
    constat.recommandation_personnalisee = None
    constat.preuve_documentaire = None
    constat.photos = []
    constat.non_verifiable_raison = None
    constat.criticite = item.criticite_par_defaut
    constat.criticite_finale = item.criticite_par_defaut

    session_state["audit"] = audit


def extract_findings(
    session_state: Any,
    contexte_technique: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    audit = _get_audit(session_state)
    findings = []

    for constat in audit.constats:
        if constat.verdict not in {
            VerdictControle.non_conforme,
            VerdictControle.non_present,
            VerdictControle.non_verifiable,
        }:
            continue

        findings.append(
            {
                "controle_id": constat.controle_id,
                "section": constat.section,
                "libelle": constat.libelle,
                "verdict": constat.verdict.value if hasattr(constat.verdict, "value") else str(constat.verdict),
                "criticite": constat.criticite_finale.value if hasattr(constat.criticite_finale, "value") else str(constat.criticite_finale),
                "observation": constat.observation or "",
                "recommandation": constat.recommandation_personnalisee or constat.recommandation or "",
                "preuve_documentaire": constat.preuve_documentaire or "",
                "photos": list(constat.photos or []),
            }
        )

    return findings


def build_action_plan(
    session_state: Any,
    contexte_technique: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    findings = extract_findings(session_state, contexte_technique=contexte_technique)

    priority_map = {
        Criticite.critique.value: "P1",
        Criticite.majeure.value: "P1",
        Criticite.mineure.value: "P2",
    }

    actions = []
    for row in findings:
        actions.append(
            {
                "priorite": priority_map.get(row["criticite"], "P3"),
                "controle_id": row["controle_id"],
                "section": row["section"],
                "objet": row["libelle"],
                "action_recommandee": row.get("recommandation") or "Définir une action corrective adaptée.",
                "preuve_associee": row.get("preuve_documentaire", ""),
            }
        )

    actions.sort(key=lambda x: (x["priorite"], x["section"], x["controle_id"]))
    return actions