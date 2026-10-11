"""« Suivre le culte » : page publique, sans compte, à ouvrir sur un téléphone.

Un lien secret (Culte.jeton_partage) donne accès, en lecture seule, aux chants
et textes du culte, que chacun fait défiler à son rythme. Le lien se crée, se
renouvelle (l'ancien ne marche plus) ou se désactive depuis l'éditeur.
"""

import uuid
from dataclasses import dataclass, field

import segno
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.chants import paroles

from .models import Culte, ElementCulte


def lien_public(request, culte):
    if not culte.jeton_partage:
        return ""
    return request.build_absolute_uri(reverse("suivre", args=[culte.jeton_partage]))


def contexte_partage(request, culte):
    lien = lien_public(request, culte)
    qr = segno.make(lien, error="m").svg_inline(scale=5, border=2, dark="#0b1f4d") if lien else ""
    return {
        "culte": culte,
        "lien_partage": lien,
        "qr_partage": mark_safe(qr),
        "peut_modifier": request.user.has_perm("cultes.change_culte"),
    }


@login_required
@permission_required("cultes.change_culte", raise_exception=True)
@require_POST
def partager(request, pk):
    """Créer, renouveler ou désactiver le lien public du culte."""
    culte = get_object_or_404(Culte, uuid=pk)
    action = request.POST.get("action")
    if action == "activer" and not culte.jeton_partage or action == "renouveler":
        culte.jeton_partage = uuid.uuid4()
    elif action == "desactiver":
        culte.jeton_partage = None
    elif action != "activer":
        return HttpResponseBadRequest("Action inconnue.")
    culte.save(update_fields=["jeton_partage"])
    return render(request, "cultes/_partage.html", contexte_partage(request, culte))


# ---------------------------------------------------------------- Page publique


@dataclass
class Partie:
    """Un élément du culte tel qu'affiché sur le téléphone."""

    ancre: str
    type: str
    moment: str
    titre: str
    auteur: str = ""
    couplets: list = field(default_factory=list)  # HTML nettoyé (chants) ou lignes de texte
    image_url: str = ""


def parties_du_culte(culte):
    parties = []
    for rang, element in enumerate(culte.elements_complets().filter(masque=False), start=1):
        ancre = f"partie-{rang}"
        if element.type == ElementCulte.CHANT and element.chant:
            couplets = [mark_safe(d.contenu) for d in element.chant.diapos.all() if d.texte.strip()]
            parties.append(Partie(ancre, "chant", element.moment, element.chant.titre, element.chant.auteur, couplets))
        elif element.type == ElementCulte.IMAGE:
            url = element.image.url if element.image else ""
            parties.append(Partie(ancre, "image", element.moment, element.titre, image_url=url))
        else:
            couplets = paroles.decouper_paragraphes(element.contenu)
            parties.append(Partie(ancre, "texte", element.moment, element.titre or element.moment, couplets=couplets))
    return parties


def suivre(request, jeton):
    """Page publique (sans connexion) : le déroulé du culte, à faire défiler soi-même."""
    culte = get_object_or_404(Culte.objects.select_related("theme"), jeton_partage=jeton)
    reponse = render(
        request,
        "cultes/suivre.html",
        {"culte": culte, "parties": parties_du_culte(culte), "bienvenue": mark_safe(culte.bienvenue_html)},
    )
    reponse["X-Robots-Tag"] = "noindex, nofollow"
    return reponse
