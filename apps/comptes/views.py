from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.cultes.models import Culte


@login_required
def accueil(request):
    prochain = None
    if request.user.has_perm("cultes.view_culte"):
        prochain = Culte.objects.filter(date__gte=timezone.localdate()).order_by("date", "pk").first()
    return render(request, "accueil.html", {"prochain_culte": prochain})


def sante(request):
    """Vérification de bon fonctionnement (healthcheck Docker / Dokploy)."""
    with connection.cursor() as curseur:
        curseur.execute("SELECT 1")
    return HttpResponse("ok", content_type="text/plain")
