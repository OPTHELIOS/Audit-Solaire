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

PAGE_TITLE = "04 - Synthèse de l'audit"


def _get_context_from_session() -> dict[str, Any]:
    installation = st.session_state.get("installation_context", {})
    if not isinstance(installation, dict):
        installation = {}

    return {
        "systeme_capteurs": installation.get("systeme_capteurs"),
        "type_echangeur": installation.get("type_echangeur"),
        "type_stockage_solaire": installation.get("type_stockage_solaire"),
        "type_comptage": installation.get("type_comptage", []),
        "requires_monitoring": bool(installation.get("requires_monitoring", False)),
        "requires_telecontrole": bool(installation.get("requires_telecontrole", False)),
    }


def _render_header(context: dict[str, Any]) -> None:
    st.title(PAGE_TITLE)
    st.caption(
        "Lecture consolidée des constats, hiérarchisation des écarts et prévisualisation du contenu de rapport."
    )

    with st.expander("Contexte technique de synthèse", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Système capteurs** : {context.get('systeme_capteurs') or 'Non défini'}")
        c2.write(f"**Type échangeur** : {context.get('type_echangeur') or 'Non défini'}")
        c3.write(
            f"**Type stockage solaire** : {context.get('type_stockage_solaire') or 'Non défini'}"
        )

        c4, c5, c6 = st.columns(3)
        comptage = context.get("type_comptage") or []
        c4.write(f"**Type comptage** : {', '.join(comptage) if comptage else 'Non défini'}")
        c5.write(f"**Monitoring** : {'Oui' if context.get('requires_monitoring') else 'Non'}")
        c6.write(f"**Télécontrôle** : {'Oui' if context.get('requires_telecontrole') else 'Non'}")


def _render_global_metrics(payload: dict[str, Any]) -> None:
    ga = payload["global_assessment"]
    counts = payload["counts"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Statut global", ga["statut_global"])
    c2.metric("Taux de complétion", f"{ga['taux_completion_pct']} %")
    c3.metric("Taux de conformité", f"{ga['taux_conformite_pct']} %")
    c4.metric("Constats critiques", counts["critical_findings"])
    c5.metric("Constats majeurs", counts["major_findings"])

    st.progress(
        min(max(ga["taux_completion_pct"] / 100.0, 0.0), 1.0),
        text="Niveau de complétude de l’audit",
    )

    if ga["statut_global"] == "défavorable":
        st.error(ga["commentaire_global"])
    elif ga["statut_global"] in ("réserves majeures", "à consolider"):
        st.warning(ga["commentaire_global"])
    else:
        st.success(ga["commentaire_global"])


def _render_executive_summary(payload: dict[str, Any]) -> None:
    st.subheader("Synthèse exécutive")
    for line in payload["executive_summary"]:
        st.write(f"- {line}")

    st.markdown("#### Messages clés")
    for line in payload["key_messages"]:
        st.write(f"- {line}")

    st.markdown("#### Note méthodologique")
    for line in payload["methodology_note"]:
        st.write(f"- {line}")


def _render_section_summary_table(payload: dict[str, Any]) -> None:
    st.subheader("Vue par section")

    rows = payload["section_summaries"]
    if not rows:
        st.info("Aucun constat structurant n’est disponible pour le moment.")
        return

    df = pd.DataFrame(rows)
    rename_map = {
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
    df = df.rename(columns=rename_map)

    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "Section": st.column_config.Column(width="medium"),
            "Lecture": st.column_config.Column(width="large"),
        },
    )


def _render_findings_tab(payload: dict[str, Any], context: dict[str, Any]) -> None:
    st.subheader("Constats détaillés")

    sections = list(payload["findings_by_section"].keys())
    if not sections:
        st.info("Aucun constat rédigé n’est encore disponible.")
        return

    selected_section = st.selectbox(
        "Choisir une section à relire",
        options=sections,
        index=0,
    )

    narrative = generate_section_narrative(
        st.session_state,
        selected_section,
        contexte_technique=context,
    )

    st.markdown(f"#### {selected_section}")
    st.write(narrative["intro"])

    if not narrative["paragraphs"]:
        st.info("Aucun paragraphe disponible pour cette section.")
        return

    for idx, paragraph in enumerate(narrative["paragraphs"], start=1):
        with st.expander(f"Constat {idx}", expanded=(idx == 1)):
            st.write(paragraph)

    raw_rows = payload["findings_by_section"].get(selected_section, [])
    if raw_rows:
        st.markdown("#### Tableau de contrôle")
        table_rows = []
        for row in raw_rows:
            table_rows.append(
                {
                    "ID": row["controle_id"],
                    "Libellé": row["libelle"],
                    "Criticité": row["criticite"],
                    "Verdict": row["verdict"],
                    "Preuve documentaire": row["preuve_documentaire"],
                    "Nb preuves": len(row["photos"]),
                }
            )

        df = pd.DataFrame(table_rows)
        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
        )


