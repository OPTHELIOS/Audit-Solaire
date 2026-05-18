from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

from domain.report_service import (
    build_report_data,
    build_report_markdown,
    generate_action_plan_table,
    generate_section_narrative,
)
from ui.studio_panel import render_studio_panel

PAGE_TITLE = "05 - Synthèse de l'audit"
SESSION_CONCLUSION_KEY = "synthese_conclusion_expert"


def _get_context_from_session() -> dict[str, Any]:
    installation = st.session_state.get("installation_context", {})
    if not isinstance(installation, dict):
        installation = {}

    return {
        "systeme_capteurs": installation.get("systeme_capteurs"),
        "type_echangeur": installation.get("type_echangeur"),
        "type_stockage_solaire": (
            installation.get("type_stockage_solaire")
            or installation.get("type_stockage")
        ),
        "type_comptage": installation.get("type_comptage", []),
        "requires_monitoring": bool(installation.get("requires_monitoring", False)),
        "requires_telecontrole": bool(installation.get("requires_telecontrole", False)),
    }


def _render_header(context: dict[str, Any]) -> None:
    st.title(PAGE_TITLE)
    st.caption(
        "Lecture consolidée des constats, hiérarchisation des écarts et préparation du rapport final."
    )

    with st.expander("Contexte technique de synthèse", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Système capteurs** : {context.get('systeme_capteurs') or 'Non défini'}")
        c2.write(f"**Type échangeur** : {context.get('type_echangeur') or 'Non défini'}")
        c3.write(
            f"**Type stockage solaire** : "
            f"{context.get('type_stockage_solaire') or 'Non défini'}"
        )

        c4, c5, c6 = st.columns(3)
        comptage = context.get("type_comptage") or []
        c4.write(f"**Type comptage** : {', '.join(comptage) if comptage else 'Non défini'}")
        c5.write(f"**Monitoring** : {'Oui' if context.get('requires_monitoring') else 'Non'}")
        c6.write(f"**Télécontrôle** : {'Oui' if context.get('requires_telecontrole') else 'Non'}")


def _render_global_metrics(payload: dict[str, Any]) -> None:
    ga = payload.get("global_assessment", {})
    counts = payload.get("counts", {})

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Statut global", ga.get("statut_global", "-"))
    c2.metric("Taux de complétion", f"{ga.get('taux_completion_pct', 0)} %")
    c3.metric("Taux de conformité", f"{ga.get('taux_conformite_pct', 0)} %")
    c4.metric("Constats critiques", counts.get("critical_findings", 0))
    c5.metric("Constats majeurs", counts.get("major_findings", 0))

    st.progress(
        min(max(ga.get("taux_completion_pct", 0) / 100.0, 0.0), 1.0),
        text="Niveau de complétude de l’audit",
    )

    statut = ga.get("statut_global", "")
    commentaire = ga.get("commentaire_global", "")

    if not commentaire:
        return

    if statut == "défavorable":
        st.error(commentaire)
    elif statut in ("réserves majeures", "à consolider"):
        st.warning(commentaire)
    else:
        st.success(commentaire)


def _render_readiness_panel(payload: dict[str, Any]) -> None:
    counts = payload.get("counts", {})
    ga = payload.get("global_assessment", {})

    metadata = payload.get("metadata", {}) or {}
    numero_audit = metadata.get("numero_audit")
    contexte_technique = metadata.get("contexte_technique") or {}

    checks = [
        ("Référence audit", bool(numero_audit)),
        ("Installation qualifiée", bool(contexte_technique)),
        ("Constats présents", counts.get("total_findings", 0) > 0),
        ("Plan d'actions exploitable", counts.get("total_actions", 0) > 0 or ga.get("taux_completion_pct", 0) >= 80),
        ("Audit suffisamment complété", ga.get("taux_completion_pct", 0) >= 80),
    ]

    st.subheader("Audit prêt à exporter ?")

    cols = st.columns(len(checks))
    for col, (label, ok) in zip(cols, checks):
        if ok:
            col.success(label)
        else:
            col.warning(label)

    if all(ok for _, ok in checks):
        st.success("Le dossier paraît suffisamment consolidé pour lancer un export de rapport.")
    else:
        st.info("Certaines briques sont encore incomplètes ou insuffisamment consolidées avant export.")


def _render_executive_summary(payload: dict[str, Any]) -> None:
    st.subheader("Synthèse exécutive")

    for line in payload.get("executive_summary", []):
        st.write(f"- {line}")

    st.markdown("#### Messages clés")
    for line in payload.get("key_messages", []):
        st.write(f"- {line}")

    st.markdown("#### Note méthodologique")
    for line in payload.get("methodology_note", []):
        st.write(f"- {line}")


def _render_expert_conclusion(payload: dict[str, Any]) -> None:
    st.subheader("Conclusion experte")

    default_text = st.session_state.get(SESSION_CONCLUSION_KEY, "")
    if not default_text:
        default_text = payload.get("global_assessment", {}).get("commentaire_global", "")

    conclusion = st.text_area(
        "Conclusion libre",
        value=default_text,
        height=180,
        placeholder="Saisir ici une conclusion technique libre, exploitable dans le rapport final.",
    )

    c1, c2 = st.columns(2)

    if c1.button("Enregistrer la conclusion", use_container_width=True):
        st.session_state[SESSION_CONCLUSION_KEY] = conclusion
        st.success("Conclusion enregistrée dans la session.")

    if c2.button("Réinitialiser depuis le statut global", use_container_width=True):
        st.session_state[SESSION_CONCLUSION_KEY] = payload.get("global_assessment", {}).get(
            "commentaire_global", ""
        )
        st.rerun()


def _render_top_actions(context: dict[str, Any]) -> None:
    st.subheader("Actions prioritaires")

    rows = generate_action_plan_table(
        st.session_state,
        contexte_technique=context,
    )

    if not rows:
        st.success("Aucune action corrective n’est actuellement générée.")
        return

    df = pd.DataFrame(rows)
    priority_order = {"P1": 1, "P2": 2, "P3": 3}
    df["priority_order"] = df["priorite"].map(priority_order).fillna(99)
    df = df.sort_values(by=["priority_order", "section", "controle_id"]).head(5)

    for _, row in df.iterrows():
        with st.expander(f"{row['priorite']} — {row['controle_id']} — {row['objet']}", expanded=False):
            st.write(f"**Section** : {row['section']}")
            st.write(f"**Impact** : {row.get('impact', '')}")
            st.write(f"**Action recommandée** : {row.get('action_recommandee', '')}")
            if row.get("preuves_disponibles"):
                st.write(f"**Preuves disponibles** : {row['preuves_disponibles']}")
            if row.get("photos"):
                st.write(f"**Nombre de photos** : {len(row['photos'])}")


def _render_section_summary_table(payload: dict[str, Any]) -> None:
    st.subheader("Vue par section")

    rows = payload.get("section_summaries", [])
    if not rows:
        st.info("Aucun constat structurant n’est disponible pour le moment.")
        return

    df = pd.DataFrame(rows).rename(
        columns={
            "section": "Section",
            "nb_constats": "Constats",
            "nb_critiques": "Critiques",
            "nb_majeures": "Majeures",
            "nb_mineures": "Mineures",
            "nb_information": "Information",
            "nb_non_conformes": "Non conformes",
            "nb_non_presents": "Non présents",
            "nb_non_verifiables": "Non vérifiables",
            "texte_intro": "Lecture",
        }
    )

    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "Section": st.column_config.Column(width="medium"),
            "Lecture": st.column_config.Column(width="large"),
        },
    )


