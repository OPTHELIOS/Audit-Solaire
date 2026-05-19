"""UI Streamlit pour la brique OPT'HELIOS Audit Studio.

Ce module est volontairement isolé pour pouvoir être intégré dans plusieurs pages
(synthèse, export) sans dupliquer la logique de rendu.
"""

from __future__ import annotations

import streamlit as st

from domain.audit_studio import (
    FORMULATIONS_CATALOG,
    FORMULATIONS_BY_CODE,
    MODE_RAPPORT_DESCRIPTIONS,
    MODE_RAPPORT_LABELS,
    SCENARIOS_CATALOG,
    SCENARIOS_BY_CODE,
    AuditStudioBlock,
    FormulationSelection,
    ModeRapport,
    ScenarioSelection,
    search_formulations,
)
from ui.state import get_audit, save_audit


def _get_studio() -> AuditStudioBlock:
    audit = get_audit()
    if not hasattr(audit, "studio") or audit.studio is None:
        audit.studio = AuditStudioBlock()
        save_audit(audit)
    return audit.studio


def _render_mode_section(studio: AuditStudioBlock) -> None:
    st.subheader("Mode de rapport")
    st.caption(
        "Permet d'adapter le niveau de détail attendu : rapport complet ou note "
        "courte de diagnostic."
    )

    options = [m.value for m in ModeRapport]
    current = studio.mode_rapport.value if studio.mode_rapport else ModeRapport.audit_complet.value
    st.session_state.setdefault("studio_mode_rapport", current)

    selected = st.radio(
        "Profil de livrable",
        options=options,
        format_func=lambda code: MODE_RAPPORT_LABELS.get(code, code),
        horizontal=True,
        key="studio_mode_rapport",
    )

    st.caption(MODE_RAPPORT_DESCRIPTIONS.get(selected, ""))

    if selected != current:
        audit = get_audit()
        audit.set_mode_rapport(ModeRapport(selected))
        save_audit(audit)


def _render_scenarios_section(studio: AuditStudioBlock) -> None:
    st.subheader("Scénarios d'audit")
    st.caption(
        "Cocher les scénarios retenus pour l'installation auditée. La justification "
        "libre alimente le rapport final."
    )

    for scenario in SCENARIOS_CATALOG:
        existing = studio.get_scenario_selection(scenario.code)
        retenu_default = existing.retenu if existing else False
        commentaire_default = existing.commentaire if existing else ""

        with st.expander(
            f"{'✅ ' if retenu_default else ''}{scenario.libelle} — {scenario.horizon}",
            expanded=retenu_default,
        ):
            st.write(scenario.description)

            if scenario.conditions:
                st.markdown("**Conditions de pertinence :**")
                for cond in scenario.conditions:
                    st.write(f"- {cond}")

            if scenario.actions_types:
                st.markdown("**Actions types :**")
                for action in scenario.actions_types:
                    st.write(f"- {action}")

            if scenario.risques:
                st.markdown("**Points de vigilance :**")
                for risque in scenario.risques:
                    st.write(f"- {risque}")

            retenu_key = f"studio_scenario_retenu_{scenario.code}"
            comment_key = f"studio_scenario_comment_{scenario.code}"
            st.session_state.setdefault(retenu_key, retenu_default)
            st.session_state.setdefault(comment_key, commentaire_default)

            retenu = st.checkbox(
                "Scénario retenu pour cet audit",
                key=retenu_key,
            )
            commentaire = st.text_area(
                "Justification / contextualisation",
                key=comment_key,
                height=80,
            )

            if retenu != retenu_default or commentaire != commentaire_default:
                studio.upsert_scenario(scenario.code, retenu, commentaire)
                save_audit(get_audit())


