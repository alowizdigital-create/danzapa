"""Crée le premier administrateur au démarrage du conteneur, s'il n'existe pas.

Identifiant : DJANGO_SUPERUSER_USERNAME (config/production.env ou Dokploy).
Mot de passe : DJANGO_SUPERUSER_PASSWORD s'il est défini dans Dokploy, sinon un
mot de passe provisoire est généré et affiché une seule fois dans les logs.
Les démarrages suivants ne changent rien, sauf demande explicite :
DJANGO_SUPERUSER_RESET=1 avec DJANGO_SUPERUSER_PASSWORD remplace le mot de
passe du compte existant (mot de passe oublié, sans accès au terminal).
"""

import os
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.comptes import roles

# Sans caractères qui se confondent à la lecture (l/1/I, o/0/O).
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def mot_de_passe_provisoire():
    groupes = ("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(4))
    return "-".join(groupes)


class Command(BaseCommand):
    help = "Crée le premier administrateur (DJANGO_SUPERUSER_USERNAME) s'il n'existe pas."

    def handle(self, *args, **options):
        nom = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        if not nom:
            return
        mot_de_passe = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()
        Utilisateur = get_user_model()
        existant = Utilisateur.objects.filter(username=nom).first()

        if existant:
            if mot_de_passe and os.environ.get("DJANGO_SUPERUSER_RESET", "").strip().lower() in ("1", "true", "oui"):
                existant.set_password(mot_de_passe)
                existant.is_active = True
                existant.save(update_fields=["password", "is_active"])
                self.stdout.write(self.style.WARNING(
                    "#" * 60 + "\n"
                    f"  Mot de passe de « {nom} » remplacé par DJANGO_SUPERUSER_PASSWORD.\n"
                    "  RETIREZ MAINTENANT DJANGO_SUPERUSER_RESET et DJANGO_SUPERUSER_PASSWORD\n"
                    "  de l'onglet Environment de Dokploy : tant qu'ils y sont, tout mot de\n"
                    "  passe changé dans l'application est écrasé à chaque redémarrage.\n" + "#" * 60
                ))
            return

        provisoire = not mot_de_passe
        if provisoire:
            mot_de_passe = mot_de_passe_provisoire()

        admin = Utilisateur.objects.create_superuser(nom, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), mot_de_passe)
        admin.groups.add(Group.objects.get(name=roles.ADMINISTRATEUR))

        self.stdout.write(self.style.SUCCESS(f"Administrateur « {nom} » créé."))
        if provisoire:
            heure = timezone.localtime().strftime("%d/%m/%Y %H:%M")
            self.stdout.write(
                "=" * 60 + "\n"
                f"  Créé le {heure}\n"
                f"  Identifiant : {nom}\n"
                f"  Mot de passe provisoire : {mot_de_passe}\n"
                "  Connectez-vous puis changez-le (menu « Mot de passe »).\n"
                "  Il ne sera plus affiché.\n" + "=" * 60
            )
