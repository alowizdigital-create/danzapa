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
    # Base PostgreSQL (service « db » du docker-compose) : attendre qu'elle
    # accepte les connexions avant d'appliquer les migrations.
    essais=0
    until python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3).close()" 2>/tmp/attente-base; do
        essais=$((essais + 1))
        if [ "$essais" -ge 30 ]; then
            echo "Base PostgreSQL injoignable après 60 secondes :"
            cat /tmp/attente-base
            echo "Vérifier que le service « db » tourne (Dokploy → Logs du service db)."
            echo "« password authentication failed » : POSTGRES_PASSWORD a changé après"
            echo "le premier déploiement ; remettre l'ancienne valeur (voir DEPLOIEMENT.md)."
            exit 1
        fi
        echo "En attente de la base PostgreSQL… ($essais/30)"
        sleep 2
    done
    echo "Base PostgreSQL prête : comptes, chants et cultes sont conservés entre les déploiements."
fi

# Sans volume monté sur /data ni PostgreSQL, la base SQLite est dans le
# conteneur : elle (et le compte administrateur) seraient perdus au prochain
# déploiement.
if [ "$(stat -c %d "$DATA")" = "$(stat -c %d /)" ] && [ -z "${DATABASE_URL}${DATABASE_ENGINE}" ]; then
    echo "############################################################"
    echo "  ATTENTION : aucun volume n'est monté sur $DATA."
    echo "  Les chants, cultes et comptes seront PERDUS au prochain"
    echo "  déploiement. Déployer avec docker-compose.yml (service"
    echo "  Compose dans Dokploy, voir DEPLOIEMENT.md)."
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