def _render_action_plan_tab(payload: dict[str, Any], context: dict[str, Any]) -> None:
    st.subheader("Plan d’actions")

    rows = generate_action_plan_table(
        st.session_state,
        contexte_technique=context,
    )

    if not rows:
        st.success("Aucune action corrective n’est actuellement générée.")
        return

    df = pd.DataFrame(rows)
    df = df.rename(
        columns={
            "priorite": "Priorité",
            "controle_id": "ID",
            "section": "Section",
            "objet": "Objet",
            "impact": "Impact",
            "action_recommandee": "Action recommandée",
            "preuve_associee": "Preuve associée",
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
            "Preuve associée": st.column_config.Column(width="large"),
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
        height=500,
    )

    st.download_button(
        label="Télécharger le brouillon Markdown",
        data=markdown_text.encode("utf-8"),
        file_name="rapport_audit_technique.md",
        mime="text/markdown",
        width="stretch",
    )

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


def _render_findings_overview(payload: dict[str, Any]) -> None:
    st.subheader("Constats prioritaires")

    rows = payload["findings_flat"]
    if not rows:
        st.info("Aucun constat prioritaire à afficher.")
        return

    top_rows = [
        row for row in rows
        if row["criticite"] in {"critique", "majeure"}
    ]

    if not top_rows:
        st.info("Aucun constat critique ou majeur n’est actuellement recensé.")
        return

    for row in top_rows[:10]:
        criticity = row["criticite"].upper()
        with st.expander(f"{criticity} — {row['controle_id']} — {row['libelle']}", expanded=False):
            st.write(f"**Section** : {row['section']}")
            st.write(f"**Verdict** : {row['verdict']}")
            st.write(f"**Constat** : {row['phrase_constat']}")
            st.write(f"**Impact** : {row['phrase_impact']}")
            st.write(f"**Action** : {row['phrase_action']}")
            if row.get("preuve_documentaire"):
                st.write(f"**Preuve documentaire** : {row['preuve_documentaire']}")
            if row.get("photos"):
                st.write(f"**Nombre de fichiers de preuve** : {len(row['photos'])}")


def main() -> None:
    context = _get_context_from_session()
    payload = build_report_data(st.session_state, contexte_technique=context)

    _render_header(context)
    _render_global_metrics(payload)

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Synthèse",
            "Constats",
            "Plan d'actions",
            "Export brut",
        ]
    )

    with tab1:
        _render_executive_summary(payload)
        st.markdown("---")
        _render_section_summary_table(payload)
        st.markdown("---")
        _render_findings_overview(payload)

    with tab2:
        _render_findings_tab(payload, context)

    with tab3:
        _render_action_plan_tab(payload, context)

    with tab4:
        _render_raw_report_tab(payload, context)


if __name__ == "__main__":
    main()