def _render_findings_overview(payload: dict[str, Any]) -> None:
    st.subheader("Constats prioritaires")

    rows = payload.get("findings_flat", [])
    if not rows:
        st.info("Aucun constat prioritaire à afficher.")
        return

    top_rows = [row for row in rows if row.get("criticite") in {"critique", "majeure"}]

    if not top_rows:
        st.info("Aucun constat critique ou majeur n’est actuellement recensé.")
        return

    for row in top_rows[:10]:
        criticity = str(row.get("criticite", "")).upper()
        with st.expander(
            f"{criticity} — {row.get('controle_id', '-')} — {row.get('libelle', '-')}",
            expanded=False,
        ):
            st.write(f"**Section** : {row.get('section', '-')}")
            st.write(f"**Verdict** : {row.get('verdict', '-')}")
            st.write(f"**Constat** : {row.get('phrase_constat', '-')}")
            st.write(f"**Impact** : {row.get('phrase_impact', '-')}")
            st.write(f"**Action** : {row.get('phrase_action', '-')}")
            if row.get("preuve_documentaire"):
                st.write(f"**Preuve documentaire** : {row['preuve_documentaire']}")
            if row.get("photos"):
                st.write(f"**Nombre de fichiers photo** : {len(row['photos'])}")


def _render_findings_tab(payload: dict[str, Any], context: dict[str, Any]) -> None:
    st.subheader("Constats détaillés")

    findings_by_section = payload.get("findings_by_section", {})
    sections = list(findings_by_section.keys())

    if not sections:
        st.info("Aucun constat rédigé n’est encore disponible.")
        return

    c1, c2 = st.columns(2)
    selected_section = c1.selectbox("Choisir une section à relire", options=sections, index=0)
    sort_mode = c2.selectbox(
        "Trier par",
        options=["ordre_naturel", "criticite", "verdict"],
        format_func=lambda x: {
            "ordre_naturel": "Ordre naturel",
            "criticite": "Criticité",
            "verdict": "Verdict",
        }[x],
        index=0,
    )

    narrative = generate_section_narrative(
        st.session_state,
        selected_section,
        contexte_technique=context,
    )

    st.markdown(f"#### {selected_section}")
    st.write(narrative.get("intro", ""))

    for idx, paragraph in enumerate(narrative.get("paragraphs", []), start=1):
        with st.expander(f"Constat {idx}", expanded=(idx == 1)):
            st.write(paragraph)

    raw_rows = findings_by_section.get(selected_section, [])
    if not raw_rows:
        st.info("Aucune ligne détaillée disponible pour cette section.")
        return

    df = pd.DataFrame(
        [
            {
                "ID": row.get("controle_id", ""),
                "Libellé": row.get("libelle", ""),
                "Criticité": row.get("criticite", ""),
                "Verdict": row.get("verdict", ""),
                "Preuve documentaire": row.get("preuve_documentaire", ""),
                "Nb photos": len(row.get("photos", [])),
            }
            for row in raw_rows
        ]
    )

    if sort_mode == "criticite":
        order = {"critique": 1, "majeure": 2, "mineure": 3, "information": 4}
        df["_sort"] = df["Criticité"].map(order).fillna(99)
        df = df.sort_values(by=["_sort", "ID"]).drop(columns=["_sort"])
    elif sort_mode == "verdict":
        df = df.sort_values(by=["Verdict", "ID"])

    st.markdown("#### Tableau de contrôle")
    st.dataframe(df, hide_index=True, width="stretch")


