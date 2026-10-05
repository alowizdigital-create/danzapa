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

# Sans volume monté sur /data, la base est dans le conteneur : elle (et le compte
# administrateur) seraient perdus au prochain déploiement.
if [ "$(stat -c %d "$DATA")" = "$(stat -c %d /)" ] && [ -n "${DATABASE_URL}${DATABASE_ENGINE}" ]; then
    echo "Base PostgreSQL séparée : comptes, chants et cultes sont conservés."
    echo "(Sans volume /data, seules les images des thèmes seraient perdues au redéploiement.)"
elif [ "$(stat -c %d "$DATA")" = "$(stat -c %d /)" ]; then
    echo "############################################################"
    echo "  ATTENTION : aucun volume n'est monté sur $DATA."
    echo "  Les chants, cultes et comptes seront PERDUS au prochain"
    echo "  déploiement. Dokploy → Advanced → Volumes : ajouter un"
    echo "  Volume Mount « danzapa-data » sur $DATA, puis redéployer."
    echo "############################################################"
fi

python manage.py migrate --noinput

# Premier administrateur (voir apps/comptes/management/commands/premier_admin.py).
python manage.py premier_admin

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
