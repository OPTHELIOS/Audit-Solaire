from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from domain.control_catalog import (
    CONTROL_CATALOG,
    Criticite,
    VerdictControle,
    ControleCatalogueItem,
    filter_controls,
    get_all_controls,
    get_control_by_id,
)

SESSION_KEY = "audit_controls"
SESSION_META_KEY = "audit_controls_meta"


class ControlServiceError(ValueError):
    """Erreur métier liée à la gestion des réponses de contrôle."""


class StatutSaisie(str):
    vide = "vide"
    commence = "commence"
    complete = "complete"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _normalize_list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = _safe_str(value)
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set, frozenset)):
        out: list[str] = []
        for item in value:
            cleaned = _safe_str(item)
            if cleaned:
                out.append(cleaned)
        return out
    return []


def _normalize_criticite(value: Any, fallback: Criticite) -> Criticite:
    if isinstance(value, Criticite):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        for item in Criticite:
            if item.value == v:
                return item
    return fallback


def _normalize_verdict(value: Any) -> VerdictControle | None:
    if value is None or value == "":
        return None
    if isinstance(value, VerdictControle):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        for item in VerdictControle:
            if item.value == v:
                return item
    raise ControlServiceError(f"Verdict invalide : {value}")


def sanitize_filename(filename: str, fallback: str = "preuve") -> str:
    name = _safe_str(filename)
    if not name:
        return fallback
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._")
    return name or fallback


@dataclass
class ControlResponse:
    controle_id: str
    applicable: bool
    statut_saisie: str
    verdict: VerdictControle | None
    criticite_catalogue: Criticite
    criticite_finale: Criticite
    observation: str
    recommandation_personnalisee: str
    preuve_documentaire: str
    photos: list[str]
    non_verifiable_raison: str
    horodatage_maj: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "controle_id": self.controle_id,
            "applicable": self.applicable,
            "statut_saisie": self.statut_saisie,
            "verdict": self.verdict.value if self.verdict else None,
            "criticite_catalogue": self.criticite_catalogue.value,
            "criticite_finale": self.criticite_finale.value,
            "observation": self.observation,
            "recommandation_personnalisee": self.recommandation_personnalisee,
            "preuve_documentaire": self.preuve_documentaire,
            "photos": list(self.photos),
            "non_verifiable_raison": self.non_verifiable_raison,
            "horodatage_maj": self.horodatage_maj,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], control_item: ControleCatalogueItem) -> "ControlResponse":
        return cls(
            controle_id=control_item.controle_id,
            applicable=_normalize_bool(data.get("applicable"), True),
            statut_saisie=_safe_str(data.get("statut_saisie")) or StatutSaisie.vide,
            verdict=_normalize_verdict(data.get("verdict")),
            criticite_catalogue=control_item.criticite_par_defaut,
            criticite_finale=_normalize_criticite(data.get("criticite_finale"), control_item.criticite_par_defaut),
            observation=_safe_str(data.get("observation")),
            recommandation_personnalisee=_safe_str(data.get("recommandation_personnalisee")),
            preuve_documentaire=_safe_str(data.get("preuve_documentaire")),
            photos=_normalize_list_of_strings(data.get("photos")),
            non_verifiable_raison=_safe_str(data.get("non_verifiable_raison")),
            horodatage_maj=data.get("horodatage_maj"),
        )


def make_default_response(control_item: ControleCatalogueItem, applicable: bool = True) -> ControlResponse:
    return ControlResponse(
        controle_id=control_item.controle_id,
        applicable=applicable,
        statut_saisie=StatutSaisie.vide if applicable else StatutSaisie.complete,
        verdict=VerdictControle.sans_objet if not applicable else None,
        criticite_catalogue=control_item.criticite_par_defaut,
        criticite_finale=control_item.criticite_par_defaut,
        observation="",
        recommandation_personnalisee="",
        preuve_documentaire="",
        photos=[],
        non_verifiable_raison="",
        horodatage_maj=None,
    )


