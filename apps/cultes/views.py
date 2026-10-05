from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, TemplateView

from apps.chants.forms import ChantInfosForm, DiapoChantForm, NouveauChantForm
from apps.chants.models import Chant, DiapoChant
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


def contexte_espace(request, culte, selection=None, edition=None, piece=None):
    """Contexte du fragment #espace.

    `selection` : élément du culte à afficher ; `edition` : chant ouvert en
    mode édition ; `piece` : diapo de ce chant à sélectionner.
    """
    theme = culte.theme_effectif
    groupes = rendu.annoter(diapos.groupes_du_culte(culte), theme)
    return {
        "edition": edition,
        "piece": piece,
        "peut_editer_chants": request.user.has_perm("chants.change_chant"),
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


def reponse_espace(request, culte, selection=None, edition=None, piece=None):
    """Après une modification : le fragment pour HTMX, sinon retour à l'éditeur."""
    culte.save(update_fields=["date_modification"])
    if request.headers.get("HX-Request"):
        return render(request, "cultes/_espace.html", contexte_espace(request, culte, selection, edition, piece))
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
    par_id = Chant.objects.prefetch_related("diapos", "utilisations").in_bulk(ids)
    chants = [par_id[i] for i in ids]
    deja = set(culte.elements.exclude(chant=None).values_list("chant_id", flat=True))
    return render(
        request,
        "cultes/_resultats_chants.html",
        {"culte": culte, "chants": chants, "q": q, "deja": deja, "message": getattr(request, "message_resultats", "")},
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


# ---------------------------------------------------------------- Chants (saisie en place)


def peut_creer_chant(vue):
    return login_required(
        permission_required(["cultes.change_culte", "chants.add_chant"], raise_exception=True)(vue)
    )


def peut_editer_chant(vue):
    return login_required(permission_required("chants.change_chant", raise_exception=True)(vue))


def chant_du_culte(pk, chant_pk):
    """Le chant, à condition qu'il fasse partie de ce culte."""
    culte = get_object_or_404(Culte, pk=pk)
    element = get_object_or_404(culte.elements.select_related("chant"), chant_id=chant_pk)
    return culte, element, element.chant


def premiere_erreur(form):
    return next((e for erreurs in form.errors.values() for e in erreurs), "Données invalides.")


@peut_creer_chant
@require_POST
def creer_chant(request, pk):
    """« Nouveau chant » : crée le chant dans la bibliothèque, l'ajoute au culte,
    et ouvre l'éditeur sur sa première diapo."""
    culte = get_object_or_404(Culte, pk=pk)
    form = NouveauChantForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(premiere_erreur(form))
    with transaction.atomic():
        form.instance.cree_par = request.user
        chant = form.save()
        if form.cleaned_data["paroles"].strip():
            chant.remplacer_paroles(form.cleaned_data["paroles"], culte.lignes_par_diapo)
        if not chant.diapos.exists():
            DiapoChant.objects.create(chant=chant, ordre=1)
        chant.mettre_a_jour_recherche()
        element = ElementCulte.objects.create(
            culte=culte,
            ordre=culte.prochain_ordre(),
            type=ElementCulte.CHANT,
            chant=chant,
            moment=form.cleaned_data["moment"].strip(),
        )
    return reponse_espace(request, culte, element.pk, chant.pk, chant.diapos.first().pk)


@peut_editer_chant
@require_POST
def infos_chant(request, pk, chant_pk):
    culte, element, chant = chant_du_culte(pk, chant_pk)
    form = ChantInfosForm(request.POST, instance=chant)
    if not form.is_valid():
        return HttpResponseBadRequest(premiere_erreur(form))
    form.save()
    chant.mettre_a_jour_recherche()
    return reponse_espace(request, culte, element.pk, chant.pk)


@peut_editer_chant
@require_POST
def enregistrer_diapo(request, pk, chant_pk, piece_pk):
    """Sauvegarde automatique d'une diapo pendant la saisie (réponse JSON légère,
    pour ne pas recharger l'éditeur sous les doigts de la personne)."""
    culte, element, chant = chant_du_culte(pk, chant_pk)
    piece = get_object_or_404(chant.diapos, pk=piece_pk)
    form = DiapoChantForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(premiere_erreur(form))
    donnees = form.cleaned_data
    if "contenu" in request.POST:
        piece.contenu = donnees["contenu"]
    if donnees.get("alignement"):
        piece.alignement = donnees["alignement"]
    if donnees.get("echelle"):
        piece.echelle = donnees["echelle"]
    if "couleur_fond" in request.POST:
        piece.couleur_fond = donnees["couleur_fond"]
    piece.save()
    chant.mettre_a_jour_recherche()
    culte.save(update_fields=["date_modification"])

    apercu = diapos.Diapo(
        diapos.PAROLES, piece.texte.split("\n") if piece.texte else [""], echelle=piece.echelle
    )
    return JsonResponse(
        {
            "contenu": piece.contenu,
            "taille": rendu.en_cqw(rendu.taille_pt(apercu, culte.theme_effectif)),
            "alignement": piece.alignement,
            "echelle": piece.echelle,
            "couleur_fond": piece.couleur_fond,
        }
    )


def renumeroter_diapos(chant, pieces):
    for rang, piece in enumerate(pieces, start=1):
        piece.ordre = rang
    DiapoChant.objects.bulk_update(pieces, ["ordre"])


@peut_editer_chant
@require_POST
def ajouter_diapo(request, pk, chant_pk):
    """Nouvelle diapo (vide, ou copie de `dupliquer`) placée après `apres`."""
    culte, element, chant = chant_du_culte(pk, chant_pk)
    pieces = list(chant.diapos.all())
    modele = next((p for p in pieces if str(p.pk) == request.POST.get("dupliquer")), None)
    apres = next((p for p in pieces if str(p.pk) == request.POST.get("apres")), modele)
    nouvelle = DiapoChant(chant=chant, ordre=0)
    if modele:
        nouvelle.contenu = modele.contenu
        nouvelle.alignement, nouvelle.echelle, nouvelle.couleur_fond = (
            modele.alignement, modele.echelle, modele.couleur_fond,
        )
    elif apres:
        # Une nouvelle diapo garde la mise en page de la précédente.
        nouvelle.alignement, nouvelle.echelle, nouvelle.couleur_fond = (
            apres.alignement, apres.echelle, apres.couleur_fond,
        )
    nouvelle.save()
    position = pieces.index(apres) + 1 if apres else len(pieces)
    pieces.insert(position, nouvelle)
    renumeroter_diapos(chant, pieces)
    chant.mettre_a_jour_recherche()
    return reponse_espace(request, culte, element.pk, chant.pk, nouvelle.pk)


@peut_editer_chant
@require_POST
def supprimer_diapo(request, pk, chant_pk, piece_pk):
    culte, element, chant = chant_du_culte(pk, chant_pk)
    pieces = list(chant.diapos.all())
    supprimee = get_object_or_404(chant.diapos, pk=piece_pk).pk
    rang = [p.pk for p in pieces].index(supprimee)
    DiapoChant.objects.filter(pk=supprimee).delete()
    pieces = [p for p in pieces if p.pk != supprimee]
    renumeroter_diapos(chant, pieces)
    chant.mettre_a_jour_recherche()
    voisine = pieces[min(rang, len(pieces) - 1)].pk if pieces else None
    return reponse_espace(request, culte, element.pk, chant.pk, voisine)


@peut_editer_chant
@require_POST
def deplacer_diapo(request, pk, chant_pk, piece_pk):
    culte, element, chant = chant_du_culte(pk, chant_pk)
    pieces = list(chant.diapos.all())
    ids = [p.pk for p in pieces]
    i = ids.index(get_object_or_404(chant.diapos, pk=piece_pk).pk)
    j = i - 1 if request.POST.get("sens") == "haut" else i + 1
    if 0 <= j < len(pieces):
        pieces[i], pieces[j] = pieces[j], pieces[i]
        renumeroter_diapos(chant, pieces)
    return reponse_espace(request, culte, element.pk, chant.pk, piece_pk)


@peut_editer_chant
@require_POST
def reordonner_diapos(request, pk, chant_pk):
    culte, element, chant = chant_du_culte(pk, chant_pk)
    par_id = {p.pk: p for p in chant.diapos.all()}
    try:
        ordre = [int(i) for i in request.POST.getlist("ordre")]
    except ValueError:
        return HttpResponseBadRequest("Ordre invalide.")
    pieces = [par_id.pop(i) for i in ordre if i in par_id] + sorted(par_id.values(), key=lambda p: p.ordre)
    renumeroter_diapos(chant, pieces)
    selection = request.POST.get("piece")
    return reponse_espace(request, culte, element.pk, chant.pk, int(selection) if selection and selection.isdigit() else None)


@login_required
@permission_required("chants.delete_chant", raise_exception=True)
@require_POST
def supprimer_chant_bibliotheque(request, pk, chant_pk):
    """Depuis la fenêtre de recherche : retirer un chant de la bibliothèque,
    seulement s'il n'est utilisé dans aucun culte."""
    chant = get_object_or_404(Chant, pk=chant_pk)
    nb = chant.utilisations.values("culte").distinct().count()
    if nb:
        request.message_resultats = (
            f"« {chant} » est utilisé dans {nb} culte{'s' if nb > 1 else ''} : "
            "retirez-le de ces cultes avant de le supprimer."
        )
    else:
        request.message_resultats = f"« {chant} » a été supprimé de la bibliothèque."
        chant.delete()
    return chercher_chants(request, pk)


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
