"""Tests du portail d'acces (services/app_auth.py).

Contexte : l'appli n'avait aucun controle d'acces, ce qui devenait
inacceptable des lors qu'elle est publiee sur une URL d'hebergeur — toute
personne disposant du lien aurait pu consulter les audits, les photos et les
adresses des clients, et declencher des ecritures dans le SharePoint
OPT'HELIOS via les identifiants embarques cote serveur.

Ces tests verrouillent la regle qui compte vraiment : SUR UN HEBERGEUR, UNE
CONFIGURATION D'AUTHENTIFICATION ABSENTE DOIT FERMER L'APPLI, JAMAIS
L'OUVRIR. C'est le piege classique du portail permissif — un secret mal
depose chez l'hebergeur, et l'appli se retrouve publique sans que personne
ne s'en apercoive, puisque tout continue de fonctionner normalement.
"""

import pathlib
from unittest.mock import patch

import services.app_auth as app_auth


# ---------------------------------------------------------------------
# gate_decision — fonction pure, coeur de la regle de securite
# ---------------------------------------------------------------------

def test_utilisateur_connecte_passe():
    assert (
        app_auth.gate_decision(auth_configured=True, hosted=True, logged_in=True)
        == app_auth.ALLOW
    )


def test_authentification_configuree_mais_non_connecte_demande_la_connexion():
    assert (
        app_auth.gate_decision(auth_configured=True, hosted=True, logged_in=False)
        == app_auth.LOGIN_REQUIRED
    )
    # Meme exigence en local des lors que l'authentification est configuree :
    # une fois `[auth]` presente, on ne contourne pas.
    assert (
        app_auth.gate_decision(auth_configured=True, hosted=False, logged_in=False)
        == app_auth.LOGIN_REQUIRED
    )


def test_hebergeur_sans_authentification_est_bloque():
    """LE test important : en ligne et non configure -> refus, pas d'acces."""
    assert (
        app_auth.gate_decision(auth_configured=False, hosted=True, logged_in=False)
        == app_auth.BLOCKED_MISCONFIGURED
    )


def test_hebergeur_sans_authentification_bloque_meme_si_un_jeton_traine():
    """Defense en profondeur : `logged_in` vrai sans configuration d'auth
    n'a pas de sens (cookie residuel, etat incoherent). Le refus doit primer
    plutot que d'accorder l'acces au benefice du doute."""
    assert (
        app_auth.gate_decision(auth_configured=False, hosted=True, logged_in=True)
        == app_auth.BLOCKED_MISCONFIGURED
    )


def test_local_sans_authentification_reste_utilisable():
    """Exiger une connexion Entra ID pour lancer l'appli sur son propre
    poste de developpement serait absurde : acces autorise, avec un
    avertissement affiche par require_login()."""
    assert (
        app_auth.gate_decision(auth_configured=False, hosted=False, logged_in=False)
        == app_auth.UNPROTECTED_LOCAL
    )


# ---------------------------------------------------------------------
# is_hosted — detection de l'exposition sur Internet
# ---------------------------------------------------------------------

def test_is_hosted_detecte_les_hebergeurs(monkeypatch):
    for var in app_auth.HOSTING_ENV_VARS:
        for name in app_auth.HOSTING_ENV_VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(var, "1")
        assert app_auth.is_hosted() is True, f"{var} non detectee"


def test_is_hosted_faux_en_local(monkeypatch):
    for name in app_auth.HOSTING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    assert app_auth.is_hosted() is False


def test_is_hosted_ignore_une_variable_vide(monkeypatch):
    """Une variable declaree mais vide ne signale pas un hebergeur."""
    for name in app_auth.HOSTING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RENDER", "")
    assert app_auth.is_hosted() is False


# ---------------------------------------------------------------------
# is_auth_configured — une configuration incomplete ne doit pas passer
# ---------------------------------------------------------------------

def _with_secrets(secrets):
    """Remplace st.secrets par un dictionnaire. `KeyError` sur une cle
    absente reproduit le comportement reel de st.secrets."""
    return patch.object(app_auth.st, "secrets", secrets)


AUTH_COMPLETE = {
    "auth": {
        "redirect_uri": "https://exemple.test/oauth2callback",
        "cookie_secret": "x" * 64,
        "microsoft": {
            "client_id": "id",
            "client_secret": "secret",
            "server_metadata_url": "https://login.microsoftonline.com/t/v2.0/.well-known/openid-configuration",
        },
    }
}


def test_configuration_complete_reconnue():
    with _with_secrets(AUTH_COMPLETE):
        assert app_auth.is_auth_configured() is True


def test_configuration_a_plat_reconnue():
    """Fournisseur unique non nomme : reglages directement sous [auth]."""
    plat = {
        "auth": {
            "redirect_uri": "https://exemple.test/oauth2callback",
            "cookie_secret": "x" * 64,
            "client_id": "id",
            "client_secret": "secret",
            "server_metadata_url": "https://exemple.test/.well-known/openid-configuration",
        }
    }
    with _with_secrets(plat):
        assert app_auth.is_auth_configured() is True


