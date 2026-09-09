"""Tests de ui/state.py::_maybe_autosave et de l'indicateur de statut cloud
(app.py::_render_cloud_sync_status_sidebar).

Contexte (retour terrain, sept. 2026) : en chaufferie mal captée (réseau
mobile faible sur iPhone), un échec de sauvegarde cloud passait totalement
inaperçu — `services/autosave_service.py::try_autosave_to_cloud` renvoyait
juste `False` en silence, sans aucun retour à l'auditeur. Ces tests
verrouillent le nouveau comportement : tri-état de retour (True / False /
None), notification uniquement sur un changement d'état (pas de spam de
toast toutes les 20s en zone blanche), et l'indicateur de barre latérale ne
plante jamais, quel que soit l'état.
"""

import time
from unittest.mock import patch

import streamlit as st

import app as app_module
import ui.state as state
from domain.models import Audit


def _fresh_session_state(monkeypatch):
    fresh: dict = {}
    monkeypatch.setattr(st, "session_state", fresh, raising=False)
    return fresh


def test_maybe_autosave_ignores_unconfigured_cloud(monkeypatch):
    session_state = _fresh_session_state(monkeypatch)
    audit = Audit()

    with patch("services.autosave_service.try_autosave_to_cloud", return_value=None):
        state._maybe_autosave(audit)

    # Cloud non configure : on ne doit rien ecrire, sinon l'indicateur de
    # statut apparaitrait pour des auditeurs qui n'utilisent pas le cloud.
    assert state.CLOUD_SYNC_OK_KEY not in session_state


def test_maybe_autosave_records_success_and_timestamp(monkeypatch):
    session_state = _fresh_session_state(monkeypatch)
    session_state[state.AUTOSAVE_TS_KEY] = 0.0
    audit = Audit()

    with patch("services.autosave_service.try_autosave_to_cloud", return_value=True):
        state._maybe_autosave(audit)

    assert session_state[state.CLOUD_SYNC_OK_KEY] is True
    assert state.CLOUD_SYNC_LAST_OK_TS_KEY in session_state


def test_maybe_autosave_failure_keeps_previous_success_timestamp(monkeypatch):
    session_state = _fresh_session_state(monkeypatch)
    session_state[state.AUTOSAVE_TS_KEY] = 0.0
    audit = Audit()

    with patch("services.autosave_service.try_autosave_to_cloud", return_value=True):
        state._maybe_autosave(audit)
    previous_ts = session_state[state.CLOUD_SYNC_LAST_OK_TS_KEY]

    session_state[state.AUTOSAVE_TS_KEY] = 0.0  # force le throttle a laisser passer
    with patch("services.autosave_service.try_autosave_to_cloud", return_value=False):
        state._maybe_autosave(audit)

    assert session_state[state.CLOUD_SYNC_OK_KEY] is False
    # La derniere synchro reussie ne doit pas bouger sur un echec : c'est ce
    # qui permet d'afficher "derniere reussie il y a X min" a l'auditeur.
    assert session_state[state.CLOUD_SYNC_LAST_OK_TS_KEY] == previous_ts


def test_maybe_autosave_respects_throttle(monkeypatch):
    session_state = _fresh_session_state(monkeypatch)
    session_state[state.AUTOSAVE_TS_KEY] = time.time()
    audit = Audit()

    with patch("services.autosave_service.try_autosave_to_cloud", return_value=True) as mock_fn:
        state._maybe_autosave(audit)
        mock_fn.assert_not_called()


def test_cloud_sync_sidebar_indicator_never_crashes(monkeypatch):
    session_state = _fresh_session_state(monkeypatch)

    # Cle absente (cloud jamais tente / non configure) : ne doit rien faire.
    app_module._render_cloud_sync_status_sidebar()

    # A jour.
    session_state[state.CLOUD_SYNC_OK_KEY] = True
    app_module._render_cloud_sync_status_sidebar()

    # En echec, sans jamais avoir reussi.
    session_state[state.CLOUD_SYNC_OK_KEY] = False
    app_module._render_cloud_sync_status_sidebar()

    # En echec, avec une derniere reussite il y a 2 minutes.
    session_state[state.CLOUD_SYNC_LAST_OK_TS_KEY] = time.time() - 125
    app_module._render_cloud_sync_status_sidebar()
