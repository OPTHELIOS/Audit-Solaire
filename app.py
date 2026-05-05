import streamlit as st
from PIL import Image

from ui.state import get_audit, init_session_state, save_audit as save_audit_session
from ui.pages import (
    _01_dossier,
    _02_controles,
    _03_preuves,
    _04_installation,
    _10_synthese,
)
from repositories.onedrive_repository import save_audit, load_audit, list_audits

logo = Image.open("assets/opthelios_logo.png")

st.set_page_config(
    page_title="OPT'HELIOS - Audit Solaire Thermique",
    page_icon=logo,
    layout="wide",
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

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Mettre à jour l'audit en session", type="secondary"):
            save_audit_session(audit)
            st.success("Audit mis à jour dans la session en cours.")

    with col2:
        if st.button("Sauvegarder dans OneDrive", type="primary"):
            save_audit_session(audit)
            audit_id = save_audit(audit)
            st.success(f"Audit sauvegardé dans OneDrive : {audit_id}")

    st.divider()
    st.subheader("Reprendre un audit sauvegardé")

    audits = list_audits()

    if not audits:
        st.info("Aucun audit sauvegardé dans OneDrive.")
    else:
        options = {}
        for a in audits:
            audit_id = a.get("audit_id", "")
            numero = a.get("numero_audit", "")
            commune = a.get("commune", "")
            date_modif = a.get("date_modification", "")
            label = f"{numero} | {commune} | {date_modif} | {audit_id}"
            options[label] = audit_id

        selected_label = st.selectbox(
            "Choisir un audit à rouvrir",
            list(options.keys()),
        )

        if st.button("Ouvrir l'audit sélectionné"):
            loaded_audit = load_audit(options[selected_label])

            if loaded_audit is None:
                st.error("Impossible de charger cet audit depuis OneDrive.")
            else:
                save_audit_session(loaded_audit)
                st.success("Audit rechargé avec succès.")
                st.rerun()


def main() -> None:
    init_session_state()

    st.sidebar.image("assets/opthelios_logo.png", use_container_width=True)
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