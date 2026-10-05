from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.chants.models import Chant
from apps.cultes.models import Culte


@login_required
def accueil(request):
    prochain = None
    if request.user.has_perm("cultes.view_culte"):
        prochain = Culte.objects.filter(date__gte=timezone.localdate()).order_by("date", "pk").first()
    return render(request, "accueil.html", {"prochain_culte": prochain, "nb_chants": Chant.objects.count()})


def sante(request):
    """Vérification de bon fonctionnement (healthcheck Docker / Dokploy)."""
    with connection.cursor() as curseur:
        curseur.execute("SELECT 1")
    # Toujours 200 (le conteneur fonctionne) ; l'absence de volume est signalée.
    message = "ok" if settings.DONNEES_PERSISTANTES else "ok (sans volume /data : données non conservées)"
    return HttpResponse(message, content_type="text/plain")