def ensure_control_state(session_state: Any, contexte_technique: Mapping[str, Any] | None = None) -> None:
    if SESSION_KEY not in session_state:
        session_state[SESSION_KEY] = {}
    if SESSION_META_KEY not in session_state:
        session_state[SESSION_META_KEY] = {
            "initialized_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "catalog_size": len(CONTROL_CATALOG),
        }

    existing = session_state[SESSION_KEY]
    applicable_ids = {
        item.controle_id for item in filter_controls(contexte=contexte_technique, actif_only=True)
    }

    for item in get_all_controls():
        if item.controle_id not in existing:
            existing[item.controle_id] = make_default_response(
                item,
                applicable=item.controle_id in applicable_ids,
            ).to_dict()
        else:
            current = ControlResponse.from_dict(existing[item.controle_id], item)
            current.applicable = item.controle_id in applicable_ids

            if not current.applicable:
                current.verdict = VerdictControle.sans_objet
                current.statut_saisie = StatutSaisie.complete

            existing[item.controle_id] = current.to_dict()

    session_state[SESSION_META_KEY]["updated_at"] = _utc_now_iso()


def get_all_responses(session_state: Any) -> dict[str, dict[str, Any]]:
    ensure_control_state(session_state)
    return session_state[SESSION_KEY]


def get_response(session_state: Any, controle_id: str) -> ControlResponse:
    ensure_control_state(session_state)
    item = get_control_by_id(controle_id)
    raw = session_state[SESSION_KEY][controle_id]
    return ControlResponse.from_dict(raw, item)


def infer_statut_saisie(response: ControlResponse) -> str:
    if not response.applicable:
        return StatutSaisie.complete

    has_content = any(
        [
            response.verdict is not None,
            bool(response.observation),
            bool(response.preuve_documentaire),
            bool(response.photos),
            bool(response.recommandation_personnalisee),
            bool(response.non_verifiable_raison),
        ]
    )
    if response.verdict is not None:
        return StatutSaisie.complete
    if has_content:
        return StatutSaisie.commence
    return StatutSaisie.vide


def validate_response(response: ControlResponse, control_item: ControleCatalogueItem) -> None:
    if response.controle_id != control_item.controle_id:
        raise ControlServiceError("Incohérence entre la réponse et le contrôle.")

    if not response.applicable:
        if response.verdict not in (VerdictControle.sans_objet, None):
            raise ControlServiceError(
                f"Le contrôle {response.controle_id} est non applicable et doit être 'sans objet'."
            )
        return

    if response.verdict == VerdictControle.non_verifiable and not response.non_verifiable_raison:
        raise ControlServiceError(
            f"Le contrôle {response.controle_id} est 'non vérifiable' sans justification."
        )

    if response.verdict == VerdictControle.non_conforme and not (
        response.observation or response.recommandation_personnalisee
    ):
        raise ControlServiceError(
            f"Le contrôle {response.controle_id} est non conforme sans observation ni recommandation."
        )


def update_response(
    session_state: Any,
    controle_id: str,
    *,
    verdict: VerdictControle | str | None = None,
    observation: str | None = None,
    criticite_finale: Criticite | str | None = None,
    recommandation_personnalisee: str | None = None,
    preuve_documentaire: str | None = None,
    photos: Iterable[str] | None = None,
    non_verifiable_raison: str | None = None,
) -> ControlResponse:
    ensure_control_state(session_state)
    item = get_control_by_id(controle_id)
    current = get_response(session_state, controle_id)

    if verdict is not None:
        current.verdict = _normalize_verdict(verdict)

    if observation is not None:
        current.observation = _safe_str(observation)

    if criticite_finale is not None:
        current.criticite_finale = _normalize_criticite(criticite_finale, item.criticite_par_defaut)

    if recommandation_personnalisee is not None:
        current.recommandation_personnalisee = _safe_str(recommandation_personnalisee)

    if preuve_documentaire is not None:
        current.preuve_documentaire = _safe_str(preuve_documentaire)

    if photos is not None:
        current.photos = _normalize_list_of_strings(list(photos))

    if non_verifiable_raison is not None:
        current.non_verifiable_raison = _safe_str(non_verifiable_raison)

    current.statut_saisie = infer_statut_saisie(current)
    current.horodatage_maj = _utc_now_iso()

    validate_response(current, item)
    session_state[SESSION_KEY][controle_id] = current.to_dict()
    session_state[SESSION_META_KEY]["updated_at"] = _utc_now_iso()
    return current