def _render_formulations_section(studio: AuditStudioBlock) -> None:
    st.subheader("Bibliothèque de formulations OPT'HELIOS")
    st.caption(
        "Insertion rapide de formulations types capitalisées sur les audits "
        "précédents. Chaque formulation appliquée peut être personnalisée."
    )

    st.session_state.setdefault("studio_formulations_search", "")
    query = st.text_input(
        "Rechercher (titre, thème, mot-clé)", key="studio_formulations_search"
    )
    results = search_formulations(query)

    if not results:
        st.info("Aucune formulation ne correspond à la recherche.")
    else:
        codes = [f.code for f in results]
        selected_code = st.selectbox(
            "Formulation à appliquer",
            options=codes,
            format_func=lambda code: FORMULATIONS_BY_CODE[code].titre,
            key="studio_formulations_pick",
        )
        chosen = FORMULATIONS_BY_CODE[selected_code]

        with st.expander("Aperçu de la formulation", expanded=True):
            st.write(f"**Thème :** {chosen.theme}")
            st.write(f"**Constat type :** {chosen.constat}")
            st.write(f"**Impact type :** {chosen.impact}")
            st.write(f"**Recommandation type :** {chosen.recommandation}")

        with st.form("studio_formulation_apply_form", clear_on_submit=True):
            section = st.text_input("Section ciblée (libre)", value="")
            controle_id = st.text_input("ID de contrôle associé (optionnel)", value="")
            constat_perso = st.text_area(
                "Constat personnalisé (laisser vide pour reprendre le texte type)",
                value="",
                height=80,
            )
            impact_perso = st.text_area(
                "Impact personnalisé (laisser vide pour reprendre le texte type)",
                value="",
                height=80,
            )
            reco_perso = st.text_area(
                "Recommandation personnalisée (laisser vide pour reprendre le texte type)",
                value="",
                height=80,
            )
            submitted = st.form_submit_button("Appliquer cette formulation")

        if submitted:
            studio.add_formulation(
                code=selected_code,
                section=section.strip(),
                controle_id=controle_id.strip() or None,
                constat_personnalise=constat_perso.strip() or None,
                impact_personnalise=impact_perso.strip() or None,
                recommandation_personnalisee=reco_perso.strip() or None,
            )
            save_audit(get_audit())
            st.success(f"Formulation « {chosen.titre} » ajoutée à l'audit.")

    if studio.formulations:
        st.markdown("#### Formulations appliquées à cet audit")
        for idx, applied in enumerate(studio.formulations):
            template = FORMULATIONS_BY_CODE.get(applied.code)
            label = template.titre if template else applied.code
            with st.expander(
                f"{idx + 1}. {label} — {applied.section or 'section libre'}",
                expanded=False,
            ):
                st.write(
                    "**Constat retenu :** "
                    + (applied.constat_personnalise or (template.constat if template else ""))
                )
                st.write(
                    "**Impact retenu :** "
                    + (applied.impact_personnalise or (template.impact if template else ""))
                )
                st.write(
                    "**Recommandation retenue :** "
                    + (
                        applied.recommandation_personnalisee
                        or (template.recommandation if template else "")
                    )
                )
                if st.button("Retirer cette formulation", key=f"studio_formulation_del_{idx}"):
                    studio.remove_formulation(idx)
                    save_audit(get_audit())
                    st.rerun()


def _render_strategic_note(studio: AuditStudioBlock) -> None:
    st.subheader("Note stratégique de synthèse")
    st.caption(
        "Texte libre qui sera intégré au rapport final pour expliciter le choix des "
        "scénarios et le positionnement OPT'HELIOS."
    )
    st.session_state.setdefault("studio_note_strategique", studio.note_strategique)
    note = st.text_area(
        "Note stratégique",
        height=160,
        key="studio_note_strategique",
    )
    if note != studio.note_strategique:
        studio.note_strategique = note
        save_audit(get_audit())


def render_studio_panel() -> None:
    """Rend l'ensemble du panneau Audit Studio (à inclure dans un onglet)."""

    studio = _get_studio()

    _render_mode_section(studio)
    st.markdown("---")
    _render_scenarios_section(studio)
    st.markdown("---")
    _render_formulations_section(studio)
    st.markdown("---")
    _render_strategic_note(studio)


def render_studio_summary() -> None:
    """Rendu compact (lecture seule) du studio, utile dans la page export."""

    studio = _get_studio()

    st.markdown(
        f"**Mode de rapport :** {MODE_RAPPORT_LABELS.get(studio.mode_rapport.value, studio.mode_rapport.value)}"
    )

    selected = studio.selected_scenarios()
    if selected:
        st.markdown("**Scénarios retenus :**")
        for sel in selected:
            sc = SCENARIOS_BY_CODE.get(sel.code)
            label = sc.libelle if sc else sel.code
            st.write(f"- {label} ({sc.horizon if sc else ''})")
            if sel.commentaire:
                st.caption(sel.commentaire)
    else:
        st.caption("Aucun scénario retenu pour le moment.")

    if studio.formulations:
        st.markdown(f"**Formulations appliquées :** {len(studio.formulations)}")
    if studio.note_strategique:
        st.markdown("**Note stratégique :**")
        st.write(studio.note_strategique)
