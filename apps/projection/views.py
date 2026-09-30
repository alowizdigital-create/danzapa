from dataclasses import replace

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.cultes import diapos as d

from .forms import ThemeForm
from .models import CHASSES, POLICES, Theme
from .rendu import en_cqw, taille_pt

# Diapos d'exemple pour l'aperçu en direct de la page d'un thème.
EXEMPLES = [
    d.Diapo(d.BIENVENUE, ["Bienvenus", "dans la", "maison du Seigneur"], libelle="Bienvenue"),
    d.Diapo(d.TITRE, ["Cantique d'entrée : Sans attendre je veux tendre"], libelle="Titre"),
    d.Diapo(d.PAROLES, ["1. Sans attendre", "Je veux tendre", "Au bonheur promis"], libelle="Couplet 1"),
]


class AccesMixin(LoginRequiredMixin, PermissionRequiredMixin):
    pass


class ThemeListe(AccesMixin, ListView):
    permission_required = "projection.view_theme"
    model = Theme
    template_name = "projection/liste.html"

    def get_queryset(self):
        Theme.par_defaut()  # « Classique » existe toujours
        return Theme.objects.all()


class ThemeEdition:
    model = Theme
    form_class = ThemeForm
    template_name = "projection/formulaire.html"
    success_url = reverse_lazy("projection:theme_liste")

    def get_context_data(self, **kwargs):
        theme = self.object or Theme()
        exemples = []
        for modele in EXEMPLES:
            diapo = replace(modele)
            diapo.taille_cqw = en_cqw(taille_pt(diapo, theme))
            exemples.append(diapo)
        return super().get_context_data(apercu_theme=theme, exemples=exemples, polices=POLICES, chasses=CHASSES, **kwargs)

    def form_valid(self, form):
        reponse = super().form_valid(form)
        messages.success(self.request, f"Le thème « {self.object} » a été enregistré.")
        return reponse


class ThemeCreation(AccesMixin, ThemeEdition, CreateView):
    permission_required = "projection.add_theme"


class ThemeModification(AccesMixin, ThemeEdition, UpdateView):
    permission_required = "projection.change_theme"


class ThemeSuppression(AccesMixin, DeleteView):
    permission_required = "projection.delete_theme"
    model = Theme
    template_name = "projection/confirmer_suppression.html"
    success_url = reverse_lazy("projection:theme_liste")

    def post(self, request, *args, **kwargs):
        theme = self.get_object()
        if theme.est_classique:
            messages.error(request, "Le thème « Classique » est le thème par défaut : il ne peut pas être supprimé.")
            return redirect(theme)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        nb = self.object.cultes.count()
        messages.success(
            self.request,
            f"Le thème « {self.object} » a été supprimé."
            + (f" {nb} culte{'s' if nb > 1 else ''} repasse{'nt' if nb > 1 else ''} au thème « Classique »." if nb else ""),
        )
        return super().form_valid(form)
