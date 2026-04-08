from __future__ import annotations

from typing import Any

import streamlit as st

from domain.control_catalog import Criticite, VerdictControle
from domain.control_service import (
    ControlServiceError,
    append_uploaded_evidences,
    build_action_plan,
    count_open_critical_findings,
    ensure_control_state,
    get_progress_by_section,
    get_section_responses,
    reset_response,
    summarize_controls,
    update_response,
)

PAGE_TITLE = "02 - Contrôles techniques"

VERDICT_LABELS = {
    "": "— Non renseigné —",
    VerdictControle.conforme.value: "Conforme",
    VerdictControle.non_conforme.value: "Non conforme",
    VerdictControle.non_verifiable.value: "Non vérifiable",
    VerdictControle.non_present.value: "Non présent",
    VerdictControle.sans_objet.value: "Sans objet",
}

CRITICITE_LABELS = {
    Criticite.critique.value: "Critique",
    Criticite.majeure.value: "Majeure",
    Criticite.mineure.value: "Mineure",
    Criticite.information.value: "Information",
}


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
        "Saisie structurée des contrôles techniques, constats terrain, preuves et recommandations."
    )

    with st.expander("Contexte technique utilisé pour l’applicabilité", expanded=False):
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


def _render_top_summary(context: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_controls(st.session_state, contexte_technique=context)
    critical_open = count_open_critical_findings(st.session_state, contexte_technique=context)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Points applicables", summary["total_applicables"])
    c2.metric("Taux de complétion", f"{summary['taux_completion_pct']} %")
    c3.metric("Taux de conformité", f"{summary['taux_conformite_pct']} %")
    c4.metric("NC critiques", critical_open)
    c5.metric("À renseigner", summary["compteurs"]["non_renseigne"])

    st.progress(
        min(max(summary["taux_completion_pct"] / 100.0, 0.0), 1.0),
        text="Progression globale de la campagne de contrôle",
    )

    return summary


def _render_sidebar(context: dict[str, Any]) -> dict[str, Any]:
    st.sidebar.header("Pilotage des contrôles")

    progress = get_progress_by_section(st.session_state, contexte_technique=context)
    sections = [row["section"] for row in progress]

    selected_section = st.sidebar.selectbox(
        "Section",
        options=["Toutes les sections"] + sections,
        index=0,
    )

    verdict_filter = st.sidebar.multiselect(
        "Filtrer par verdict",
        options=[
            VerdictControle.conforme.value,
            VerdictControle.non_conforme.value,
            VerdictControle.non_verifiable.value,
            VerdictControle.non_present.value,
            VerdictControle.sans_objet.value,
            "non_renseigne",
        ],
        default=[],
        format_func=lambda v: {
            VerdictControle.conforme.value: "Conforme",
            VerdictControle.non_conforme.value: "Non conforme",
            VerdictControle.non_verifiable.value: "Non vérifiable",
            VerdictControle.non_present.value: "Non présent",
            VerdictControle.sans_objet.value: "Sans objet",
            "non_renseigne": "Non renseigné",
        }[v],
    )

    criticite_filter = st.sidebar.multiselect(
        "Filtrer par criticité",
        options=[c.value for c in Criticite],
        default=[],
        format_func=lambda v: CRITICITE_LABELS[v],
    )

    only_incomplete = st.sidebar.checkbox("Afficher seulement les points non complétés", value=False)
    only_findings = st.sidebar.checkbox("Afficher seulement les écarts / réserves", value=False)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Avancement par section")
    for row in progress:
        st.sidebar.write(
            f"**{row['section']}** — {row['completed']}/{row['total']} ({row['completion_pct']} %)"
        )

    return {
        "sections": sections,
        "selected_section": None if selected_section == "Toutes les sections" else selected_section,
        "verdicts": set(verdict_filter),
        "criticites": set(criticite_filter),
        "only_incomplete": only_incomplete,
        "only_findings": only_findings,
    }


def _matches_filters(control_item: Any, response: Any, filters: dict[str, Any]) -> bool:
    if filters["selected_section"] and control_item.section != filters["selected_section"]:
        return False

    if filters["criticites"] and response.criticite_finale.value not in filters["criticites"]:
        return False

    if filters["verdicts"]:
        verdict_value = response.verdict.value if response.verdict else "non_renseigne"
        if verdict_value not in filters["verdicts"]:
            return False

    if filters["only_incomplete"] and response.verdict is not None:
        return False

    if filters["only_findings"] and response.verdict not in (
        VerdictControle.non_conforme,
        VerdictControle.non_present,
        VerdictControle.non_verifiable,
    ):
        return False

    return True


def _render_control_header(control_item: Any, response: Any) -> None:
    st.markdown(f"### {control_item.libelle}")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**ID** : `{control_item.controle_id}`")
    c2.markdown(
        f"**Criticité catalogue** : {CRITICITE_LABELS[control_item.criticite_par_defaut.value]}"
    )
    c3.markdown(f"**Criticité retenue** : {CRITICITE_LABELS[response.criticite_finale.value]}")

    if control_item.condition_applicabilite:
        st.caption(f"Applicabilité conditionnelle : {control_item.condition_applicabilite}")


def _render_control_help(control_item: Any) -> None:
    with st.expander("Référentiel de contrôle", expanded=False):
        if getattr(control_item, "description_controle", ""):
            st.write(f"**Description** : {control_item.description_controle}")
        st.write(f"**Méthode de vérification** : {control_item.methode_verification}")
        st.write(f"**Impact du défaut** : {control_item.impact_defaut}")
        st.write(f"**Recommandation type** : {control_item.recommandation_type}")
        st.write(f"**Preuve attendue** : {control_item.preuve_attendue}")
        if getattr(control_item, "tags", None):
            st.write(f"**Tags** : {', '.join(control_item.tags)}")


def _clear_form_keys(controle_id: str) -> None:
    for suffix in [
        "_verdict",
        "_criticite_finale",
        "_observation",
        "_recommandation",
        "_preuve_doc",
        "_raison_nv",
        "_uploader",
    ]:
        key = f"{controle_id}{suffix}"
        if key in st.session_state:
            del st.session_state[key]


def _render_existing_evidences(response: Any) -> None:
    if not response.photos:
        return

    with st.expander("Preuves déjà associées", expanded=False):
        for path in response.photos:
            st.code(path, language="text")


def _render_control_form(control_item: Any, response: Any, context: dict[str, Any]) -> None:
    verdict_default = response.verdict.value if response.verdict else ""
    criticite_default = response.criticite_finale.value

    options_verdict = [""] + [v.value for v in VerdictControle]
    options_criticite = [c.value for c in Criticite]

    with st.form(f"form_{control_item.controle_id}", clear_on_submit=False):
        _render_control_header(control_item, response)

        verdict = st.selectbox(
            "Verdict",
            options=options_verdict,
            index=options_verdict.index(verdict_default),
            format_func=lambda v: VERDICT_LABELS[v],
            key=f"{control_item.controle_id}_verdict",
        )

        criticite_finale = st.selectbox(
            "Criticité retenue",
            options=options_criticite,
            index=options_criticite.index(criticite_default),
            format_func=lambda v: CRITICITE_LABELS[v],
            key=f"{control_item.controle_id}_criticite_finale",
        )

        observation = st.text_area(
            "Observation terrain",
            value=response.observation,
            height=120,
            key=f"{control_item.controle_id}_observation",
            placeholder="Décris ici le constat terrain de manière factuelle, localisée et technique.",
        )

        recommandation = st.text_area(
            "Recommandation personnalisée",
            value=response.recommandation_personnalisee,
            height=100,
            key=f"{control_item.controle_id}_recommandation",
            placeholder=control_item.recommandation_type,
        )

        preuve_documentaire = st.text_input(
            "Preuve documentaire / référence / relevé",
            value=response.preuve_documentaire,
            key=f"{control_item.controle_id}_preuve_doc",
            placeholder="Ex. DOE, plaque signalétique, relevé régulation, supervision, mesure terrain…",
        )

        non_verifiable_raison = st.text_input(
            "Justification si non vérifiable",
            value=response.non_verifiable_raison,
            key=f"{control_item.controle_id}_raison_nv",
            placeholder="Renseigner obligatoirement si le point est non vérifiable.",
        )

        uploaded_files = st.file_uploader(
            "Ajouter des preuves (JPG, PNG, PDF)",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True,
            key=f"{control_item.controle_id}_uploader",
        )

        c1, c2 = st.columns(2)
        save_clicked = c1.form_submit_button("Enregistrer", use_container_width=True)
        reset_clicked = c2.form_submit_button("Réinitialiser", use_container_width=True)

    if reset_clicked:
        reset_response(
            st.session_state,
            control_item.controle_id,
            contexte_technique=context,
        )
        _clear_form_keys(control_item.controle_id)
        st.success(f"Contrôle {control_item.controle_id} réinitialisé.")
        st.rerun()

    if save_clicked:
        try:
            saved_paths = append_uploaded_evidences(
                uploaded_files or [],
                controle_id=control_item.controle_id,
                session_state=st.session_state,
                existing_paths=response.photos,
                base_dir="data/evidences",
            )

            update_response(
                st.session_state,
                control_item.controle_id,
                verdict=verdict or None,
                observation=observation,
                criticite_finale=criticite_finale,
                recommandation_personnalisee=recommandation,
                preuve_documentaire=preuve_documentaire,
                photos=saved_paths,
                non_verifiable_raison=non_verifiable_raison,
            )

            _clear_form_keys(control_item.controle_id)
            st.success(f"Contrôle {control_item.controle_id} enregistré.")
            st.rerun()

        except ControlServiceError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Erreur lors de l’enregistrement : {exc}")

    _render_existing_evidences(response)
    _render_control_help(control_item)


def _render_section(
    section: str,
    rows: list[dict[str, Any]],
    filters: dict[str, Any],
    context: dict[str, Any],
) -> None:
    visible_rows = [row for row in rows if _matches_filters(row["control"], row["response"], filters)]
    if not visible_rows:
        return

    nc_count = sum(
        1
        for row in visible_rows
        if row["response"].verdict in (VerdictControle.non_conforme, VerdictControle.non_present)
    )
    missing_count = sum(1 for row in visible_rows if row["response"].verdict is None)

    with st.expander(
        f"{section} — {len(visible_rows)} point(s), {nc_count} écart(s), {missing_count} non renseigné(s)",
        expanded=False,
    ):
        for idx, row in enumerate(visible_rows, start=1):
            control_item = row["control"]
            response = row["response"]

            st.markdown(f"## Point {idx}")
            _render_control_form(control_item, response, context)

            if idx < len(visible_rows):
                st.markdown("---")


def _render_action_plan_preview(context: dict[str, Any]) -> None:
    with st.expander("Aperçu du plan d’actions généré", expanded=False):
        actions = build_action_plan(st.session_state, contexte_technique=context)
        if not actions:
            st.info("Aucune action générée pour le moment.")
            return

        for action in actions[:20]:
            st.write(
                f"**{action['priorite']} — {action['controle_id']}** | "
                f"{action['section']} | {action['objet']}"
            )
            st.caption(action["action_recommandee"])


def main() -> None:
    context = _get_context_from_session()
    ensure_control_state(st.session_state, contexte_technique=context)

    _render_header(context)
    _render_top_summary(context)

    filters = _render_sidebar(context)
    sections = filters["sections"]

    if not sections:
        st.warning("Aucun contrôle applicable n’est disponible avec le contexte technique actuel.")
        return

    for section in sections:
        rows = get_section_responses(
            st.session_state,
            section,
            contexte_technique=context,
        )
        _render_section(section, rows, filters, context)

    _render_action_plan_preview(context)


if __name__ == "__main__":
    main()


def render() -> None:
    main()