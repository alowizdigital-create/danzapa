# Image de production de Danzapa (Django + Gunicorn + WhiteNoise).
# Données persistantes (base SQLite, images des thèmes) : volume sur /data.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_DEBUG=false \
    DATA_DIR=/data \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Fichiers statiques rassemblés à la construction (une clé temporaire suffit ici).
RUN DJANGO_SECRET_KEY=construction-uniquement python manage.py collectstatic --noinput \
    && useradd --create-home --uid 1000 danzapa \
    && mkdir -p /data \
    && chown -R danzapa:danzapa /data /app \
    && chmod +x docker/entrypoint.sh

# Le conteneur démarre en root uniquement pour donner /data à l'utilisateur
# « danzapa » (utile si le volume est un dossier de l'hôte appartenant à root),
# puis l'entrypoint relance tout sous cet utilisateur non privilégié.
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/sante/', timeout=4)" || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
