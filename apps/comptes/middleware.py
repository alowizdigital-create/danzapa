"""Mode « sans connexion » (temporaire) : DANZAPA_SANS_CONNEXION=true.

Chaque visiteur anonyme utilise le compte administrateur : les vues, les
permissions et le champ « créé par » fonctionnent sans modification. Pour
réactiver la connexion, retirer la variable (config/production.env) et
redéployer.
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model


def compte_par_defaut():
    Utilisateur = get_user_model()
    compte = Utilisateur.objects.filter(is_superuser=True, is_active=True).order_by("pk").first()
    if compte is None:
        nom = os.environ.get("DJANGO_SUPERUSER_USERNAME") or "admin"
        compte = Utilisateur.objects.filter(username=nom).first() or Utilisateur.objects.create_superuser(nom, password=None)
    return compte


class ConnexionAutomatique:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.CONNEXION_DESACTIVEE and not request.user.is_authenticated:
            request.user = compte_par_defaut()
        return self.get_response(request)
