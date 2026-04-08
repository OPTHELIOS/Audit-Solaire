from __future__ import annotations

import streamlit as st

from domain.models import Audit
from services.audit_service import create_empty_audit


SESSION_AUDIT_KEY = "current_audit"


def init_session_state() -> None:
    if SESSION_AUDIT_KEY not in st.session_state:
        st.session_state[SESSION_AUDIT_KEY] = create_empty_audit()


def get_audit() -> Audit:
    init_session_state()
    return st.session_state[SESSION_AUDIT_KEY]


def set_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit


def save_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit


def reset_session_audit() -> None:
    st.session_state[SESSION_AUDIT_KEY] = create_empty_audit()


def update_audit(audit: Audit) -> None:
    st.session_state[SESSION_AUDIT_KEY] = audit