from __future__ import annotations

import time

import streamlit as st

from domain.models import Audit
from services.audit_service import create_empty_audit

SESSION_AUDIT_KEY = "audit"
LEGACY_SESSION_AUDIT_KEY = "current_audit"

# Sauvegarde automatique : throttle pour eviter de retenter un appel reseau
# a chaque frappe/interaction Streamlit. 20s est un compromis entre
# reactivite (peu de perte en cas de coupure) et cout reseau/latence UI.
# Avec l'authentification app-only (voir services/sharepoint_auth.py), ce
# throttle est la SEULE raison de ne pas sauvegarder a chaque frappe : il
# n'y a plus de notion de "session utilisateur non connectee".
AUTOSAVE_TS_KEY = "_last_autosave_attempt_ts"
AUTOSAVE_MIN_INTERVAL_SECONDS = 20

# CORRECTIF (visibilite de l'echec d'autosave, sept. 2026 — reseau mobile
# faible en chaufferie) : ces deux cles memorisent l'etat du DERNIER essai
# de sauvegarde cloud (True/False) et l'horodatage de la DERNIERE reussite,
# pour que `app.py` puisse afficher un indicateur permanent dans la barre
# laterale ("cloud a jour" / "cloud en attente, reseau ?") au lieu de ne
# rien montrer du tout en cas d'echec. Absentes de session_state tant que
# le cloud n'est pas configure (voir `_maybe_autosave`), pour ne rien
# afficher chez un auditeur qui n'utilise pas la sauvegarde cloud.
CLOUD_SYNC_OK_KEY = "_cloud_sync_ok"
CLOUD_SYNC_LAST_OK_TS_KEY = "_cloud_sync_last_ok_ts"


def init_session_state() -> None:
    if SESSION_AUDIT_KEY in st.session_state and st.session_state[SESSION_AUDIT_KEY] is not None:
        return

    if LEGACY_SESSION_AUDIT_KEY in st.session_state and st.session_state[LEGACY_SESSION_AUDIT_KEY] is not None:
        st.session_state[SESSION_AUDIT_KEY] = st.session_state[LEGACY_SESSION_AUDIT_KEY]
        return

    audit = create_empty_audit()
    st.session_state[SESSION_AUDIT_KEY] = audit
    st.session_state[LEGACY_SESSION_AUDIT_KEY] = audit


def get_audit() -> Audit:
    init_session_state()
    return st.session_state[SESSION_AUDIT_KEY]


def set_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit
    st.session_state[LEGACY_SESSION_AUDIT_KEY] = audit


def save_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit
    st.session_state[LEGACY_SESSION_AUDIT_KEY] = audit
    _maybe_autosave(audit)


def reset_session_audit() -> None:
    audit = create_empty_audit()
    st.session_state[SESSION_AUDIT_KEY] = audit
    st.session_state[LEGACY_SESSION_AUDIT_KEY] = audit


def update_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit
    st.session_state[LEGACY_SESSION_AUDIT_KEY] = audit
    _maybe_autosave(audit)


def autosave_now(audit: Audit) -> None:
    """Point d'entree explicite pour les pages qui ne passent pas par
    `save_audit` (ex. ui/pages/_02_controles.py, qui met a jour
    `st.session_state["audit"]` directement via `domain/control_service.py`)."""
    _maybe_autosave(audit)


def _maybe_autosave(audit: Audit) -> None:
    now = time.time()
    last = st.session_state.get(AUTOSAVE_TS_KEY, 0.0)
    if now - last < AUTOSAVE_MIN_INTERVAL_SECONDS:
        return

    st.session_state[AUTOSAVE_TS_KEY] = now

    try:
        from services.autosave_service import try_autosave_to_cloud

        result = try_autosave_to_cloud(audit)
    except Exception:
        # L'autosave ne doit jamais faire planter une page.
        result = False

    if result is None:
        # Cloud non configure : ne rien afficher (voir CLOUD_SYNC_OK_KEY).
        return

    previous = st.session_state.get(CLOUD_SYNC_OK_KEY)
    st.session_state[CLOUD_SYNC_OK_KEY] = result
    if result:
        st.session_state[CLOUD_SYNC_LAST_OK_TS_KEY] = now

    # Notification uniquement sur un CHANGEMENT d'etat (reussite -> echec ou
    # l'inverse), jamais a chaque tentative : sinon, en zone blanche
    # (chaufferie mal captee), l'auditeur recevrait un toast d'echec toutes
    # les 20 secondes pendant toute sa visite. L'etat courant reste
    # consultable en permanence via l'indicateur de la barre laterale
    # (voir app.py::_render_cloud_sync_status_sidebar).
    if previous is not None and previous != result:
        try:
            if result:
                st.toast("Connexion cloud retrouvée : sauvegarde à jour.", icon="☁️")
            else:
                st.toast(
                    "Sauvegarde cloud impossible pour le moment (réseau ?) — "
                    "vos saisies restent conservées dans cette session.",
                    icon="⚠️",
                )
        except Exception:
            pass
