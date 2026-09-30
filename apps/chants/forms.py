from django import forms

from . import paroles
from .models import Chant

AIDE_PAROLES = (
    "Séparez chaque couplet par une ligne vide. "
    "Numérotez les couplets (« 1. », « 2. »…) et écrivez « Refrain » "
    "ou « Pont » sur la première ligne du bloc concerné."
)


class ChantForm(forms.ModelForm):
    paroles = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 18, "spellcheck": "true"}),
        help_text=AIDE_PAROLES,
    )

    class Meta:
        model = Chant
        fields = ["titre", "auteur", "langue", "tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["paroles"] = self.instance.paroles_texte

    def clean_paroles(self):
        texte = self.cleaned_data["paroles"]
        if not paroles.decouper(texte):
            raise forms.ValidationError("Les paroles ne contiennent aucun couplet.")
        return texte

    def clean(self):
        donnees = super().clean()
        titre = donnees.get("titre", "").strip()
        auteur = donnees.get("auteur", "").strip()
        if titre:
            doublons = Chant.objects.filter(titre__iexact=titre, auteur__iexact=auteur)
            if self.instance.pk:
                doublons = doublons.exclude(pk=self.instance.pk)
            if doublons.exists():
                raise forms.ValidationError(
                    "Ce chant existe déjà dans la bibliothèque. "
                    "Modifiez-le plutôt que de le recréer."
                )
        return donnees
