from __future__ import annotations

import time

import streamlit as st
from PIL import Image

# CORRECTIF (lenteur au demarrage, signalee par l'utilisateur sept. 2026) :
# les 8 modules de pages ci-dessous etaient tous importes ici, en tete de
# fichier, donc executes a CHAQUE demarrage du serveur Streamlit — meme
# pour les pages jamais visitees pendant la session. Or plusieurs d'entre
# elles importent, a leur propre niveau module, des bibliotheques lourdes a
# charger (folium + geopy + streamlit_folium pour "Dossier", pandas pour
# "Synthese", python-docx pour "Export"...). Resultat : le premier lancement
# payait le cout d'import de TOUTES ces bibliotheques d'un coup, meme si
# l'auditeur n'utilise que 2-3 pages dans sa session. Chaque page est
# desormais importee a la demande, uniquement quand elle est reellement
# affichee (voir `main()` plus bas) : Python met de toute facon en cache un
# module deja importe (`sys.modules`), donc naviguer plusieurs fois vers la
# meme page ne recharge rien de plus qu'avant — seul le tout premier
# affichage de CETTE page precise a un cout d'import, au lieu que les 8
# pages le paient toutes au demarrage. Meme logique appliquee ci-dessous a
# `render_infos_audit()` : les imports SharePoint/MSAL (qui chargent
# `requests`/`msal`) sont deplaces a l'interieur de la fonction, puisque
# "Infos audit" n'est pas la page par defaut.
#
# CORRECTIF (sauvegarde automatique) : le depot OneDrive personnel
# (repositories/onedrive_repository.py, authentification "device code"
# interactive) est remplace par le depot SharePoint "app-only"
# (repositories/sharepoint_repository.py), qui n'exige plus qu'un auditeur
# se connecte manuellement. Voir CHANGES.md pour la configuration requise
# (secrets `microsoft_app`) et la marche a suivre cote Azure/M365.
from ui.state import CLOUD_SYNC_LAST_OK_TS_KEY, CLOUD_SYNC_OK_KEY, init_session_state


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


def _render_cloud_sync_status_sidebar() -> None:
    """Indicateur permanent (toutes pages) de l'etat de la derniere
    sauvegarde cloud automatique. Ajoute suite a un retour terrain : en
    chaufferie mal captee (reseau mobile faible), un echec de sauvegarde
    cloud passait totalement inaperçu (voir services/autosave_service.py) —
    l'auditeur n'avait aucun moyen de savoir que ses saisies ne partaient
    plus vers le cloud. Ne s'affiche que si la sauvegarde cloud a deja ete
    tentee au moins une fois dans cette session (cle absente si le cloud
    n'est pas configure) : aucun cout d'import supplementaire (lecture d'une
    simple valeur de session_state, pas de nouvel appel reseau ni de
    rechargement de `services/sharepoint_auth.py`)."""
    ok = st.session_state.get(CLOUD_SYNC_OK_KEY)
    if ok is None:
        return

    st.sidebar.markdown("---")
    if ok:
        st.sidebar.caption("☁️ Sauvegarde cloud à jour.")
        return

    last_ok = st.session_state.get(CLOUD_SYNC_LAST_OK_TS_KEY)
    if last_ok:
        minutes = max(int((time.time() - last_ok) / 60), 0)
        delay = f"il y a {minutes} min" if minutes > 0 else "à l'instant"
        detail = f"dernière réussie {delay}"
    else:
        detail = "aucune synchro réussie sur ce dossier depuis l'ouverture"

    st.sidebar.warning(
        f"⚠️ Sauvegarde cloud en attente (réseau ?) — {detail}. "
        "Vos saisies restent conservées dans cette session ; retentez "
        "depuis « Infos audit » une fois une meilleure connexion retrouvée.",
        icon="⚠️",
    )


# CORRECTIF (presentation pro, sept. 2026) : `page_icon` (onglet du
# navigateur) recevait jusqu'ici le logo RECTANGULAIRE complet
# (assets/opthelios_logo.png, 700x363 avec marge blanche). Un favicon est
# affiche minuscule (16-32 px) : le logo large y devenait un pate illisible.
# `assets/icons/favicon-32.png` est un recadrage carre, centre sur le seul
# disque solaire (sans le texte "OPT'HELIOS", illisible a cette taille),
# genere depuis le meme logo officiel. Le logo complet reste utilise tel
# quel dans la barre laterale (LOGO_PATH, plus bas), ou sa largeur passe
# bien. Memes fichiers que ceux prepares pour l'icone "Ajouter a l'ecran
# d'accueil" iOS/Android en cas de deploiement Docker (voir CHANGES.md).
FAVICON_PATH = "assets/icons/favicon-32.png"


def _load_logo(path: str) -> Image.Image | None:
    try:
        return Image.open(path)
    except Exception:
        return None


logo = _load_logo(LOGO_PATH)
favicon = _load_logo(FAVICON_PATH) or logo

st.set_page_config(
    page_title="OPT'HELIOS - Audit Solaire Thermique",
    page_icon=favicon if favicon is not None else None,
    layout="wide",
)


def render_infos_audit() -> None:
    # Imports paresseux (voir le CORRECTIF en tete de fichier) : "Infos
    # audit" n'est pas la page par defaut, inutile de charger requests/msal
    # au demarrage pour les auditeurs qui ne visitent jamais cette page.
    from repositories.sharepoint_repository import (
        SharePointNotConfigured,
        list_audits,
        load_audit,
        save_audit,
    )
    from services.audit_service import duplicate_audit
    from services.sharepoint_auth import is_configured as is_cloud_configured
    from ui.state import get_audit, save_audit as save_audit_session

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
    _render_cloud_sync_status_sidebar()

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
        import ui.pages._01_dossier as _01_dossier
        _01_dossier.render()
    elif page == "Installation":
        import ui.pages._04_installation as _04_installation
        _04_installation.render()
    elif page == "Documents fournis":
        import ui.pages._07_documents as _07_documents
        _07_documents.render()
    elif page == "Contrôles techniques":
        import ui.pages._02_controles as _02_controles
        _02_controles.render()
    elif page == "Preuves et annexes":
        import ui.pages._03_preuves as _03_preuves
        _03_preuves.render()
    elif page == "Mesures et comparaison":
        import ui.pages._08_mesures as _08_mesures
        _08_mesures.render()
    elif page == "Synthèse":
        import ui.pages._05_synthese as _05_synthese
        _05_synthese.render()
    elif page == "Export":
        import ui.pages._06_export as _06_export
        _06_export.render()
    elif page == "Infos audit":
        render_infos_audit()


if __name__ == "__main__":
    main()
