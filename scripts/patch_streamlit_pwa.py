#!/usr/bin/env python3
"""Patch "présentation pro" exécuté au build de l'image Docker (voir
`Dockerfile`), PAS en local ni sur Streamlit Community Cloud.

Streamlit ne propose aucune option officielle pour injecter des balises
dans le <head> de la page (favicon complet, icône "Ajouter à l'écran
d'accueil" iOS, manifest PWA pour Android). La seule méthode qui fonctionne
réellement (les injections via st.markdown/st.components ne le permettent
pas : le contenu y est isolé dans un <iframe>, sans accès au <head> du
document parent) consiste à modifier directement le fichier `index.html`
compilé, livré à l'intérieur du paquet `streamlit` lui-même, une fois cette
dépendance installée dans l'image Docker.

Conséquence assumée : ce patch dépend de la structure interne du build
front-end de Streamlit, qui peut changer d'une version à l'autre. Le script
est donc défensif de bout en bout (jamais d'exception qui ferait échouer le
build) : si `index.html` introuvable ou déjà d'une forme inattendue, il
log un avertissement et NE FAIT RIEN plutôt que de produire une image
cassée. L'appli reste alors utilisable normalement, simplement sans icône
"Ajouter à l'écran d'accueil" soignée (repli sur le favicon standard,
lui-même correctement configuré indépendamment de ce script — voir
`app.py::FAVICON_PATH`).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

MARKER = "<!-- opthelios-pwa-patch -->"

# NB : concatenation et non f-string — le script d'enregistrement du service
# worker ci-dessous contient des accolades, qu'une f-string interpreterait
# comme des champs de substitution.
HEAD_INJECTION = MARKER + """
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1C1E3D">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Opt'Audit">
<!-- Equivalent standard de `apple-mobile-web-app-capable`, desormais la
     forme recommandee et celle que lit Chrome/Android. Les deux sont
     conservees : iOS ne reconnait que la variante prefixee `apple-`. -->
<meta name="mobile-web-app-capable" content="yes">
<script>
  // Enregistrement du service worker (voir assets/pwa/sw.js) : condition
  // pour que Chrome/Android propose "Installer l'application", et pour
  // afficher un ecran OPT'HELIOS plutot que l'erreur brute du navigateur
  // en cas de coupure reseau. Un echec ici est sans consequence sur le
  // fonctionnement de l'appli : on se contente de le journaliser.
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function (err) {
        console.warn("[opthelios] service worker non enregistre :", err);
      });
    });
  }
</script>
"""

ASSET_FILES = [
    "apple-touch-icon.png",
    "icon-192.png",
    "icon-512.png",
    "icon-maskable-512.png",
    "favicon.ico",
    "favicon-32.png",
    "favicon-16.png",
    "manifest.json",
]

# Fichiers du mode "appli" servis depuis assets/pwa/. Separes des icones
# ci-dessus parce qu'ils portent du comportement, pas de la presentation.
# `sw.js` DOIT etre servi a la racine du site : la portee d'un service
# worker est limitee au dossier d'ou il est servi, et il doit donc couvrir
# "/" pour controler toute l'appli.
PWA_FILES = [
    "sw.js",
    "offline.html",
]


def _find_streamlit_static_dir() -> Path | None:
    try:
        import streamlit
    except Exception as exc:  # pragma: no cover - streamlit non installe
        print(f"[patch_streamlit_pwa] streamlit non importable, patch ignore : {exc}")
        return None

    static_dir = Path(streamlit.__file__).parent / "static"
    if not static_dir.is_dir():
        print(f"[patch_streamlit_pwa] dossier static introuvable ({static_dir}), patch ignore.")
        return None
    return static_dir


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    source_assets = repo_root / "assets" / "icons"
    if not source_assets.is_dir():
        print(f"[patch_streamlit_pwa] {source_assets} introuvable, patch ignore.")
        return 0

    static_dir = _find_streamlit_static_dir()
    if static_dir is None:
        return 0

    index_html = static_dir / "index.html"
    if not index_html.is_file():
        print(f"[patch_streamlit_pwa] {index_html} introuvable, patch ignore.")
        return 0

    try:
        html = index_html.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[patch_streamlit_pwa] lecture de index.html impossible ({exc}), patch ignore.")
        return 0

    if MARKER in html:
        print("[patch_streamlit_pwa] deja applique, rien a faire.")
        return 0

    if "<head>" not in html:
        print("[patch_streamlit_pwa] balise <head> introuvable dans index.html, patch ignore.")
        return 0

    # Copie des icones/manifest et des fichiers du mode "appli" a la racine
    # du dossier static de Streamlit (servi tel quel a la racine de l'appli,
    # ex. /favicon.ico, /sw.js), pour que les chemins absolus references
    # dans HEAD_INJECTION fonctionnent.
    #
    # assets/pwa/ est traite comme optionnel au meme titre que le reste :
    # absent, l'appli garde ses icones et son plein ecran, elle perd
    # seulement l'installabilite Android et l'ecran de repli hors reseau.
    sources = [
        (source_assets, ASSET_FILES),
        (repo_root / "assets" / "pwa", PWA_FILES),
    ]
    for source_dir, filenames in sources:
        for filename in filenames:
            source = source_dir / filename
            if not source.is_file():
                print(f"[patch_streamlit_pwa] {source} manquant, ignore.")
                continue
            try:
                shutil.copy2(source, static_dir / filename)
            except Exception as exc:
                print(f"[patch_streamlit_pwa] copie de {filename} impossible ({exc}), ignore.")

    patched_html = html.replace("<head>", f"<head>\n{HEAD_INJECTION}", 1)

    try:
        index_html.write_text(patched_html, encoding="utf-8")
    except Exception as exc:
        print(f"[patch_streamlit_pwa] ecriture de index.html impossible ({exc}), patch ignore.")
        return 0

    print(f"[patch_streamlit_pwa] OK : {index_html} et icônes patchés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
