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

        try_autosave_to_cloud(audit)
    except Exception:
        # L'autosave ne doit jamais faire planter une page.
        pass
