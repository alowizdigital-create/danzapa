"""Sauvegarde de la base et des images dans DATA_DIR/sauvegardes.

    python manage.py sauvegarde            # garde les 14 dernières
    python manage.py sauvegarde --garder 30

Avec Docker :  docker exec <conteneur> python manage.py sauvegarde
La copie de la base SQLite est cohérente même si l'application est utilisée
pendant la sauvegarde (API de sauvegarde de SQLite).
"""

import sqlite3
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Sauvegarde la base SQLite et les images des thèmes dans DATA_DIR/sauvegardes."

    def add_arguments(self, parser):
        parser.add_argument("--garder", type=int, default=14, help="Nombre de sauvegardes conservées (14 par défaut).")

    def handle(self, *args, garder, **options):
        if connection.vendor != "sqlite":
            raise CommandError("Base PostgreSQL : utilisez les sauvegardes de base de données de Dokploy (pg_dump).")

        dossier = Path(settings.DATA_DIR) / "sauvegardes"
        dossier.mkdir(parents=True, exist_ok=True)
        nom = f"danzapa-{timezone.localtime():%Y%m%d-%H%M%S}.tar.gz"
        archive = dossier / nom

        with tempfile.TemporaryDirectory() as temp:
            copie = Path(temp) / "db.sqlite3"
            connection.ensure_connection()
            destination = sqlite3.connect(copie)
            with destination:
                connection.connection.backup(destination)
            destination.close()

            with tarfile.open(archive, "w:gz") as tar:
                tar.add(copie, arcname="db.sqlite3")
                media = Path(settings.MEDIA_ROOT)
                if media.exists():
                    tar.add(media, arcname="media")

        anciennes = sorted(dossier.glob("danzapa-*.tar.gz"))[:-garder] if garder > 0 else []
        for fichier in anciennes:
            fichier.unlink()

        taille = archive.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {archive} ({taille:.0f} Ko)"))
        if anciennes:
            self.stdout.write(f"{len(anciennes)} ancienne(s) sauvegarde(s) supprimée(s).")
