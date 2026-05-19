"""Régression : OneDrive ne doit pas crasher l'app sans secrets configurés."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.onedrive_auth import (
    OneDriveNotConfiguredError,
    _read_client_id,
    get_msal_app,
)


class _MissingSecrets(dict):
    """Stub `st.secrets` sans section microsoft."""

    def __getitem__(self, key):
        raise KeyError(key)


class _EmptyMicrosoft(dict):
    """Stub `st.secrets["microsoft"]` sans client_id."""

    def __getitem__(self, key):
        if key == "microsoft":
            return {}
        raise KeyError(key)


class TestReadClientIdRaisesNotConfigured(unittest.TestCase):
    def test_missing_microsoft_section_raises(self) -> None:
        with patch("services.onedrive_auth.st") as st_mock:
            st_mock.secrets = _MissingSecrets()
            with self.assertRaises(OneDriveNotConfiguredError):
                _read_client_id()

    def test_missing_client_id_raises(self) -> None:
        with patch("services.onedrive_auth.st") as st_mock:
            st_mock.secrets = _EmptyMicrosoft()
            with self.assertRaises(OneDriveNotConfiguredError):
                _read_client_id()

    def test_empty_client_id_raises(self) -> None:
        with patch("services.onedrive_auth.st") as st_mock:
            st_mock.secrets = {"microsoft": {"client_id": ""}}
            with self.assertRaises(OneDriveNotConfiguredError):
                _read_client_id()

    def test_get_msal_app_propagates_not_configured(self) -> None:
        with patch("services.onedrive_auth.st") as st_mock:
            st_mock.secrets = _MissingSecrets()
            with self.assertRaises(OneDriveNotConfiguredError):
                get_msal_app()


class TestListAuditsSurfacesNotConfigured(unittest.TestCase):
    def test_list_audits_raises_onedrive_not_configured(self) -> None:
        from repositories import onedrive_repository

        with patch(
            "repositories.onedrive_repository.get_access_token",
            side_effect=OneDriveNotConfiguredError("OneDrive non configuré"),
        ):
            with self.assertRaises(OneDriveNotConfiguredError):
                onedrive_repository.list_audits()


if __name__ == "__main__":
    unittest.main()
