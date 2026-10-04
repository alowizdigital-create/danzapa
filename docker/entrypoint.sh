#!/bin/sh
# Démarrage du conteneur : migrations, premier administrateur, puis Gunicorn.
set -e

DATA="${DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA/media"
    chown -R danzapa:danzapa "$DATA"
    export HOME=/home/danzapa
    exec setpriv --reuid=danzapa --regid=danzapa --init-groups "$0" "$@"
fi

mkdir -p "$DATA/media"

python manage.py migrate --noinput

# Premier administrateur (voir apps/comptes/management/commands/premier_admin.py).
python manage.py premier_admin

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
