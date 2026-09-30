from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ChantForm
from .models import Chant
from .recherche import filtrer


class AccesMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Anonyme → page de connexion ; connecté sans droit → erreur 403."""


class ChantListe(AccesMixin, ListView):
    permission_required = "chants.view_chant"
    model = Chant
    paginate_by = 25
    template_name = "chants/liste.html"

    def get_queryset(self):
        self.q = self.request.GET.get("q", "").strip()
        return filtrer(Chant.objects.prefetch_related("couplets"), self.q)

    def get_context_data(self, **kwargs):
        return super().get_context_data(q=self.q, total=Chant.objects.count(), **kwargs)


class ChantDetail(AccesMixin, DetailView):
    permission_required = "chants.view_chant"
    model = Chant
    template_name = "chants/detail.html"

    def get_context_data(self, **kwargs):
        cultes = (
            self.object.utilisations.select_related("culte")
            .order_by("-culte__date")
            .values_list("culte__pk", "culte__titre", "culte__date")
            .distinct()
        )
        return super().get_context_data(cultes=list(cultes), **kwargs)


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

    def retour(self):
        """Page d'origine (par exemple l'éditeur du culte), si elle est sur ce site."""
        suivant = self.request.GET.get("next", "")
        if url_has_allowed_host_and_scheme(
            suivant, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return suivant
        return None

    def get_context_data(self, **kwargs):
        return super().get_context_data(retour=self.retour(), **kwargs)

    def get_success_url(self):
        return self.retour() or super().get_success_url()


class ChantSuppression(AccesMixin, DeleteView):
    permission_required = "chants.delete_chant"
    model = Chant
    template_name = "chants/confirmer_suppression.html"
    success_url = reverse_lazy("chants:liste")

    def form_valid(self, form):
        titre = str(self.object)
        try:
            reponse = super().form_valid(form)
        except ProtectedError:
            nb = self.object.utilisations.values("culte").distinct().count()
            messages.error(
                self.request,
                f"« {titre} » est utilisé dans {nb} culte{'s' if nb > 1 else ''} : "
                "retirez-le de ces cultes avant de le supprimer.",
            )
            return redirect(self.object)
        messages.success(self.request, f"« {titre} » a été supprimé.")
        return reponse
