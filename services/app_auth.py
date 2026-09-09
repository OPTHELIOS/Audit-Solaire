"""Controle d'acces a l'application (connexion Microsoft Entra ID).

POURQUOI CE MODULE : jusqu'ici l'appli n'avait aucune authentification, ce
qui etait sans consequence tant qu'elle tournait sur le poste de
l'auditeur. Des lors qu'elle est publiee sur une URL d'hebergeur, la meme
absence signifie que toute personne disposant du lien peut consulter les
audits, les photos et les adresses des clients, et declencher des ecritures
dans le SharePoint OPT'HELIOS via les identifiants `microsoft_app` embarques
cote serveur. Une URL d'hebergeur n'est pas devinable, mais elle n'est pas
secrete : elle circule par SMS, par mail, dans les historiques de
navigateur et les journaux des equipements traverses.

NE PAS CONFONDRE AVEC `services/sharepoint_auth.py`, qui authentifie
l'APPLICATION aupres de Microsoft Graph pour ecrire dans SharePoint sans
intervention humaine (mode "app-only"). Le present module authentifie
l'UTILISATEUR humain devant l'ecran. Les deux sont independants et
utilisent deliberement deux inscriptions d'application Azure distinctes :
celle de la sauvegarde detient des permissions d'ecriture larges avec
consentement administrateur, il serait malsain de la doubler d'un flux de
connexion utilisateur et de partager son secret. Voir CHANGES.md.

COMPORTEMENT EN L'ABSENCE DE CONFIGURATION — le point important. Laisser
passer quand la section `[auth]` est absente serait un piege : un secret mal
depose chez l'hebergeur rouvrirait silencieusement l'appli a tous. Le module
distingue donc les deux situations :

- en local (poste de developpement), acces autorise avec un avertissement
  visible : exiger une connexion Entra ID pour lancer l'appli sur son propre
  poste serait absurde ;
- sur un hebergeur, acces REFUSE avec un message explicite. Une erreur de
  configuration doit fermer l'appli, jamais l'ouvrir.
"""

from __future__ import annotations

import os

import streamlit as st

# Variables d'environnement posees par les hebergeurs courants. Leur seule
# presence signale "cette instance est exposee sur Internet", ce qui suffit
# a decider de fermer l'acces en cas de configuration manquante.
HOSTING_ENV_VARS = ("RENDER", "FLY_APP_NAME", "WEBSITE_SITE_NAME", "K_SERVICE")

# Etats possibles du portail. Valeurs decidees par `gate_decision`, une
# fonction pure — c'est elle qui porte les tests.
ALLOW = "allow"                          # utilisateur connecte, acces normal
LOGIN_REQUIRED = "login_required"        # authentification configuree, connexion a faire
UNPROTECTED_LOCAL = "unprotected_local"  # pas d'authentification, mais execution locale
BLOCKED_MISCONFIGURED = "blocked"        # pas d'authentification sur un hebergeur : refus


def gate_decision(auth_configured: bool, hosted: bool, logged_in: bool) -> str:
    """Decide de l'etat du portail. Fonction pure, sans dependance a
    Streamlit ni a l'environnement, afin d'etre testable directement."""
    if auth_configured:
        return ALLOW if logged_in else LOGIN_REQUIRED
    return BLOCKED_MISCONFIGURED if hosted else UNPROTECTED_LOCAL


def is_hosted() -> bool:
    """True si l'appli tourne chez un hebergeur (donc exposee sur Internet)."""
    return any(os.environ.get(name) for name in HOSTING_ENV_VARS)


def is_auth_configured() -> bool:
    """True si `[auth]` est presente et exploitable dans les secrets.

    On verifie les reglages partages (`redirect_uri`, `cookie_secret`) ET la
    presence d'au moins un fournisseur complet : une section `[auth]`
    incomplete ferait echouer `st.login()` au moment du clic, c'est-a-dire
    trop tard pour l'expliquer proprement.
    """
    try:
        auth = st.secrets["auth"]
    except Exception:
        return False

    try:
        if not auth.get("redirect_uri") or not auth.get("cookie_secret"):
            return False
        # Configuration a plat (fournisseur unique, non nomme).
        if auth.get("client_id") and auth.get("server_metadata_url"):
            return True
        # Fournisseur nomme, ex. [auth.microsoft].
        return any(
            isinstance(value, dict)
            and value.get("client_id")
            and value.get("server_metadata_url")
            for value in auth.values()
        )
    except Exception:
        return False


def is_logged_in() -> bool:
    """True si un utilisateur est connecte. Ne leve jamais : `st.user` n'est
    pas exploitable tant que l'authentification n'est pas configuree."""
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def current_user_label() -> str | None:
    """Nom ou adresse de l'utilisateur connecte, pour affichage."""
    try:
        return st.user.get("name") or st.user.get("email")
    except Exception:
        return None


def _provider_name() -> str | None:
    """Nom du fournisseur a passer a `st.login()`, ou None si la
    configuration est a plat (fournisseur unique non nomme)."""
    try:
        auth = st.secrets["auth"]
        if auth.get("client_id"):
            return None
        for key, value in auth.items():
            if isinstance(value, dict) and value.get("client_id"):
                return key
    except Exception:
        pass
    return None


def require_login(logo_path: str | None = None) -> None:
    """Portail d'entree. A appeler tout en haut de `main()`, avant toute
    lecture de donnees d'audit. Interrompt le script (`st.stop()`) tant que
    l'acces n'est pas accorde."""
    decision = gate_decision(
        auth_configured=is_auth_configured(),
        hosted=is_hosted(),
        logged_in=is_logged_in(),
    )

    if decision == ALLOW:
        return

    if decision == UNPROTECTED_LOCAL:
        st.sidebar.warning(
            "Accès non protégé : aucune authentification configurée. "
            "Normal en local ; à ne jamais laisser en ligne.",
            icon=":material/lock_open:",
        )
        return

    if decision == BLOCKED_MISCONFIGURED:
        st.error(
            "**Application non configurée — accès refusé.**\n\n"
            "Cette instance est publiée sur Internet mais aucune "
            "authentification n'est configurée. Par sécurité, l'accès est "
            "bloqué plutôt que laissé ouvert.\n\n"
            "Administrateur : ajouter la section `[auth]` aux secrets de "
            "l'hébergeur (voir `.streamlit/secrets.toml.example`).",
            icon=":material/gpp_maybe:",
        )
        st.stop()

    # decision == LOGIN_REQUIRED
    _, center, _ = st.columns([1, 2, 1])
    with center:
        if logo_path:
            try:
                st.image(logo_path, width="stretch")
            except Exception:
                pass
        st.title("Audit Solaire Thermique")
        st.caption(
            "Accès réservé aux collaborateurs OPT'HELIOS. "
            "Connectez-vous avec votre compte Microsoft professionnel."
        )
        if st.button(
            "Se connecter avec Microsoft",
            type="primary",
            width="stretch",
            icon=":material/login:",
        ):
            provider = _provider_name()
            if provider:
                st.login(provider)
            else:
                st.login()
    st.stop()


def render_user_sidebar() -> None:
    """Identite connectee et bouton de deconnexion, en pied de barre
    laterale. Sans effet si personne n'est connecte (execution locale non
    protegee)."""
    if not is_logged_in():
        return

    label = current_user_label()
    st.sidebar.markdown("---")
    if label:
        st.sidebar.caption(f"Connecté : {label}")
    if st.sidebar.button("Se déconnecter", width="stretch", icon=":material/logout:"):
        st.logout()
