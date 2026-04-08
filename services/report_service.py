from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from domain.control_catalog import Criticite, VerdictControle
from domain.control_service import (
    build_action_plan,
    export_responses_for_report,
    extract_findings,
    summarize_controls,
)


@dataclass
class ReportFinding:
    controle_id: str
    section: str
    libelle: str
    criticite: str
    verdict: str
    observation: str
    recommandation: str
    impact: str
    preuve_documentaire: str
    photos: list[str]
    phrase_constat: str
    phrase_impact: str
    phrase_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "controle_id": self.controle_id,
            "section": self.section,
            "libelle": self.libelle,
            "criticite": self.criticite,
            "verdict": self.verdict,
            "observation": self.observation,
            "recommandation": self.recommandation,
            "impact": self.impact,
            "preuve_documentaire": self.preuve_documentaire,
            "photos": list(self.photos),
            "phrase_constat": self.phrase_constat,
            "phrase_impact": self.phrase_impact,
            "phrase_action": self.phrase_action,
        }


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _criticite_rank(value: str) -> int:
    order = {
        Criticite.critique.value: 0,
        Criticite.majeure.value: 1,
        Criticite.mineure.value: 2,
        Criticite.information.value: 3,
    }
    return order.get(value, 99)


def _verdict_to_label(verdict: str) -> str:
    labels = {
        VerdictControle.conforme.value: "conforme",
        VerdictControle.non_conforme.value: "non conforme",
        VerdictControle.non_present.value: "non présent",
        VerdictControle.non_verifiable.value: "non vérifiable",
        VerdictControle.sans_objet.value: "sans objet",
    }
    return labels.get(verdict, verdict)


def _criticite_to_label(criticite: str) -> str:
    labels = {
        Criticite.critique.value: "critique",
        Criticite.majeure.value: "majeure",
        Criticite.mineure.value: "mineure",
        Criticite.information.value: "d'information",
    }
    return labels.get(criticite, criticite)


def _make_constat_sentence(finding: dict[str, Any]) -> str:
    verdict = _verdict_to_label(finding["verdict"])
    criticite = _criticite_to_label(finding["criticite"])
    base = f"Le contrôle {finding['controle_id']} relatif à « {finding['libelle']} » a été classé {verdict}, avec une criticité {criticite}."

    observation = _safe_str(finding.get("observation"))
    if observation:
        return f"{base} Observation relevée : {observation}"
    return base


def _make_impact_sentence(finding: dict[str, Any]) -> str:
    impact = _safe_str(finding.get("impact_defaut") or finding.get("impact"))
    if impact:
        return f"L’impact potentiel identifié concerne {impact}."
    return "L’impact potentiel doit être apprécié au regard du fonctionnement, de la sécurité et de la performance de l’installation."


def _make_action_sentence(finding: dict[str, Any]) -> str:
    action = _safe_str(finding.get("recommandation"))
    if action:
        return f"Action recommandée : {action}"
    return "Action recommandée : définir puis mettre en œuvre une action corrective adaptée au défaut observé."


def _make_report_finding(raw: dict[str, Any]) -> ReportFinding:
    return ReportFinding(
        controle_id=raw["controle_id"],
        section=raw["section"],
        libelle=raw["libelle"],
        criticite=raw["criticite"],
        verdict=raw["verdict"],
        observation=_safe_str(raw.get("observation")),
        recommandation=_safe_str(raw.get("recommandation")),
        impact=_safe_str(raw.get("impact_defaut") or raw.get("impact")),
        preuve_documentaire=_safe_str(raw.get("preuve_documentaire")),
        photos=list(raw.get("photos") or []),
        phrase_constat=_make_constat_sentence(raw),
        phrase_impact=_make_impact_sentence(raw),
        phrase_action=_make_action_sentence(raw),
    )


