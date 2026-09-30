from django.conf import settings
from django.db import models, transaction
from django.urls import reverse

from . import paroles
from .recherche import normaliser


class Chant(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.CharField(max_length=200, blank=True)
    langue = models.CharField(max_length=50, default="Français")
    tags = models.CharField(
        max_length=300,
        blank=True,
        help_text="Séparés par des virgules, par exemple : adoration, louange, Noël",
    )
    # Titre, auteur, tags et paroles normalisés, pour une recherche sans accents.
    recherche = models.TextField(blank=True, editable=False)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chants_crees",
        verbose_name="créé par",
    )
    date_ajout = models.DateTimeField("ajouté le", auto_now_add=True)
    date_modification = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        # `recherche` commence par le titre sans accents : « À toi la gloire »
        # est classé avec les A, et non après le Z comme avec un tri sur `titre`.
        ordering = ["recherche", "pk"]
        verbose_name = "chant"
        verbose_name_plural = "chants"

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse("chants:detail", args=[self.pk])

    @property
    def liste_tags(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def paroles_texte(self):
        return paroles.vers_texte(self.couplets.all())

    @transaction.atomic
    def remplacer_paroles(self, texte):
        """Remplace les couplets par ceux découpés dans `texte`."""
        self.couplets.all().delete()
        Couplet.objects.bulk_create(
            Couplet(chant=self, ordre=i, type=b.type, numero=b.numero, texte=b.texte)
            for i, b in enumerate(paroles.decouper(texte), start=1)
        )
        self.mettre_a_jour_recherche()

    def mettre_a_jour_recherche(self):
        morceaux = [self.titre, self.auteur, self.tags]
        morceaux += self.couplets.values_list("texte", flat=True)
        self.recherche = normaliser(" ".join(morceaux))
        Chant.objects.filter(pk=self.pk).update(recherche=self.recherche)


class Couplet(models.Model):
    TYPES = [
        (paroles.COUPLET, "Couplet"),
        (paroles.REFRAIN, "Refrain"),
        (paroles.PONT, "Pont"),
    ]

    chant = models.ForeignKey(Chant, on_delete=models.CASCADE, related_name="couplets")
    ordre = models.PositiveSmallIntegerField()
    type = models.CharField(max_length=10, choices=TYPES, default=paroles.COUPLET)
    numero = models.PositiveSmallIntegerField(
        "numéro", null=True, blank=True, help_text="Numéro affiché devant le couplet"
    )
    texte = models.TextField()

    class Meta:
        ordering = ["chant_id", "ordre"]
        verbose_name = "couplet"
        verbose_name_plural = "couplets"

    def __str__(self):
        return f"{self.chant} – {self.libelle}"

    @property
    def libelle(self):
        if self.type == paroles.COUPLET and self.numero:
            return f"Couplet {self.numero}"
        return self.get_type_display()

    @property
    def lignes(self):
        return self.texte.splitlines()
