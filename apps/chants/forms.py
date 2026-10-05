from django import forms

from .models import Chant

AIDE_COLLER = (
    "Optionnel : collez des paroles existantes pour créer les diapos d'un coup "
    "(une ligne vide sépare deux blocs). Sinon, tapez-les diapo par diapo."
)


class ChantInfosForm(forms.ModelForm):
    """Titre, tags et auteur : ce qui permet de retrouver le chant."""

    class Meta:
        model = Chant
        fields = ["titre", "tags", "auteur"]
        widgets = {
            "tags": forms.TextInput(attrs={"placeholder": "adoration, louange, entrée…"}),
        }

    def clean(self):
        donnees = super().clean()
        titre = (donnees.get("titre") or "").strip()
        auteur = (donnees.get("auteur") or "").strip()
        if titre:
            doublons = Chant.objects.filter(titre__iexact=titre, auteur__iexact=auteur)
            if self.instance.pk:
                doublons = doublons.exclude(pk=self.instance.pk)
            if doublons.exists():
                raise forms.ValidationError(
                    "Ce chant existe déjà dans la bibliothèque : insérez-le avec « Insérer un chant »."
                )
        return donnees


class NouveauChantForm(ChantInfosForm):
    moment = forms.CharField(max_length=100, required=False)
    paroles = forms.CharField(widget=forms.Textarea, required=False, help_text=AIDE_COLLER)


class DiapoChantForm(forms.Form):
    """Contenu et réglages d'une diapo, envoyés par l'éditeur à chaque modification."""

    contenu = forms.CharField(required=False, max_length=20000, strip=False)
    alignement = forms.ChoiceField(choices=[("gauche", ""), ("centre", ""), ("droite", "")], required=False)
    echelle = forms.IntegerField(required=False, min_value=50, max_value=200)
    taille = forms.IntegerField(required=False, min_value=8, max_value=200)
    police = forms.CharField(required=False, max_length=40)
    couleur_fond = forms.RegexField(regex=r"^(#[0-9a-fA-F]{6})?$", required=False)
