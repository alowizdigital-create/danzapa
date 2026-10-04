"""Crée le premier administrateur au démarrage du conteneur, s'il n'existe pas.

Identifiant : DJANGO_SUPERUSER_USERNAME (config/production.env ou Dokploy).
Mot de passe : DJANGO_SUPERUSER_PASSWORD s'il est défini dans Dokploy, sinon un
mot de passe provisoire est généré et affiché une seule fois dans les logs.
Les démarrages suivants ne changent rien.
"""

import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.comptes import roles


class Command(BaseCommand):
    help = "Crée le premier administrateur (DJANGO_SUPERUSER_USERNAME) s'il n'existe pas."

    def handle(self, *args, **options):
        nom = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        if not nom:
            return
        Utilisateur = get_user_model()
        if Utilisateur.objects.filter(username=nom).exists():
            return

        mot_de_passe = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()
        provisoire = not mot_de_passe
        if provisoire:
            mot_de_passe = secrets.token_urlsafe(12)

        admin = Utilisateur.objects.create_superuser(nom, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), mot_de_passe)
        admin.groups.add(Group.objects.get(name=roles.ADMINISTRATEUR))

        self.stdout.write(self.style.SUCCESS(f"Administrateur « {nom} » créé."))
        if provisoire:
            self.stdout.write(
                "=" * 60 + "\n"
                f"  Mot de passe provisoire de « {nom} » : {mot_de_passe}\n"
                "  Connectez-vous puis changez-le (menu « Mot de passe »).\n"
                "  Il ne sera plus affiché.\n" + "=" * 60
            )
