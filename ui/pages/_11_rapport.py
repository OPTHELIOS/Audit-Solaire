import streamlit as st

from services.report_service import generate_html_report
from ui.state import get_audit


def render() -> None:
    audit = get_audit()

    st.header("11 - Rapport")
    st.caption("Cette page est conservée provisoirement pour compatibilité, mais la génération du livrable a été centralisée.")

    st.info(
        "La génération principale du rapport a été déplacée vers la page "
        "**06 - Export du rapport**, qui regroupe désormais les exports DOCX, Markdown et JSON."
    )

    st.markdown(
        """
Utilise désormais la page **06 - Export du rapport** pour :
- vérifier la complétude du dossier ;
- renseigner les métadonnées du livrable ;
- générer le rapport DOCX ;
- exporter les versions Markdown et JSON.
"""
    )

    with st.expander("Accès technique provisoire au rapport HTML", expanded=False):
        st.warning(
            "Ce générateur HTML est conservé temporairement pour tests ou compatibilité, "
            "mais il ne doit plus être la voie principale de production du rapport."
        )

        if st.button("Générer le rapport HTML (mode technique)", type="secondary"):
            try:
                report_path = generate_html_report(audit)
                st.success(f"Rapport HTML généré : {report_path}")
            except Exception as exc:
                st.error(f"Impossible de générer le rapport HTML : {exc}")

    st.caption(
        "Recommandation : masquer cette page de la navigation dès que la page "
        "06 - Export du rapport couvre entièrement ton besoin."
    )