from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ChantForm
from .models import Chant
from .recherche import normaliser


class AccesMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Anonyme → page de connexion ; connecté sans droit → erreur 403."""


class ChantListe(AccesMixin, ListView):
    permission_required = "chants.view_chant"
    model = Chant
    paginate_by = 25
    template_name = "chants/liste.html"

    def get_queryset(self):
        chants = Chant.objects.prefetch_related("couplets")
        self.q = self.request.GET.get("q", "").strip()
        for mot in normaliser(self.q).split():
            chants = chants.filter(recherche__contains=mot)
        return chants

    def get_context_data(self, **kwargs):
        return super().get_context_data(q=self.q, total=Chant.objects.count(), **kwargs)


class ChantDetail(AccesMixin, DetailView):
    permission_required = "chants.view_chant"
    model = Chant
    template_name = "chants/detail.html"


class ChantEdition:
    """Enregistre le chant puis ses paroles découpées, en une transaction."""

    model = Chant
    form_class = ChantForm
    template_name = "chants/formulaire.html"
    message = ""

    @transaction.atomic
    def form_valid(self, form):
        reponse = super().form_valid(form)
        self.object.remplacer_paroles(form.cleaned_data["paroles"])
        messages.success(self.request, self.message.format(chant=self.object))
        return reponse


class ChantCreation(AccesMixin, ChantEdition, CreateView):
    permission_required = "chants.add_chant"
    message = "« {chant} » a été ajouté à la bibliothèque."

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        return super().form_valid(form)


class ChantModification(AccesMixin, ChantEdition, UpdateView):
    permission_required = "chants.change_chant"
    message = "« {chant} » a été enregistré."


class ChantSuppression(AccesMixin, DeleteView):
    permission_required = "chants.delete_chant"
    model = Chant
    template_name = "chants/confirmer_suppression.html"
    success_url = reverse_lazy("chants:liste")

    def form_valid(self, form):
        messages.success(self.request, f"« {self.object} » a été supprimé.")
        return super().form_valid(form)
