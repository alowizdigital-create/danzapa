"""Sauvegarde de la base et des images dans DATA_DIR/sauvegardes.

    python manage.py sauvegarde            # garde les 14 dernières
    python manage.py sauvegarde --garder 30

Avec Docker :  docker exec <conteneur web> python manage.py sauvegarde
La copie de la base est cohérente même si l'application est utilisée pendant
la sauvegarde : pg_dump pour PostgreSQL (fichier base.sql), API de sauvegarde
de SQLite sinon (fichier db.sqlite3).
"""

import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Sauvegarde la base de données et les images des thèmes dans DATA_DIR/sauvegardes."

    def add_arguments(self, parser):
        parser.add_argument("--garder", type=int, default=14, help="Nombre de sauvegardes conservées (14 par défaut).")

    def handle(self, *args, garder, **options):
        dossier = Path(settings.DATA_DIR) / "sauvegardes"
        dossier.mkdir(parents=True, exist_ok=True)
        nom = f"danzapa-{timezone.localtime():%Y%m%d-%H%M%S}.tar.gz"
        archive = dossier / nom

        with tempfile.TemporaryDirectory() as temp:
            if connection.vendor == "postgresql":
                copie = self.copier_postgresql(Path(temp) / "base.sql")
            else:
                copie = self.copier_sqlite(Path(temp) / "db.sqlite3")

            with tarfile.open(archive, "w:gz") as tar:
                tar.add(copie, arcname=copie.name)
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

    def copier_sqlite(self, copie):
        connection.ensure_connection()
        destination = sqlite3.connect(copie)
        with destination:
            connection.connection.backup(destination)
        destination.close()
        return copie

    def copier_postgresql(self, copie):
        """Export SQL complet. Restauration : psql … < base.sql (voir DEPLOIEMENT.md)."""
        if not shutil.which("pg_dump"):
            raise CommandError("pg_dump introuvable : installer le paquet postgresql-client.")
        base = connection.settings_dict
        env = {
            **os.environ,
            "PGHOST": base["HOST"] or "localhost",
            "PGPORT": str(base["PORT"] or 5432),
            "PGUSER": base["USER"],
            "PGPASSWORD": base["PASSWORD"],
            "PGDATABASE": base["NAME"],
        }
        resultat = subprocess.run(
            ["pg_dump", "--no-owner", "--no-privileges", "--clean", "--if-exists", "--file", str(copie)],
            env=env,
            capture_output=True,
            text=True,
        )
        if resultat.returncode != 0:
            raise CommandError(f"pg_dump a échoué : {resultat.stderr.strip()}")
        return copie
