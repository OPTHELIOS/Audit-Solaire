from __future__ import annotations

import streamlit as st
from PIL import Image

import ui.pages._01_dossier as _01_dossier
import ui.pages._02_controles as _02_controles
import ui.pages._03_preuves as _03_preuves
import ui.pages._04_installation as _04_installation
import ui.pages._05_synthese as _05_synthese
import ui.pages._06_export as _06_export
import ui.pages._07_documents as _07_documents
import ui.pages._08_mesures as _08_mesures

# CORRECTIF (sauvegarde automatique) : le depot OneDrive personnel
# (repositories/onedrive_repository.py, authentification "device code"
# interactive) est remplace par le depot SharePoint "app-only"
# (repositories/sharepoint_repository.py), qui n'exige plus qu'un auditeur
# se connecte manuellement. Voir CHANGES.md pour la configuration requise
# (secrets `microsoft_app`) et la marche a suivre cote Azure/M365.
from repositories.sharepoint_repository import (
    SharePointNotConfigured,
    list_audits,
    load_audit,
    save_audit,
)
from services.audit_service import duplicate_audit
from services.sharepoint_auth import is_configured as is_cloud_configured
from ui.state import get_audit, init_session_state, save_audit as save_audit_session


LOGO_PATH = "assets/opthelios_logo.png"


def _get_context_from_session() -> dict:
    installation = st.session_state.get("installation_context", {})
    if not isinstance(installation, dict):
        installation = {}

    return {
        "systeme_capteurs": installation.get("systeme_capteurs"),
        "type_echangeur": installation.get("type_echangeur"),
        "type_stockage_solaire": (
            installation.get("type_stockage_solaire") or installation.get("type_stockage")
        ),
        "type_comptage": installation.get("type_comptage", []),
        "requires_monitoring": bool(installation.get("requires_monitoring", False)),
        "requires_telecontrole": bool(installation.get("requires_telecontrole", False)),
    }


def _render_global_progress_sidebar() -> None:
    """Progression globale de l'audit, visible dans la barre latérale sur
    TOUTES les pages (pas seulement sur "Contrôles techniques") : utile pour
    garder un repère constant sans devoir naviguer pour le consulter."""
    audit = st.session_state.get("audit")
    if audit is None:
        return

    try:
        from domain.control_service import summarize_controls

        context = _get_context_from_session()
        summary = summarize_controls(st.session_state, contexte_technique=context)
    except Exception:
        return

    st.sidebar.markdown("---")
    st.sidebar.caption("Avancement global de l'audit")
    st.sidebar.progress(
        min(max(summary["taux_completion_pct"] / 100.0, 0.0), 1.0),
        text=f"{summary['taux_completion_pct']} % complété · {summary['taux_conformite_pct']} % conforme",
    )


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

    if is_cloud_configured():
        st.caption("☁️ Sauvegarde automatique active (site SharePoint partagé, sans connexion requise).")
    else:
        st.warning(
            "Sauvegarde cloud non configurée : les secrets `microsoft_app` "
            "(tenant_id, client_id, client_secret, site_id) sont absents ou incomplets. "
            "L'audit ne vit que dans cette session tant que ce n'est pas configuré — "
            "voir CHANGES.md pour la marche à suivre."
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Mettre à jour l'audit en session", type="secondary"):
            save_audit_session(audit)
            st.success("Audit mis à jour dans la session en cours.")

    with col2:
        if st.button("Forcer la sauvegarde maintenant", type="primary"):
            save_audit_session(audit)
            try:
                audit_id = save_audit(audit)
                st.success(f"Audit sauvegardé : {audit_id}")
            except SharePointNotConfigured as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Échec de la sauvegarde : {exc}")

    st.divider()
    st.subheader("Dupliquer cet audit")
    st.caption(
        "Crée un nouvel audit à partir de celui-ci : reprend l'installation, le maître "
        "d'ouvrage/exploitant/mainteneur (utile pour un site similaire du même parc), "
        "mais repart à zéro sur l'adresse, les constats et les preuves."
    )
    if st.button("Dupliquer cet audit comme point de départ"):
        new_audit = duplicate_audit(audit)
        save_audit_session(new_audit)
        st.success(
            "Nouvel audit créé à partir de celui-ci. Rends-toi sur la page Dossier "
            "pour renseigner l'adresse et les infos du nouveau site."
        )
        st.rerun()

    st.divider()
    st.subheader("Reprendre un audit sauvegardé")

    try:
        audits = list_audits()
    except SharePointNotConfigured as exc:
        st.info(str(exc))
        return
    except Exception as exc:
        st.error(f"Impossible de lister les audits sauvegardés : {exc}")
        return

    if not audits:
        st.info("Aucun audit sauvegardé pour le moment.")
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
        except Exception as exc:
            st.error(f"Impossible de charger cet audit : {exc}")
            loaded_audit = None

        if loaded_audit is None:
            st.error("Impossible de charger cet audit.")
        else:
            save_audit_session(loaded_audit)
            st.success("Audit rechargé avec succès.")
            st.rerun()


def main() -> None:
    init_session_state()

    if logo is not None:
        st.sidebar.image(LOGO_PATH, use_container_width=True)

    st.sidebar.title("Navigation")

    _render_global_progress_sidebar()

    page = st.sidebar.radio(
        "Aller vers",
        [
            "Dossier",
            "Installation",
            "Documents fournis",
            "Contrôles techniques",
            "Preuves et annexes",
            "Mesures et comparaison",
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
    elif page == "Documents fournis":
        _07_documents.render()
    elif page == "Contrôles techniques":
        _02_controles.render()
    elif page == "Preuves et annexes":
        _03_preuves.render()
    elif page == "Mesures et comparaison":
        _08_mesures.render()
    elif page == "Synthèse":
        _05_synthese.render()
    elif page == "Export":
        _06_export.render()
    elif page == "Infos audit":
        render_infos_audit()


if __name__ == "__main__":
    main()
