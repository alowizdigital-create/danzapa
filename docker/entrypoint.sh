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

if [ -n "${DATABASE_URL}" ]; then
    # Base PostgreSQL (service Database de Dokploy) : attendre qu'elle
    # accepte les connexions avant d'appliquer les migrations.
    essais=0
    until python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3).close()" 2>/tmp/attente-base; do
        essais=$((essais + 1))
        if [ "$essais" -ge 30 ]; then
            echo "Base PostgreSQL injoignable après 60 secondes :"
            cat /tmp/attente-base
            echo "Vérifier que la base tourne (Dokploy → page de la base → Deploy / Logs)"
            echo "et que DATABASE_URL est bien l'« Internal Connection URL » de la base."
            exit 1
        fi
        echo "En attente de la base PostgreSQL… ($essais/30)"
        sleep 2
    done
    hote=$(python -c "import os; from urllib.parse import urlsplit; print(urlsplit(os.environ['DATABASE_URL']).hostname)")
    echo "Base de données : PostgreSQL (hôte $hote) — comptes, chants et cultes sont conservés entre les déploiements."
else
    echo "Base de données : SQLite ($DATA/db.sqlite3)."
fi

# Sans volume monté sur /data ni PostgreSQL, la base SQLite est dans le
# conteneur : elle (et le compte administrateur) seraient perdus au prochain
# déploiement.
if [ "$(stat -c %d "$DATA")" = "$(stat -c %d /)" ] && [ -z "${DATABASE_URL}${DATABASE_ENGINE}" ]; then
    echo "############################################################"
    echo "  ATTENTION : aucun volume n'est monté sur $DATA."
    echo "  Les chants, cultes et comptes seront PERDUS au prochain"
    echo "  déploiement. Dokploy : créer une base PostgreSQL et ajouter"
    echo "  DATABASE_URL dans Environment (voir DEPLOIEMENT.md)."
    echo "############################################################"
fi

if [ "$(stat -c %d "$DATA")" = "$(stat -c %d /)" ] && [ -n "${DATABASE_URL}" ]; then
    echo "Note : sans volume sur $DATA, les images envoyées (diapos image, thèmes)"
    echo "ne sont pas conservées. Dokploy → Advanced → Volumes : danzapa-data sur $DATA."
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
