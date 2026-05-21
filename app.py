from __future__ import annotations

import streamlit as st
from PIL import Image

import ui.pages._01_dossier as _01_dossier
import ui.pages._02_controles as _02_controles
import ui.pages._03_preuves as _03_preuves
import ui.pages._04_installation as _04_installation
import ui.pages._05_synthese as _05_synthese
import ui.pages._06_export as _06_export

from repositories.onedrive_repository import list_audits, load_audit, save_audit
from services.onedrive_auth import OneDriveNotConfiguredError
from ui.state import get_audit, init_session_state, save_audit as save_audit_session


LOGO_PATH = "assets/opthelios_logo.png"


def _load_logo() -> Image.Image | None:
    try:
        return Image.open(LOGO_PATH)
    except Exception:
        return None


logo = _load_logo()

st.set_page_config(
    page_title="OPT'HELIOS - Audit Solaire Thermique",
    page_icon=logo if logo is not None else None,
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
            try:
                audit_id = save_audit(audit)
                st.success(f"Audit sauvegardé dans OneDrive : {audit_id}")
            except OneDriveNotConfiguredError as exc:
                st.warning(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Échec sauvegarde OneDrive : {exc}")

    st.divider()
    st.subheader("Reprendre un audit sauvegardé")

    try:
        audits = list_audits()
    except OneDriveNotConfiguredError as exc:
        st.info(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Impossible de lister les audits OneDrive : {exc}")
        return

    if not audits:
        st.info("Aucun audit sauvegardé dans OneDrive.")
        return

    options: dict[str, str] = {}
    for item in audits:
        audit_id = item.get("audit_id", "")
        numero = item.get("numero_audit", "")
        commune = item.get("commune", "")
        date_modification = item.get("date_modification", "")
        label = f"{numero} | {commune} | {date_modification} | {audit_id}"
        options[label] = audit_id

    selected_label = st.selectbox(
        "Choisir un audit à rouvrir",
        list(options.keys()),
    )

    if st.button("Ouvrir l'audit sélectionné"):
        try:
            loaded_audit = load_audit(options[selected_label])
        except OneDriveNotConfiguredError as exc:
            st.warning(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"Échec du chargement OneDrive : {exc}")
            return

        if loaded_audit is None:
            st.error("Impossible de charger cet audit depuis OneDrive.")
        else:
            save_audit_session(loaded_audit)
            st.success("Audit rechargé avec succès.")
            st.rerun()


def main() -> None:
    init_session_state()

    if logo is not None:
        st.sidebar.image(LOGO_PATH, use_container_width=True)

    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Aller vers",
        [
            "Dossier",
            "Installation",
            "Contrôles techniques",
            "Preuves et annexes",
            "Synthèse",
            "Export",
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
        _05_synthese.render()
    elif page == "Export":
        _06_export.render()
    elif page == "Infos audit":
        render_infos_audit()


if __name__ == "__main__":
    main()