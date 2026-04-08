import streamlit as st

from services.audit_service import touch_audit
from services.scoring_service import compute_synthese
from ui.state import get_audit, save_audit

SESSION_CONCLUSION_KEY = "synthese_conclusion_expert"


def _safe_get(obj, attr, default="-"):
    return getattr(obj, attr, default)


def render() -> None:
    audit = get_audit()

    st.header("10 - Synthèse")
    st.caption("Calcul automatique des indicateurs de synthèse de l'audit.")

    if st.button("Calculer la synthèse", type="primary"):
        try:
            audit.synthese = compute_synthese(audit)
            audit = touch_audit(audit)
            save_audit(audit)
            st.success("Synthèse calculée et enregistrée dans la session.")
            st.rerun()
        except Exception as exc:
            st.error(f"Impossible de calculer la synthèse : {exc}")
            return

    synthese = getattr(audit, "synthese", None)

    if synthese is None:
        st.info("Aucune synthèse disponible pour le moment.")
        return

    st.subheader("Indicateurs")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Contrôles totaux", _safe_get(synthese, "nb_controles_total", 0))
        st.metric("Conformes", _safe_get(synthese, "nb_conformes", 0))
        st.metric("Défauts", _safe_get(synthese, "nb_defauts", 0))

    with col2:
        st.metric("Non contrôlables", _safe_get(synthese, "nb_non_controlables", 0))
        st.metric("Sans objet", _safe_get(synthese, "nb_sans_objet", 0))
        st.metric("Non renseignés", _safe_get(synthese, "nb_non_renseignes", 0))

    with col3:
        st.metric("Preuves", _safe_get(synthese, "nb_preuves", 0))
        st.metric("Complétude (%)", _safe_get(synthese, "score_completude_sur_100", 0) or 0)
        st.metric("Score global (%)", _safe_get(synthese, "score_global_sur_100", 0) or 0)

    st.subheader("Niveau de risque")
    st.write(_safe_get(synthese, "niveau_risque", "-"))

    st.subheader("Résumé exécutif")
    st.write(_safe_get(synthese, "resume_executif", "-"))

    st.subheader("Conclusion expert")
    conclusion = st.text_area(
        "Conclusion libre",
        value=st.session_state.get(SESSION_CONCLUSION_KEY, ""),
        placeholder="Saisir ici une conclusion technique libre...",
        height=150,
    )

    if st.button("Enregistrer la conclusion"):
        st.session_state[SESSION_CONCLUSION_KEY] = conclusion
        st.success("Conclusion enregistrée dans la session.")