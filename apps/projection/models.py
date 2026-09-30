from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

CLASSIQUE = "Classique"

# Polices présentes sur Windows et Mac, pour que le .pptx s'affiche comme
# prévu sur l'ordinateur de projection. La pile CSS ajoute des équivalents
# libres pour l'aperçu dans le navigateur.
POLICES = {
    "Calibri": "Calibri, Carlito, 'Segoe UI', sans-serif",
    "Arial": "Arial, 'Liberation Sans', Helvetica, sans-serif",
    "Segoe UI": "'Segoe UI', system-ui, sans-serif",
    "Verdana": "Verdana, 'DejaVu Sans', sans-serif",
    "Tahoma": "Tahoma, 'DejaVu Sans', sans-serif",
    "Trebuchet MS": "'Trebuchet MS', 'DejaVu Sans', sans-serif",
    "Century Gothic": "'Century Gothic', 'URW Gothic', sans-serif",
    "Georgia": "Georgia, 'DejaVu Serif', serif",
    "Times New Roman": "'Times New Roman', 'Liberation Serif', Times, serif",
}
CHOIX_POLICES = [(p, p) for p in POLICES]

# Largeur moyenne d'un caractère gras, en proportion de la taille : sert à
# réduire la taille quand une ligne ne tiendrait pas (apps/projection/rendu.py).
CHASSES = {
    "Calibri": 0.53,
    "Arial": 0.60,
    "Segoe UI": 0.58,
    "Verdana": 0.68,
    "Tahoma": 0.60,
    "Trebuchet MS": 0.57,
    "Century Gothic": 0.63,
    "Georgia": 0.62,
    "Times New Roman": 0.55,
}

couleur_hex = RegexValidator(r"^#[0-9a-fA-F]{6}$", "Couleur au format #RRGGBB.")


def image_legere(fichier):
    if fichier and fichier.size > 5 * 1024 * 1024:
        raise ValidationError("L'image ne doit pas dépasser 5 Mo.")


def couleur(**kwargs):
    return models.CharField(max_length=7, validators=[couleur_hex], **kwargs)


class Theme(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    couleur_fond = couleur(verbose_name="couleur de fond", default="#000000")
    image_fond = models.ImageField(
        "image de fond", upload_to="themes/", blank=True, validators=[image_legere],
        help_text="Optionnelle, étirée sur toute la diapo.",
    )
    couleur_texte = couleur(verbose_name="couleur du texte", default="#ffffff")
    police = models.CharField("police des paroles", max_length=40, choices=CHOIX_POLICES, default="Calibri")
    police_titres = models.CharField("police des titres", max_length=40, choices=CHOIX_POLICES, default="Georgia")
    gras = models.BooleanField("paroles en gras", default=True)
    taille_paroles = models.PositiveSmallIntegerField(
        "taille des paroles (pt)", default=54, validators=[MinValueValidator(20), MaxValueValidator(120)]
    )
    taille_titre = models.PositiveSmallIntegerField(
        "taille des titres (pt)", default=32, validators=[MinValueValidator(14), MaxValueValidator(96)]
    )
    titres_majuscules = models.BooleanField("titres en majuscules", default=True)
    couleur_bandeau = couleur(verbose_name="couleur du bandeau de bienvenue", default="#8f8f8f")
    image_bienvenue = models.ImageField(
        "image de bienvenue", upload_to="themes/", blank=True, validators=[image_legere],
        help_text="Optionnelle : remplace toute la diapo de bienvenue (texte compris).",
    )
    date_modification = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "thème"
        verbose_name_plural = "thèmes"

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("projection:theme_modification", args=[self.pk])

    @classmethod
    def par_defaut(cls):
        theme, _ = cls.objects.get_or_create(nom=CLASSIQUE)
        return theme

    @property
    def est_classique(self):
        return self.nom == CLASSIQUE

    @property
    def taille_bienvenue(self):
        return round(self.taille_paroles * 1.3)

    @property
    def pile_police(self):
        return POLICES.get(self.police, POLICES["Calibri"])

    @property
    def pile_police_titres(self):
        return POLICES.get(self.police_titres, POLICES["Georgia"])

    def style_css(self):
        """Variables CSS de l'aperçu (vignettes, grande diapo, page du thème)."""
        from .rendu import en_cqw

        variables = {
            "--fond-couleur": self.couleur_fond,
            "--fond-image": f"url('{self.image_fond.url}')" if self.image_fond else "none",
            "--texte-couleur": self.couleur_texte,
            "--police": self.pile_police,
            "--police-titres": self.pile_police_titres,
            "--poids": "700" if self.gras else "400",
            "--taille-titre": en_cqw(self.taille_titre),
            "--taille-bienvenue": en_cqw(self.taille_bienvenue),
            "--casse-titre": "uppercase" if self.titres_majuscules else "none",
            "--bandeau": self.couleur_bandeau,
        }
        # Sans image de bienvenue, la diapo de bienvenue garde l'image de fond.
        if self.image_bienvenue:
            variables["--bienvenue-image"] = f"url('{self.image_bienvenue.url}')"
        return "; ".join(f"{k}: {v}" for k, v in variables.items())
