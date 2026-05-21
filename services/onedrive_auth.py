import msal
import streamlit as st

SCOPES = [
    "Files.ReadWrite.AppFolder",
    "User.Read",
]

AUTHORITY = "https://login.microsoftonline.com/consumers"


class OneDriveNotConfiguredError(RuntimeError):
    """Levée quand les secrets Microsoft / OneDrive ne sont pas configurés."""


def _read_client_id() -> str:
    try:
        microsoft = st.secrets["microsoft"]
    except Exception as exc:
        raise OneDriveNotConfiguredError(
            "OneDrive non configuré : ajoute la section [microsoft] avec "
            "`client_id` dans `.streamlit/secrets.toml`."
        ) from exc

    try:
        client_id = microsoft["client_id"]
    except Exception as exc:
        raise OneDriveNotConfiguredError(
            "OneDrive non configuré : la clé `microsoft.client_id` est absente "
            "de `.streamlit/secrets.toml`."
        ) from exc

    if not client_id:
        raise OneDriveNotConfiguredError(
            "OneDrive non configuré : `microsoft.client_id` est vide."
        )

    return str(client_id)


def get_msal_app() -> msal.PublicClientApplication:
    client_id = _read_client_id()
    return msal.PublicClientApplication(
        client_id=client_id,
        authority=AUTHORITY,
    )


def get_access_token() -> str:
    app = get_msal_app()

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Impossible d'initialiser l'authentification Microsoft.")

    st.warning(
        "Authentification OneDrive requise.\n\n"
        f"Va sur {flow['verification_uri']} puis saisis le code : {flow['user_code']}"
    )

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(
            f"Échec authentification Microsoft : {result.get('error_description', 'erreur inconnue')}"
        )

    return result["access_token"]