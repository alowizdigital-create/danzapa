import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models, transaction

from . import mise_en_forme, paroles
from .recherche import normaliser


class Chant(models.Model):
    """Un chant de la bibliothèque : saisi une fois, réutilisé dans tous les cultes."""

    # Identifiant public (adresses, pages, JavaScript) ; la clé entière reste interne.
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

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

    @property
    def liste_tags(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def premiere_ligne(self):
        diapo = self.diapos.first()
        return diapo.texte.split("\n", 1)[0] if diapo else ""

    @transaction.atomic
    def remplacer_paroles(self, texte, lignes_par_diapo=4):
        """Remplace les diapos par celles découpées dans des paroles collées."""
        self.diapos.all().delete()
        DiapoChant.objects.bulk_create(
            DiapoChant(chant=self, ordre=i, **DiapoChant.champs_depuis_html(mise_en_forme.depuis_texte(t)))
            for i, t in enumerate(paroles.en_diapos(texte, lignes_par_diapo), start=1)
        )
        self.mettre_a_jour_recherche()

    def mettre_a_jour_recherche(self):
        morceaux = [self.titre, self.auteur, self.tags]
        morceaux += self.diapos.values_list("texte", flat=True)
        self.recherche = normaliser(" ".join(morceaux))
        Chant.objects.filter(pk=self.pk).update(recherche=self.recherche)


couleur_hex = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Couleur au format #RRGGBB.")


class DiapoChant(models.Model):
    """Une diapo d'un chant, telle qu'elle a été tapée et mise en forme."""

    # Identifiant public (adresses, pages, JavaScript) ; la clé entière reste interne.
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    GAUCHE, CENTRE, DROITE = "gauche", "centre", "droite"
    ALIGNEMENTS = [(GAUCHE, "Gauche"), (CENTRE, "Centré"), (DROITE, "Droite")]
    ECHELLE_MIN, ECHELLE_MAX = 50, 200
    TAILLE_MIN, TAILLE_MAX = 8, 200
    INTERLIGNE_MIN, INTERLIGNE_MAX = 80, 300  # en % de la taille du texte
    # Animations d'entrée du texte (projection, aperçu de l'éditeur, export .pptx).
    ANIMATIONS = [
        ("", "Aucune"),
        ("fondu", "Fondu"),
        ("monter", "Glisser vers le haut"),
        ("zoom", "Zoom"),
        ("lignes", "Ligne par ligne"),
        ("machine", "Machine à écrire"),
    ]
    VITESSES = [("rapide", "Rapide"), ("normale", "Normale"), ("lente", "Lente")]

    chant = models.ForeignKey(Chant, on_delete=models.CASCADE, related_name="diapos")
    ordre = models.PositiveIntegerField()
    # HTML canonique produit par mise_en_forme.nettoyer (jamais le HTML brut du navigateur).
    contenu = models.TextField(blank=True)
    texte = models.TextField(blank=True, editable=False)
    alignement = models.CharField(max_length=10, choices=ALIGNEMENTS, default=CENTRE)
    echelle = models.PositiveSmallIntegerField(
        "taille (%)", default=100, validators=[MinValueValidator(ECHELLE_MIN), MaxValueValidator(ECHELLE_MAX)]
    )
    # Taille du texte choisie (pt) ; vide : taille du thème, réduite si le texte ne tient pas.
    taille = models.PositiveSmallIntegerField(
        "taille du texte (pt)", null=True, blank=True,
        validators=[MinValueValidator(TAILLE_MIN), MaxValueValidator(TAILLE_MAX)],
    )
    # Interligne en % (150 = 1,5 ligne) ; vide : automatique (1,2).
    interligne = models.PositiveSmallIntegerField(null=True, blank=True)
    # Vide : police du thème. Noms de apps/projection/models.py (POLICES).
    police = models.CharField(max_length=40, blank=True)
    animation = models.CharField(max_length=12, choices=ANIMATIONS, blank=True)
    vitesse_animation = models.CharField(max_length=8, choices=VITESSES, default="normale")
    couleur_fond = models.CharField(
        "couleur de fond", max_length=7, blank=True, validators=[couleur_hex], help_text="Vide : couleur du thème."
    )

    class Meta:
        ordering = ["chant_id", "ordre", "pk"]
        verbose_name = "diapo de chant"
        verbose_name_plural = "diapos de chant"

    def __str__(self):
        return f"{self.chant} – diapo {self.ordre}"

    @staticmethod
    def champs_depuis_html(html):
        contenu = mise_en_forme.nettoyer(html)
        return {"contenu": contenu, "texte": mise_en_forme.texte_brut(contenu)}

    def save(self, *args, **kwargs):
        champs = self.champs_depuis_html(self.contenu)
        self.contenu, self.texte = champs["contenu"], champs["texte"]
        self.echelle = min(self.ECHELLE_MAX, max(self.ECHELLE_MIN, self.echelle or 100))
        if self.taille:
            self.taille = min(self.TAILLE_MAX, max(self.TAILLE_MIN, self.taille))
        if self.interligne:
            self.interligne = min(self.INTERLIGNE_MAX, max(self.INTERLIGNE_MIN, self.interligne))
        from apps.projection.models import POLICES

        if self.police not in POLICES:
            self.police = ""
        if self.animation not in dict(self.ANIMATIONS):
            self.animation = ""
        if self.vitesse_animation not in dict(self.VITESSES):
            self.vitesse_animation = "normale"
        super().save(*args, **kwargs)
