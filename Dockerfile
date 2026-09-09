# Image Docker de production pour l'appli OPT'HELIOS — Audit Solaire
# Thermique. Nécessaire pour tout hébergement avec NOM DE DOMAINE
# PERSONNALISÉ (Azure Container Apps, Render, Fly.io, Railway...) : voir
# CHANGES.md, section "Palier 1 — hébergement pro avec domaine
# personnalisé". Streamlit Community Cloud, à l'inverse, N'UTILISE PAS ce
# Dockerfile (déploiement direct depuis GitHub, cf. section
# "Déploiement cloud" plus bas dans CHANGES.md) et ne supporte pas de
# domaine personnalisé — uniquement un sous-domaine *.streamlit.app.
#
# Étapes :
# 1. Dépendances Python (requirements.txt).
# 2. Dépendance système LibreOffice (packages.txt), nécessaire à l'export
#    PDF côté serveur Linux (voir services/pdf_service.py).
# 3. Patch "présentation pro" : icônes + manifest PWA injectés dans le
#    <head> de la page (voir scripts/patch_streamlit_pwa.py). Défensif —
#    ne fait jamais échouer le build.

FROM python:3.12-slim

WORKDIR /app

# Dépendances système : celles de packages.txt (LibreOffice, pour l'export
# PDF côté serveur — voir services/pdf_service.py) + curl, utilisé
# uniquement par HEALTHCHECK ci-dessous (pas embarqué par défaut dans
# l'image de base python:3.12-slim).
COPY packages.txt .
RUN apt-get update \
    && xargs -a packages.txt apt-get install -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code de l'application.
COPY . .

# Icônes + manifest PWA injectés directement dans le build de Streamlit
# (voir le script pour le détail et les limites de cette approche).
RUN python scripts/patch_streamlit_pwa.py

RUN chmod +x docker-entrypoint.sh

# PORT est fixé par la plateforme d'hébergement au runtime (ex. Render :
# 10000 par défaut, personnalisable dans le dashboard) — voir
# docker-entrypoint.sh, qui lit cette variable avec un repli sur 8501 pour
# un lancement local (`docker run` sans variable PORT). EXPOSE et
# HEALTHCHECK ci-dessous restent cohérents avec ce même repli par défaut ;
# si tu fixes un PORT différent côté hébergeur, mets-le aussi à jour ici.
ENV PORT=8501
EXPOSE 8501

HEALTHCHECK CMD curl --fail "http://localhost:${PORT:-8501}/_stcore/health" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
