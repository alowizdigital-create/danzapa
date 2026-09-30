from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, TemplateView

from apps.chants.forms import ChantForm
from apps.chants.models import Chant
from apps.chants.recherche import filtrer, titres_d_abord

from apps.projection import pptx, rendu
from apps.projection.models import Theme

from . import diapos
from .forms import (
    AjoutChantForm,
    DuplicationForm,
    ElementForm,
    NouveauCulteForm,
    TexteLibreForm,
    parametres_form,
)
from .models import MOMENT_PAR_DEFAUT, Culte, ElementCulte


def peut_voir(vue):
    return login_required(permission_required("cultes.view_culte", raise_exception=True)(vue))


def peut_modifier(vue):
    return login_required(permission_required("cultes.change_culte", raise_exception=True)(vue))


def moments_connus():
    moments = set(ElementCulte.objects.exclude(moment="").values_list("moment", flat=True))
    moments.add(MOMENT_PAR_DEFAUT)
    return sorted(moments)


def contexte_espace(request, culte, selection=None):
    theme = culte.theme_effectif
    groupes = rendu.annoter(diapos.groupes_du_culte(culte), theme)
    return {
        "culte": culte,
        "theme": theme,
        "themes": Theme.objects.all(),
        "groupes": groupes,
        "a_des_elements": any(g.element for g in groupes),
        "total_diapos": sum(len(g.diapos) for g in groupes),
        "selection": selection,
        "peut_modifier": request.user.has_perm("cultes.change_culte"),
        "moments": moments_connus(),
        "maintenant": timezone.now(),
    }


def reponse_espace(request, culte, selection=None):
    """Après une modification : le fragment pour HTMX, sinon retour à l'éditeur."""
    culte.save(update_fields=["date_modification"])
    if request.headers.get("HX-Request"):
        return render(request, "cultes/_espace.html", contexte_espace(request, culte, selection))
    return redirect(culte)


# ---------------------------------------------------------------- Cultes


