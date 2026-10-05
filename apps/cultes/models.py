from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import formats

from apps.chants.models import Chant

MOMENT_PAR_DEFAUT = "Cantique d'entrée"
# Sur trois lignes, comme dans la présentation PowerPoint actuelle.
BIENVENUE_PAR_DEFAUT = "Bienvenus\ndans la\nmaison du Seigneur"


def titre_pour(date):
    return f"Culte du {formats.date_format(date, 'j F Y')}"


class Culte(models.Model):
    BROUILLON = "brouillon"
    PRET = "pret"
    STATUTS = [(BROUILLON, "Brouillon"), (PRET, "Prêt")]

    titre = models.CharField(max_length=200)
    date = models.DateField()
    statut = models.CharField(max_length=10, choices=STATUTS, default=BROUILLON)
    texte_bienvenue = models.TextField(
        "texte de bienvenue",
        blank=True,
        default=BIENVENUE_PAR_DEFAUT,
        help_text="Première diapo du culte. Laisser vide pour ne pas l'afficher.",
    )
    theme = models.ForeignKey(
        "projection.Theme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cultes",
        verbose_name="thème",
        help_text="Vide : thème « Classique ».",
    )
    lignes_par_diapo = models.PositiveSmallIntegerField(
        "lignes par diapo",
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cultes_crees",
        verbose_name="créé par",
    )
    date_creation = models.DateTimeField("créé le", auto_now_add=True)
    date_modification = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ["-date", "-pk"]
        verbose_name = "culte"
        verbose_name_plural = "cultes"

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse("cultes:editeur", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.titre:
            self.titre = titre_pour(self.date)
        super().save(*args, **kwargs)

    @property
    def theme_effectif(self):
        from apps.projection.models import Theme

        return self.theme or Theme.par_defaut()

    def elements_complets(self):
        """Éléments avec leurs chants et leurs diapos, en deux requêtes."""
        return self.elements.select_related("chant").prefetch_related("chant__diapos")

    def prochain_ordre(self):
        dernier = self.elements.aggregate(m=models.Max("ordre"))["m"]
        return (dernier or 0) + 1

    def renumeroter(self, ids):
        """Range les éléments dans l'ordre des `ids` donnés (ceux du culte uniquement)."""
        elements = {e.pk: e for e in self.elements.all()}
        ordonnes = [elements.pop(i) for i in ids if i in elements]
        # Les éléments absents de la liste gardent leur ordre relatif, à la fin.
        ordonnes += sorted(elements.values(), key=lambda e: e.ordre)
        for rang, element in enumerate(ordonnes, start=1):
            element.ordre = rang
        ElementCulte.objects.bulk_update(ordonnes, ["ordre"])

    @transaction.atomic
    def dupliquer(self, date, par=None):
        copie = Culte.objects.create(
            titre=titre_pour(date),
            date=date,
            texte_bienvenue=self.texte_bienvenue,
            theme_id=self.theme_id,
            lignes_par_diapo=self.lignes_par_diapo,
            cree_par=par,
        )
        ElementCulte.objects.bulk_create(
            ElementCulte(
                culte=copie,
                ordre=e.ordre,
                type=e.type,
                moment=e.moment,
                chant_id=e.chant_id,
                masque=e.masque,
                titre=e.titre,
                contenu=e.contenu,
            )
            for e in self.elements.all()
        )
        return copie


class ElementCulte(models.Model):
    CHANT = "chant"
    TEXTE = "texte"
    TYPES = [(CHANT, "Chant"), (TEXTE, "Texte libre")]

    culte = models.ForeignKey(Culte, on_delete=models.CASCADE, related_name="elements")
    ordre = models.PositiveIntegerField()
    type = models.CharField(max_length=10, choices=TYPES)
    moment = models.CharField(max_length=100, blank=True)
    # PROTECT : un chant utilisé dans un culte ne peut pas être supprimé
    # de la bibliothèque sans le retirer d'abord du culte.
    chant = models.ForeignKey(
        Chant, on_delete=models.PROTECT, null=True, blank=True, related_name="utilisations"
    )
    masque = models.BooleanField("masqué", default=False)
    titre = models.CharField(max_length=200, blank=True)
    contenu = models.TextField(blank=True)

    class Meta:
        ordering = ["ordre", "pk"]
        verbose_name = "élément du culte"
        verbose_name_plural = "éléments du culte"

    def __str__(self):
        return self.nom

    @property
    def nom(self):
        if self.type == self.CHANT and self.chant:
            return self.chant.titre
        return self.titre or self.moment or "Texte libre"
