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

# Premier administrateur, seulement si les variables sont définies et que le
# compte n'existe pas encore (les redémarrages suivants ne changent rien).
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py shell --no-imports -c "
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
U = get_user_model()
nom = os.environ['DJANGO_SUPERUSER_USERNAME']
if not U.objects.filter(username=nom).exists():
    u = U.objects.create_superuser(nom, os.environ.get('DJANGO_SUPERUSER_EMAIL', ''), os.environ['DJANGO_SUPERUSER_PASSWORD'])
    u.groups.add(Group.objects.get(name='Administrateur'))
    print(f'Administrateur « {nom} » créé.')
"
fi

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
