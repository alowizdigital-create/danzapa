from django import forms

from .models import Theme


class ThemeForm(forms.ModelForm):
    class Meta:
        model = Theme
        fields = [
            "nom",
            "couleur_fond",
            "image_fond",
            "couleur_texte",
            "police",
            "gras",
            "taille_paroles",
            "police_titres",
            "taille_titre",
            "titres_majuscules",
            "couleur_bandeau",
            "image_bienvenue",
        ]
        widgets = {
            "couleur_fond": forms.TextInput(attrs={"type": "color"}),
            "couleur_texte": forms.TextInput(attrs={"type": "color"}),
            "couleur_bandeau": forms.TextInput(attrs={"type": "color"}),
            "image_fond": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "image_bienvenue": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_nom(self):
        nom = self.cleaned_data["nom"].strip()
        if self.instance.pk and self.instance.est_classique and nom != self.instance.nom:
            raise forms.ValidationError("Le thème « Classique » ne peut pas être renommé.")
        return nom