def test_section_auth_absente():
    with _with_secrets({"microsoft_app": {"tenant_id": "t"}}):
        assert app_auth.is_auth_configured() is False


def test_fournisseur_manquant_refuse():
    """`[auth]` presente mais aucun fournisseur : `st.login()` echouerait au
    clic. Mieux vaut le detecter avant d'ouvrir la page de connexion."""
    incomplet = {
        "auth": {
            "redirect_uri": "https://exemple.test/oauth2callback",
            "cookie_secret": "x" * 64,
        }
    }
    with _with_secrets(incomplet):
        assert app_auth.is_auth_configured() is False


def test_cookie_secret_manquant_refuse():
    ampute = {"auth": dict(AUTH_COMPLETE["auth"])}
    del ampute["auth"]["cookie_secret"]
    with _with_secrets(ampute):
        assert app_auth.is_auth_configured() is False


def test_redirect_uri_manquante_refuse():
    ampute = {"auth": dict(AUTH_COMPLETE["auth"])}
    del ampute["auth"]["redirect_uri"]
    with _with_secrets(ampute):
        assert app_auth.is_auth_configured() is False


def test_fournisseur_incomplet_refuse():
    """Fournisseur declare mais sans server_metadata_url."""
    bancal = {
        "auth": {
            "redirect_uri": "https://exemple.test/oauth2callback",
            "cookie_secret": "x" * 64,
            "microsoft": {"client_id": "id"},
        }
    }
    with _with_secrets(bancal):
        assert app_auth.is_auth_configured() is False


def test_secrets_illisibles_ne_font_pas_planter():
    """En l'absence totale de fichier de secrets, st.secrets leve. Le
    portail doit repondre "non configure", pas propager l'exception."""

    class SecretsQuiLeve(dict):
        def __getitem__(self, key):
            raise FileNotFoundError("aucun secrets.toml")

    with _with_secrets(SecretsQuiLeve()):
        assert app_auth.is_auth_configured() is False


# ---------------------------------------------------------------------
# _provider_name — nom passe a st.login()
# ---------------------------------------------------------------------

def test_provider_name_nomme():
    with _with_secrets(AUTH_COMPLETE):
        assert app_auth._provider_name() == "microsoft"


def test_provider_name_absent_si_configuration_a_plat():
    plat = {
        "auth": {
            "redirect_uri": "https://exemple.test/oauth2callback",
            "cookie_secret": "x" * 64,
            "client_id": "id",
            "server_metadata_url": "https://exemple.test/.well-known/openid-configuration",
        }
    }
    with _with_secrets(plat):
        assert app_auth._provider_name() is None


# ---------------------------------------------------------------------
# is_logged_in / current_user_label — robustesse
# ---------------------------------------------------------------------

def test_is_logged_in_faux_si_st_user_inexploitable():
    """Hors authentification configuree, st.user leve a l'acces. Le portail
    doit repondre "non connecte" plutot que faire planter l'appli."""

    class UserQuiLeve:
        @property
        def is_logged_in(self):
            raise RuntimeError("auth non configuree")

    with patch.object(app_auth.st, "user", UserQuiLeve()):
        assert app_auth.is_logged_in() is False
        assert app_auth.current_user_label() is None


# ---------------------------------------------------------------------
# Test d'integration sur l'APPLI REELLE (harnais officiel de Streamlit)
# ---------------------------------------------------------------------
# Les tests unitaires ci-dessus verifient la regle ; ceux-ci verifient
# qu'elle est effectivement appliquee par app.py. Sans eux, un simple
# oubli d'appel a require_login() dans main() laisserait tous les tests
# au vert avec une appli grande ouverte. Plus lents (le script complet est
# execute), mais ce sont ceux qui protegent reellement les donnees clients.

import pytest
from streamlit.testing.v1 import AppTest

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def sans_hebergeur(monkeypatch):
    for name in app_auth.HOSTING_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_integration_local_non_protege_affiche_lappli_et_avertit(sans_hebergeur):
    at = AppTest.from_file(APP, default_timeout=120).run()

    assert not at.exception, at.exception
    assert any(
        "non protégé" in w.value.lower() for w in at.sidebar.warning
    ), "l'avertissement d'acces non protege est absent"
    assert any(
        "Audit Solaire Thermique" in t.value for t in at.title
    ), "l'appli aurait du s'afficher normalement en local"


def test_integration_hebergeur_sans_auth_ferme_lappli(sans_hebergeur, monkeypatch):
    """LE test qui compte : publiee sans authentification, l'appli doit se
    fermer. On verifie non seulement qu'une erreur s'affiche, mais surtout
    qu'AUCUN contenu applicatif n'est rendu — un message d'erreur au-dessus
    d'une appli fonctionnelle ne protegerait rien."""
    monkeypatch.setenv("RENDER", "true")

    at = AppTest.from_file(APP, default_timeout=120).run()

    assert not at.exception, at.exception
    assert at.error, "aucune erreur affichee : l'appli serait restee ouverte"
    assert not at.title, "du contenu applicatif a ete rendu malgre le blocage"
    assert not at.sidebar.radio, "la navigation a ete rendue malgre le blocage"
