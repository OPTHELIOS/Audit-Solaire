"""Authentification Microsoft Graph en mode "app-only" (client credentials).

Remplace le flux "device code" de `services/onedrive_auth.py`, qui exigeait
qu'un auditeur se connecte interactivement (et se reconnecte a intervalles
reguliers) sur SON OneDrive personnel. Ici, l'application s'authentifie
elle-meme aupres d'Azure AD avec ses propres identifiants
(tenant_id / client_id / client_secret), sans JAMAIS demander a un humain de
se connecter. Consequence directe :

- la sauvegarde automatique fonctionne tout le temps, des la premiere
  utilisation, sur n'importe quelle tablette de n'importe quel auditeur,
  sans popup de connexion et sans reexpiration de session en plein audit ;
- les fichiers atterrissent dans un espace partage (site SharePoint /
  Teams) accessible a toute l'equipe, pas dans le OneDrive personnel de la
  personne qui a ouvert l'appli ce jour-la.

Contrepartie : ça necessite une inscription d'application dans le portail
Azure (Entra ID) du tenant Microsoft 365 d'OPT'HELIOS, avec le consentement
d'un administrateur. Voir CHANGES.md pour la marche a suivre pas-a-pas.

Configuration attendue dans `.streamlit/secrets.toml` (ou les secrets du
service d'hebergement) :

    [microsoft_app]
    tenant_id = "..."
    client_id = "..."
    client_secret = "..."
    site_id = "..."          # id du site SharePoint cible
    root_folder = "AuditsOPTHELIOS"   # optionnel, dossier racine dans la bibliotheque
"""

from __future__ import annotations

import msal
import streamlit as st

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def is_configured() -> bool:
    """True si les secrets necessaires sont presents, sans rien valider aupres d'Azure."""
    try:
        cfg = st.secrets["microsoft_app"]
        return bool(cfg.get("tenant_id") and cfg.get("client_id") and cfg.get("client_secret"))
    except Exception:
        return False


def _get_confidential_app() -> msal.ConfidentialClientApplication:
    cfg = st.secrets["microsoft_app"]
    authority = f"https://login.microsoftonline.com/{cfg['tenant_id']}"
    return msal.ConfidentialClientApplication(
        client_id=cfg["client_id"],
        client_credential=cfg["client_secret"],
        authority=authority,
    )


def get_app_only_token() -> str | None:
    """Recupere (ou reutilise depuis le cache MSAL en memoire) un jeton applicatif.

    Ne leve jamais d'exception : retourne None si les secrets sont absents,
    mal configures, ou si Azure AD refuse la demande (secret expire,
    consentement admin manquant...). C'est volontaire : ce jeton est utilise
    par la sauvegarde automatique, qui ne doit jamais faire planter une page
    Streamlit ni interrompre l'auditeur.
    """
    if not is_configured():
        return None

    try:
        app = _get_confidential_app()
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
        if result and "access_token" in result:
            return result["access_token"]
    except Exception:
        return None

    return None


def get_site_id() -> str | None:
    try:
        return st.secrets["microsoft_app"].get("site_id")
    except Exception:
        return None


def get_root_folder() -> str:
    try:
        return st.secrets["microsoft_app"].get("root_folder", "AuditsOPTHELIOS")
    except Exception:
        return "AuditsOPTHELIOS"