def reset_response(
    session_state: Any,
    controle_id: str,
    contexte_technique: Mapping[str, Any] | None = None,
) -> ControlResponse:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    item = get_control_by_id(controle_id)
    applicable = item.is_applicable(contexte_technique)
    default = make_default_response(item, applicable=applicable)
    session_state[SESSION_KEY][controle_id] = default.to_dict()
    session_state[SESSION_META_KEY]["updated_at"] = _utc_now_iso()
    return default


def get_applicable_controls(
    contexte_technique: Mapping[str, Any] | None = None,
    section: str | None = None,
) -> list[ControleCatalogueItem]:
    return filter_controls(section=section, contexte=contexte_technique, actif_only=True)


def get_section_responses(
    session_state: Any,
    section: str,
    contexte_technique: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    controls = get_applicable_controls(contexte_technique=contexte_technique, section=section)
    return [{"control": item, "response": get_response(session_state, item.controle_id)} for item in controls]


def summarize_controls(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    controls = get_applicable_controls(contexte_technique=contexte_technique)

    total = len(controls)
    counters = {
        "conforme": 0,
        "non_conforme": 0,
        "non_verifiable": 0,
        "non_present": 0,
        "sans_objet": 0,
        "non_renseigne": 0,
    }
    criticites_nc = {c.value: 0 for c in Criticite}
    by_section: dict[str, dict[str, int]] = {}

    for item in controls:
        response = get_response(session_state, item.controle_id)
        section_stats = by_section.setdefault(
            item.section,
            {
                "total": 0,
                "conforme": 0,
                "non_conforme": 0,
                "non_verifiable": 0,
                "non_present": 0,
                "non_renseigne": 0,
            },
        )
        section_stats["total"] += 1

        if response.verdict is None:
            counters["non_renseigne"] += 1
            section_stats["non_renseigne"] += 1
            continue

        counters[response.verdict.value] += 1
        if response.verdict.value in section_stats:
            section_stats[response.verdict.value] += 1

        if response.verdict in (VerdictControle.non_conforme, VerdictControle.non_present):
            criticites_nc[response.criticite_finale.value] += 1

    taux_completion = 0.0 if total == 0 else round((total - counters["non_renseigne"]) / total * 100, 1)
    taux_conformite = 0.0 if total == 0 else round(counters["conforme"] / total * 100, 1)

    return {
        "total_applicables": total,
        "compteurs": counters,
        "criticites_nc": criticites_nc,
        "par_section": by_section,
        "taux_completion_pct": taux_completion,
        "taux_conformite_pct": taux_conformite,
    }


def extract_findings(
    session_state: Any,
    *,
    contexte_technique: Mapping[str, Any] | None = None,
    verdicts: Iterable[VerdictControle | str] | None = None,
    criticites: Iterable[Criticite | str] | None = None,
) -> list[dict[str, Any]]:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    controls = get_applicable_controls(contexte_technique=contexte_technique)

    verdict_filter = None
    if verdicts is not None:
        verdict_filter = {
            v.value if isinstance(v, VerdictControle) else str(v).strip()
            for v in verdicts
        }

    criticite_filter = None
    if criticites is not None:
        criticite_filter = {
            c.value if isinstance(c, Criticite) else str(c).strip()
            for c in criticites
        }

    findings: list[dict[str, Any]] = []
    for item in controls:
        response = get_response(session_state, item.controle_id)
        if response.verdict is None:
            continue
        if verdict_filter and response.verdict.value not in verdict_filter:
            continue
        if criticite_filter and response.criticite_finale.value not in criticite_filter:
            continue

        findings.append(
            {
                "controle_id": item.controle_id,
                "section": item.section,
                "libelle": item.libelle,
                "criticite": response.criticite_finale.value,
                "verdict": response.verdict.value,
                "observation": response.observation,
                "recommandation": response.recommandation_personnalisee or item.recommandation_type,
                "preuve_attendue": item.preuve_attendue,
                "preuve_documentaire": response.preuve_documentaire,
                "photos": list(response.photos),
                "impact_defaut": item.impact_defaut,
            }
        )

    severity_rank = {
        Criticite.critique.value: 0,
        Criticite.majeure.value: 1,
        Criticite.mineure.value: 2,
        Criticite.information.value: 3,
    }
    findings.sort(key=lambda x: (severity_rank.get(x["criticite"], 99), x["section"], x["controle_id"]))
    return findings


def build_action_plan(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    findings = extract_findings(
        session_state,
        contexte_technique=contexte_technique,
        verdicts=[VerdictControle.non_conforme, VerdictControle.non_present],
    )

    actions: list[dict[str, Any]] = []
    for f in findings:
        priority = "P3"
        if f["criticite"] == Criticite.critique.value:
            priority = "P1"
        elif f["criticite"] == Criticite.majeure.value:
            priority = "P2"

        actions.append(
            {
                "priorite": priority,
                "controle_id": f["controle_id"],
                "section": f["section"],
                "objet": f["libelle"],
                "impact": f["impact_defaut"],
                "action_recommandee": f["recommandation"],
                "preuve_associee": f["preuve_documentaire"],
            }
        )
    return actions


def export_responses_for_report(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    return {
        "metadata": deepcopy(session_state.get(SESSION_META_KEY, {})),
        "summary": summarize_controls(session_state, contexte_technique=contexte_technique),
        "findings": extract_findings(session_state, contexte_technique=contexte_technique),
        "action_plan": build_action_plan(session_state, contexte_technique=contexte_technique),
        "responses": deepcopy(session_state.get(SESSION_KEY, {})),
    }


def get_progress_by_section(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ensure_control_state(session_state, contexte_technique=contexte_technique)
    sections = sorted({item.section for item in get_applicable_controls(contexte_technique=contexte_technique)})

    progress: list[dict[str, Any]] = []
    for section in sections:
        rows = get_section_responses(session_state, section, contexte_technique=contexte_technique)
        total = len(rows)
        completed = sum(1 for row in rows if row["response"].statut_saisie == StatutSaisie.complete)
        started = sum(1 for row in rows if row["response"].statut_saisie == StatutSaisie.commence)
        pct = 0.0 if total == 0 else round(completed / total * 100, 1)
        progress.append(
            {
                "section": section,
                "total": total,
                "completed": completed,
                "started": started,
                "completion_pct": pct,
            }
        )
    return progress


def count_open_critical_findings(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> int:
    findings = extract_findings(
        session_state,
        contexte_technique=contexte_technique,
        verdicts=[VerdictControle.non_conforme, VerdictControle.non_present],
        criticites=[Criticite.critique],
    )
    return len(findings)


def get_audit_slug(session_state: Any) -> str:
    audit_meta = session_state.get("audit_meta", {})
    if isinstance(audit_meta, dict):
        candidate = audit_meta.get("audit_id") or audit_meta.get("site_slug") or audit_meta.get("reference")
        if candidate:
            return sanitize_filename(str(candidate), fallback="audit")
    return "audit"


def save_uploaded_evidence(
    uploaded_file: Any,
    *,
    controle_id: str,
    session_state: Any,
    base_dir: str | Path = "data/evidences",
) -> str:
    if uploaded_file is None:
        raise ControlServiceError("Aucun fichier à enregistrer.")

    audit_slug = get_audit_slug(session_state)
    target_dir = Path(base_dir) / audit_slug / sanitize_filename(controle_id, fallback="controle")
    target_dir.mkdir(parents=True, exist_ok=True)

    original_name = getattr(uploaded_file, "name", "preuve")
    safe_name = sanitize_filename(original_name, fallback=f"{controle_id}_preuve")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    final_name = f"{timestamp}_{safe_name}"
    target_path = target_dir / final_name

    with open(target_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(target_path.as_posix())


def append_uploaded_evidences(
    uploaded_files: Iterable[Any] | None,
    *,
    controle_id: str,
    session_state: Any,
    existing_paths: Iterable[str] | None = None,
    base_dir: str | Path = "data/evidences",
) -> list[str]:
    paths = list(existing_paths or [])
    if not uploaded_files:
        return paths

    for uploaded_file in uploaded_files:
        saved_path = save_uploaded_evidence(
            uploaded_file,
            controle_id=controle_id,
            session_state=session_state,
            base_dir=base_dir,
        )
        paths.append(saved_path)

    return list(dict.fromkeys(paths))