def _group_findings_by_section(findings: list[ReportFinding]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        out[finding.section].append(finding.to_dict())

    for section, rows in out.items():
        rows.sort(key=lambda x: (_criticite_rank(x["criticite"]), x["controle_id"]))
    return dict(out)


def _build_executive_summary(summary: dict[str, Any], actions: list[dict[str, Any]]) -> list[str]:
    total = summary["total_applicables"]
    nc = summary["compteurs"]["non_conforme"]
    np = summary["compteurs"]["non_present"]
    nv = summary["compteurs"]["non_verifiable"]
    nr = summary["compteurs"]["non_renseigne"]

    p1 = sum(1 for a in actions if a["priorite"] == "P1")
    p2 = sum(1 for a in actions if a["priorite"] == "P2")
    p3 = sum(1 for a in actions if a["priorite"] == "P3")

    lines = [
        f"L’audit technique couvre {total} point(s) de contrôle applicables.",
        f"La campagne de contrôle met en évidence {nc} non-conformité(s), {np} point(s) non présent(s), {nv} point(s) non vérifiable(s) et {nr} point(s) restant à renseigner.",
        f"Le plan d’actions issu de l’audit comprend {p1} action(s) de priorité P1, {p2} action(s) de priorité P2 et {p3} action(s) de priorité P3.",
    ]
    return lines


def _build_global_assessment(summary: dict[str, Any]) -> dict[str, Any]:
    criticites = summary["criticites_nc"]
    nb_crit = criticites.get(Criticite.critique.value, 0)
    nb_maj = criticites.get(Criticite.majeure.value, 0)
    taux_completion = summary["taux_completion_pct"]
    taux_conformite = summary["taux_conformite_pct"]

    statut = "favorable sous réserves"
    commentaire = (
        "L’installation présente un niveau globalement acceptable, sous réserve du traitement des écarts relevés."
    )

    if nb_crit > 0:
        statut = "défavorable"
        commentaire = (
            "L’installation présente au moins un écart critique nécessitant un traitement prioritaire avant considération d’un fonctionnement satisfaisant."
        )
    elif nb_maj >= 3:
        statut = "réserves majeures"
        commentaire = (
            "L’installation présente plusieurs écarts majeurs susceptibles d’altérer durablement la performance, la disponibilité ou la maintenabilité."
        )
    elif taux_completion < 90:
        statut = "à consolider"
        commentaire = (
            "L’analyse reste partiellement incomplète et nécessite la consolidation des points encore non renseignés ou non vérifiables."
        )

    return {
        "statut_global": statut,
        "commentaire_global": commentaire,
        "taux_completion_pct": taux_completion,
        "taux_conformite_pct": taux_conformite,
        "nb_nc_critique": nb_crit,
        "nb_nc_majeure": nb_maj,
    }


def _build_section_summaries(findings: list[ReportFinding]) -> list[dict[str, Any]]:
    by_section: dict[str, list[ReportFinding]] = defaultdict(list)
    for finding in findings:
        by_section[finding.section].append(finding)

    output: list[dict[str, Any]] = []
    for section, rows in sorted(by_section.items()):
        criticity_counter = Counter([r.criticite for r in rows])
        verdict_counter = Counter([r.verdict for r in rows])

        intro = f"La section « {section} » présente {len(rows)} constat(s) significatif(s)."
        if criticity_counter.get(Criticite.critique.value, 0) > 0:
            intro += " Au moins un écart critique y a été identifié."
        elif criticity_counter.get(Criticite.majeure.value, 0) > 0:
            intro += " Des écarts majeurs y ont été relevés."

        output.append(
            {
                "section": section,
                "nb_constats": len(rows),
                "nb_critiques": criticity_counter.get(Criticite.critique.value, 0),
                "nb_majeures": criticity_counter.get(Criticite.majeure.value, 0),
                "nb_mineures": criticity_counter.get(Criticite.mineure.value, 0),
                "nb_information": criticity_counter.get(Criticite.information.value, 0),
                "nb_non_conformes": verdict_counter.get(VerdictControle.non_conforme.value, 0),
                "nb_non_presents": verdict_counter.get(VerdictControle.non_present.value, 0),
                "nb_non_verifiables": verdict_counter.get(VerdictControle.non_verifiable.value, 0),
                "texte_intro": intro,
            }
        )
    return output


def _build_key_messages(findings: list[ReportFinding], actions: list[dict[str, Any]]) -> list[str]:
    messages: list[str] = []

    critical_findings = [f for f in findings if f.criticite == Criticite.critique.value]
    if critical_findings:
        messages.append(
            "Des écarts critiques ont été identifiés et doivent être traités en priorité avant toute appréciation favorable du fonctionnement global."
        )

    monitoring_findings = [
        f for f in findings
        if "monitor" in f.section.lower()
        or "métrologie" in f.section.lower()
        or "régulation" in f.section.lower()
    ]
    if monitoring_findings:
        messages.append(
            "Les constats liés à la régulation, à la métrologie ou au suivi de fonctionnement doivent être considérés avec attention, car ils conditionnent la capacité à diagnostiquer et maintenir les performances dans le temps."
        )

    if any(a["priorite"] == "P1" for a in actions):
        messages.append(
            "Le plan d’actions comprend des mesures de priorité P1 nécessitant un traitement prioritaire et tracé."
        )

    if not messages:
        messages.append(
            "Aucun message d’alerte majeur ne ressort à ce stade, sous réserve de compléter et confirmer l’ensemble des points de contrôle."
        )

    return messages


def _build_methodology_note() -> list[str]:
    return [
        "Les constats sont établis à partir des points de contrôle applicables, des observations terrain, des pièces justificatives associées et des informations de configuration de l’installation.",
        "Les écarts sont hiérarchisés selon une criticité de type critique, majeure, mineure ou information, afin de prioriser les actions correctives.",
        "Le plan d’actions vise à traiter les écarts observés selon une logique de priorité, de conséquence technique et de traçabilité des preuves.",
    ]


def _build_report_payload(
    summary: dict[str, Any],
    findings: list[ReportFinding],
    actions: list[dict[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "metadata": dict(metadata or {}),
        "executive_summary": _build_executive_summary(summary, actions),
        "global_assessment": _build_global_assessment(summary),
        "key_messages": _build_key_messages(findings, actions),
        "methodology_note": _build_methodology_note(),
        "section_summaries": _build_section_summaries(findings),
        "findings_by_section": _group_findings_by_section(findings),
        "findings_flat": [f.to_dict() for f in findings],
        "action_plan": actions,
        "counts": {
            "total_findings": len(findings),
            "total_actions": len(actions),
            "critical_findings": sum(1 for f in findings if f.criticite == Criticite.critique.value),
            "major_findings": sum(1 for f in findings if f.criticite == Criticite.majeure.value),
        },
    }


def build_report_data(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = summarize_controls(session_state, contexte_technique=contexte_technique)
    raw_findings = extract_findings(session_state, contexte_technique=contexte_technique)
    findings = [_make_report_finding(item) for item in raw_findings]
    findings.sort(key=lambda x: (_criticite_rank(x.criticite), x.section, x.controle_id))

    actions = build_action_plan(session_state, contexte_technique=contexte_technique)
    metadata = export_responses_for_report(
        session_state,
        contexte_technique=contexte_technique,
    ).get("metadata", {})

    return _build_report_payload(summary, findings, actions, metadata=metadata)


def generate_section_narrative(
    session_state: Any,
    section: str,
    contexte_technique: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_report_data(session_state, contexte_technique=contexte_technique)
    rows = payload["findings_by_section"].get(section, [])

    if not rows:
        return {
            "section": section,
            "intro": f"Aucun constat significatif n’est actuellement consolidé pour la section « {section} ».",
            "paragraphs": [],
        }

    intro = f"La section « {section} » regroupe {len(rows)} constat(s) nécessitant une attention particulière."
    paragraphs = []
    for row in rows:
        paragraphs.append(" ".join([row["phrase_constat"], row["phrase_impact"], row["phrase_action"]]))

    return {
        "section": section,
        "intro": intro,
        "paragraphs": paragraphs,
    }


def generate_action_plan_table(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions = build_action_plan(session_state, contexte_technique=contexte_technique)
    actions.sort(key=lambda x: (x["priorite"], x["section"], x["controle_id"]))
    return actions


def build_report_markdown(
    session_state: Any,
    contexte_technique: Mapping[str, Any] | None = None,
) -> str:
    payload = build_report_data(session_state, contexte_technique=contexte_technique)

    lines: list[str] = []
    lines.append("# Rapport d’audit technique")
    lines.append("")
    lines.append("## Synthèse")
    for item in payload["executive_summary"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Appréciation globale")
    lines.append(payload["global_assessment"]["commentaire_global"])

    lines.append("")
    lines.append("## Messages clés")
    for item in payload["key_messages"]:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## Constats par section")
    for section in sorted(payload["findings_by_section"].keys()):
        narrative = generate_section_narrative(
            session_state,
            section,
            contexte_technique=contexte_technique,
        )
        lines.append(f"### {section}")
        lines.append(narrative["intro"])
        for paragraph in narrative["paragraphs"]:
            lines.append(f"- {paragraph}")
        lines.append("")

    lines.append("## Plan d’actions")
    for action in payload["action_plan"]:
        lines.append(
            f"- {action['priorite']} | {action['controle_id']} | {action['section']} | {action['objet']} | {action['action_recommandee']}"
        )

    return "\n".join(lines).strip()