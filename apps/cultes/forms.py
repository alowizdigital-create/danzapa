from django import forms
from django.forms import modelform_factory

from .models import Culte, ElementCulte

CHAMPS_PARAMETRES = ["titre", "statut", "texte_bienvenue", "lignes_par_diapo", "theme"]


class NouveauCulteForm(forms.ModelForm):
    class Meta:
        model = Culte
        fields = ["date", "titre"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {"titre": "Laisser vide pour « Culte du <date> »."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titre"].required = False


class DuplicationForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


def parametres_form(donnees, instance):
    """Formulaire limité aux champs envoyés.

    La barre de titre n'envoie que le titre, l'onglet Création le texte de
    bienvenue… : les autres champs ne doivent pas être écrasés.
    """
    champs = [c for c in CHAMPS_PARAMETRES if c in donnees]
    if not champs:
        return None
    form = modelform_factory(Culte, fields=champs)(donnees, instance=instance)
    if "theme" in form.fields:
        form.fields["theme"].to_field_name = "uuid"  # le thème est choisi par son UUID
    return form


class ElementForm(forms.ModelForm):
    class Meta:
        model = ElementCulte
        fields = ["moment", "titre", "contenu", "image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.type == ElementCulte.CHANT:
            del self.fields["titre"]
            del self.fields["contenu"]
        if self.instance.type == ElementCulte.IMAGE:
            del self.fields["contenu"]  # image facultative : sans fichier, on garde l'actuelle
        else:
            del self.fields["image"]


class ImageForm(forms.ModelForm):
    """Insertion → Image : nouvelle diapo image dans le culte."""

    class Meta:
        model = ElementCulte
        fields = ["moment", "titre", "image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].required = True


class TexteLibreForm(forms.ModelForm):
    class Meta:
        model = ElementCulte
        fields = ["moment", "titre", "contenu"]


class AjoutChantForm(forms.Form):
    chant = forms.UUIDField()
    moment = forms.CharField(max_length=100, required=False)
