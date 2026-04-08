import streamlit as st

from ui.state import get_audit, init_session_state, save_audit
from ui.pages import (
    _01_dossier,
    _02_controles,
    _03_preuves,
    _04_installation,
    _10_synthese,
)


st.set_page_config(
    page_title="OPT'HELIOS - Audit Solaire Thermique",
    layout="wide",
    page_icon="☀️",
)


def render_infos_audit() -> None:
    audit = get_audit()

    st.header("Infos audit")
    st.write(f"Numéro d'audit : {audit.meta.numero_audit}")
    st.write(f"Statut : {audit.meta.statut.value}")
    st.write(f"Date d'audit : {audit.meta.date_audit}")
    st.write(f"Auditeur : {audit.meta.auditeur or '-'}")

    st.write(f"Opération : {audit.projet.operation or '-'}")
    st.write(f"Commune : {audit.projet.adresse.commune or '-'}")

    st.write(f"Type installation : {audit.installation.type_installation or '-'}")
    st.write(f"Usage principal : {audit.installation.usage_principal or '-'}")
    st.write(
        f"Surface capteurs totale : "
        f"{audit.installation.champ_capteurs.surface_totale_m2 or '-'}"
    )
    st.write(
        f"Volume stockage : "
        f"{audit.installation.stockage_solaire.volume_total_litres or '-'}"
    )

    st.write(f"Nombre de constats : {len(audit.constats)}")
    st.write(f"Nombre de preuves : {len(audit.preuves)}")

    if st.button("Mettre à jour l'audit en session", type="primary"):
        save_audit(audit)
        st.success("Audit mis à jour dans la session en cours.")


def main() -> None:
    init_session_state()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Aller vers",
        [
            "Dossier",
            "Installation",
            "Contrôles techniques",
            "Preuves et annexes",
            "Synthèse",
            "Infos audit",
        ],
    )

    st.title("OPT'HELIOS - Audit Solaire Thermique")

    if page == "Dossier":
        _01_dossier.render()
    elif page == "Installation":
        _04_installation.render()
    elif page == "Contrôles techniques":
        _02_controles.render()
    elif page == "Preuves et annexes":
        _03_preuves.render()
    elif page == "Synthèse":
        _10_synthese.render()
    elif page == "Infos audit":
        render_infos_audit()


if __name__ == "__main__":
    main()