class CulteListe(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "cultes.view_culte"
    template_name = "cultes/liste.html"

    def get_context_data(self, **kwargs):
        aujourd_hui = timezone.localdate()
        return super().get_context_data(
            a_venir=Culte.objects.filter(date__gte=aujourd_hui).order_by("date", "pk"),
            passes=Culte.objects.filter(date__lt=aujourd_hui)[:30],
            form=NouveauCulteForm(initial={"date": prochain_dimanche(aujourd_hui)}),
            **kwargs,
        )


def prochain_dimanche(jour):
    return jour + timedelta(days=(6 - jour.weekday()) % 7)


class CulteCreation(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "cultes.add_culte"
    model = Culte
    form_class = NouveauCulteForm
    template_name = "cultes/nouveau.html"

    def get_initial(self):
        return {"date": prochain_dimanche(timezone.localdate())}

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        return super().form_valid(form)


class CulteSuppression(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "cultes.delete_culte"
    model = Culte
    template_name = "cultes/confirmer_suppression.html"
    success_url = reverse_lazy("cultes:liste")

    def form_valid(self, form):
        messages.success(self.request, f"« {self.object} » a été supprimé.")
        return super().form_valid(form)


@login_required
@permission_required("cultes.add_culte", raise_exception=True)
@require_POST
def dupliquer(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    form = DuplicationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choisissez une date valide pour la copie.")
        return redirect(culte)
    copie = culte.dupliquer(form.cleaned_data["date"], par=request.user)
    messages.success(request, f"« {culte} » a été copié dans « {copie} ».")
    return redirect(copie)


# ---------------------------------------------------------------- Éditeur


@peut_voir
def editeur(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    contexte = contexte_espace(request, culte)
    # Le premier chant d'un culte est en général le cantique d'entrée.
    contexte["moment_suggere"] = "" if contexte["a_des_elements"] else MOMENT_PAR_DEFAUT
    contexte["form_duplication"] = DuplicationForm(
        initial={"date": prochain_dimanche(max(culte.date, timezone.localdate()) + timedelta(days=1))}
    )
    return render(request, "cultes/editeur.html", contexte)


@peut_modifier
@require_POST
def parametres(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    form = parametres_form(request.POST, culte)
    if form is None:
        return HttpResponseBadRequest("Aucun paramètre reçu.")
    if not form.is_valid():
        return HttpResponseBadRequest(" ".join(e for erreurs in form.errors.values() for e in erreurs))
    form.save()
    return reponse_espace(request, culte)


@peut_voir
def chercher_chants(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    q = request.GET.get("q", "").strip()
    # Classement sur tous les résultats (titres seuls, requête légère), puis
    # chargement complet des 30 premiers.
    ids = [c.pk for c in titres_d_abord(filtrer(Chant.objects.only("pk", "titre"), q), q)[:30]]
    par_id = Chant.objects.prefetch_related("couplets").in_bulk(ids)
    chants = [par_id[i] for i in ids]
    deja = set(culte.elements.exclude(chant=None).values_list("chant_id", flat=True))
    return render(
        request,
        "cultes/_resultats_chants.html",
        {"culte": culte, "chants": chants, "q": q, "deja": deja},
    )


@peut_modifier
@require_POST
def ajouter_chant(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    form = AjoutChantForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Chant invalide.")
    chant = get_object_or_404(Chant, pk=form.cleaned_data["chant"])
    element = ElementCulte.objects.create(
        culte=culte,
        ordre=culte.prochain_ordre(),
        type=ElementCulte.CHANT,
        chant=chant,
        moment=form.cleaned_data["moment"].strip(),
    )
    return reponse_espace(request, culte, element.pk)


@peut_modifier
@require_POST
def ajouter_texte(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    form = TexteLibreForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Texte invalide.")
    element = form.save(commit=False)
    element.culte = culte
    element.type = ElementCulte.TEXTE
    element.ordre = culte.prochain_ordre()
    element.save()
    return reponse_espace(request, culte, element.pk)


@login_required
@permission_required(["cultes.change_culte", "chants.add_chant"], raise_exception=True)
def nouveau_chant(request, pk):
    """Saisir un chant qui n'est pas encore dans la bibliothèque et l'ajouter au culte."""
    culte = get_object_or_404(Culte, pk=pk)
    moment = request.POST.get("moment", request.GET.get("moment", "")).strip()
    form = ChantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.instance.cree_par = request.user
            chant = form.save()
            chant.remplacer_paroles(form.cleaned_data["paroles"])
            ElementCulte.objects.create(
                culte=culte,
                ordre=culte.prochain_ordre(),
                type=ElementCulte.CHANT,
                chant=chant,
                moment=moment,
            )
        culte.save(update_fields=["date_modification"])
        messages.success(request, f"« {chant} » a été ajouté à la bibliothèque et au culte.")
        return redirect(culte)
    return render(
        request,
        "cultes/nouveau_chant.html",
        {"culte": culte, "form": form, "moment": moment, "moments": moments_connus()},
    )


# ---------------------------------------------------------------- Éléments


def element_du_culte(pk, element_pk):
    return get_object_or_404(ElementCulte.objects.select_related("culte"), pk=element_pk, culte_id=pk)


@peut_modifier
@require_POST
def modifier_element(request, pk, element_pk):
    element = element_du_culte(pk, element_pk)
    form = ElementForm(request.POST, instance=element)
    if not form.is_valid():
        return HttpResponseBadRequest("Données invalides.")
    form.save()
    return reponse_espace(request, element.culte, element.pk)


@peut_modifier
@require_POST
def basculer_masque(request, pk, element_pk):
    element = element_du_culte(pk, element_pk)
    element.masque = not element.masque
    element.save(update_fields=["masque"])
    return reponse_espace(request, element.culte, element.pk)


@peut_modifier
@require_POST
def supprimer_element(request, pk, element_pk):
    element = element_du_culte(pk, element_pk)
    culte = element.culte
    element.delete()
    culte.renumeroter([])
    return reponse_espace(request, culte)


@peut_modifier
@require_POST
def deplacer_element(request, pk, element_pk):
    element = element_du_culte(pk, element_pk)
    culte = element.culte
    ids = list(culte.elements.values_list("pk", flat=True))
    i = ids.index(element.pk)
    j = i - 1 if request.POST.get("sens") == "haut" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
        culte.renumeroter(ids)
    return reponse_espace(request, culte, element.pk)


@peut_modifier
@require_POST
def reordonner(request, pk):
    culte = get_object_or_404(Culte, pk=pk)
    try:
        ids = [int(i) for i in request.POST.getlist("ordre")]
    except ValueError:
        return HttpResponseBadRequest("Ordre invalide.")
    culte.renumeroter(ids)
    selection = request.POST.get("selection")
    return reponse_espace(request, culte, int(selection) if selection and selection.isdigit() else None)


@peut_voir
def exporter_pptx(request, pk):
    culte = get_object_or_404(Culte.objects.select_related("theme"), pk=pk)
    reponse = HttpResponse(
        pptx.exporter(culte),
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    # Content-Disposition avec nom UTF-8 (accents) géré par Django.
    reponse.headers["Content-Disposition"] = content_disposition_header(True, pptx.nom_de_fichier(culte))
    return reponse
