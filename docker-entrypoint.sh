#!/bin/sh
# Point d'entree Docker : recopie le secret Render (voir CHANGES.md,
# section Render.com) vers l'emplacement que l'appli lit nativement
# (.streamlit/secrets.toml), avant de lancer Streamlit.
#
# Sur Render, un "Secret File" uploade dans le dashboard du service est
# monte au runtime a un chemin FIXE : /etc/secrets/<nom-du-fichier>
# (pour les services Docker — voir la doc Render "Using Secrets with
# Docker"), pas a l'emplacement de notre choix. On uploade donc un fichier
# nomme exactement "secrets.toml" (meme contenu que le
# .streamlit/secrets.toml local), et ce script le recopie au bon endroit
# avant de demarrer l'appli — aucune modification du code Python
# necessaire, `services/sharepoint_auth.py` continue de lire
# `st.secrets["microsoft_app"]` exactement comme en local.
set -e

RENDER_SECRET=/etc/secrets/secrets.toml
LOCAL_SECRET=/app/.streamlit/secrets.toml

if [ -f "$RENDER_SECRET" ] && [ ! -f "$LOCAL_SECRET" ]; then
    mkdir -p /app/.streamlit
    cp "$RENDER_SECRET" "$LOCAL_SECRET"
    echo "[docker-entrypoint] secrets.toml recopie depuis $RENDER_SECRET"
fi

exec streamlit run app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true
