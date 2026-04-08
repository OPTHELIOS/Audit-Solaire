import streamlit as st

from services.report_service import generate_html_report
from ui.state import get_audit


def render():
    audit = get_audit()

    st.header("11 - Rapport")
    st.caption("Génération du rapport HTML d'audit.")

    st.info(
        "Avant de générer le rapport, vérifie que le dossier, les contrôles, les preuves "
        "et la synthèse sont bien renseignés."
    )

    if st.button("Générer le rapport HTML", type="primary"):
        report_path = generate_html_report(audit)
        st.success(f"Rapport généré : {report_path}")

    st.markdown(
        """
Le rapport généré contient :
- l'identification du projet ;
- la synthèse de l'audit ;
- les constats techniques ;
- les preuves et annexes.
"""
    )