def _render_action_plan_tab(context: dict[str, Any]) -> None:
    st.subheader("Plan d’actions")

    rows = generate_action_plan_table(
        st.session_state,
        contexte_technique=context,
    )

    if not rows:
        st.success("Aucune action corrective n’est actuellement générée.")
        return

    df = pd.DataFrame(rows).rename(
        columns={
            "priorite": "Priorité",
            "controle_id": "ID",
            "section": "Section",
            "objet": "Objet",
            "impact": "Impact",
            "action_recommandee": "Action recommandée",
            "preuves_disponibles": "Preuves disponibles",
        }
    )

    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "Priorité": st.column_config.Column(width="small"),
            "ID": st.column_config.Column(width="small"),
            "Section": st.column_config.Column(width="medium"),
            "Objet": st.column_config.Column(width="medium"),
            "Impact": st.column_config.Column(width="large"),
            "Action recommandée": st.column_config.Column(width="large"),
            "Preuves disponibles": st.column_config.Column(width="large"),
        },
    )

    priorities = df["Priorité"].value_counts().to_dict()
    c1, c2, c3 = st.columns(3)
    c1.metric("P1", priorities.get("P1", 0))
    c2.metric("P2", priorities.get("P2", 0))
    c3.metric("P3", priorities.get("P3", 0))


def _render_raw_report_tab(payload: dict[str, Any], context: dict[str, Any]) -> None:
    st.subheader("Prévisualisation du rapport")

    markdown_text = build_report_markdown(
        st.session_state,
        contexte_technique=context,
    )

    st.text_area(
        "Markdown généré",
        value=markdown_text,
        height=420,
    )

    st.download_button(
        label="Télécharger le brouillon Markdown",
        data=markdown_text.encode("utf-8"),
        file_name="rapport_audit_technique.md",
        mime="text/markdown",
        width="stretch",
    )

    with st.expander("Export JSON simplifié", expanded=False):
        json_bytes = BytesIO()
        json_bytes.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        json_bytes.seek(0)

        st.download_button(
            label="Télécharger un export JSON simplifié",
            data=json_bytes.getvalue(),
            file_name="rapport_audit_technique.json",
            mime="application/json",
            width="stretch",
        )


def main() -> None:
    context = _get_context_from_session()
    payload = build_report_data(st.session_state, contexte_technique=context)

    _render_header(context)
    _render_global_metrics(payload)
    _render_readiness_panel(payload)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Synthèse", "Constats", "Plan d'actions", "Studio OPT'HELIOS", "Export brut"]
    )

    with tab1:
        _render_executive_summary(payload)
        st.markdown("---")
        _render_expert_conclusion(payload)
        st.markdown("---")
        _render_top_actions(context)
        st.markdown("---")
        _render_section_summary_table(payload)
        st.markdown("---")
        _render_findings_overview(payload)

    with tab2:
        _render_findings_tab(payload, context)

    with tab3:
        _render_action_plan_tab(context)

    with tab4:
        render_studio_panel()

    with tab5:
        _render_raw_report_tab(payload, context)


def render() -> None:
    main()


if __name__ == "__main__":
    main()