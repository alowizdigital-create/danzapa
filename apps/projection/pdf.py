"""Export d'un culte en PDF : une diapo par page (16:9), comme en projection.

Même liste de diapos et mêmes tailles que l'aperçu et le .pptx
(apps/cultes/diapos.py, apps/projection/rendu.py). Les diapos masquées ne
sont pas exportées, comme en projection.

Polices : les noms du thème (Calibri, Arial…) sont remplacés par des polices
libres de même gabarit (Carlito, Liberation, DejaVu) si elles sont installées
(voir le Dockerfile), sinon par Helvetica / Times de reportlab.
"""

import io
import os
from functools import lru_cache
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from apps.chants import mise_en_forme
from apps.cultes import diapos as d

from . import rendu
from .models import Theme
from .pptx import lire_image, lire_image_de_diapo

LARGEUR, HAUTEUR = rendu.LARGEUR_PT, rendu.HAUTEUR_PT
ALIGNEMENTS = {"gauche": TA_LEFT, "centre": TA_CENTER, "droite": TA_RIGHT}
DOSSIERS_POLICES = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

# Police du thème → fichiers TTF (normal, gras, italique, gras italique).
SUBSTITUTS = {
    "Carlito": ("Carlito-Regular.ttf", "Carlito-Bold.ttf", "Carlito-Italic.ttf", "Carlito-BoldItalic.ttf"),
    "LiberationSans": (
        "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
        "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf",
    ),
    "LiberationSerif": (
        "LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf",
        "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf",
    ),
    "DejaVuSans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"),
    "DejaVuSerif": ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf"),
}
POLICES_PDF = {
    "Calibri": ("Carlito", "Helvetica"),
    "Arial": ("LiberationSans", "Helvetica"),
    "Segoe UI": ("DejaVuSans", "Helvetica"),
    "Verdana": ("DejaVuSans", "Helvetica"),
    "Tahoma": ("DejaVuSans", "Helvetica"),
    "Trebuchet MS": ("DejaVuSans", "Helvetica"),
    "Century Gothic": ("DejaVuSans", "Helvetica"),
    "Georgia": ("DejaVuSerif", "Times-Roman"),
    "Times New Roman": ("LiberationSerif", "Times-Roman"),
}


@lru_cache(maxsize=1)
def fichiers_de_polices():
    """Nom de fichier → chemin, pour les polices installées sur le système."""
    trouves = {}
    for dossier in DOSSIERS_POLICES:
        for racine, _, fichiers in os.walk(dossier):
            for nom in fichiers:
                trouves.setdefault(nom, os.path.join(racine, nom))
    return trouves


@lru_cache(maxsize=None)
def famille(nom_police):
    """Nom de famille reportlab pour une police du thème (<b>, <i> compris)."""
    substitut, repli = POLICES_PDF.get(nom_police, ("Carlito", "Helvetica"))
    normal, gras, italique, gras_italique = (fichiers_de_polices().get(f) for f in SUBSTITUTS[substitut])
    if not normal:
        return repli
    # Variante absente (ex. italiques DejaVu hors de fonts-dejavu-core) : la plus proche disponible.
    gras = gras or normal
    italique = italique or normal
    gras_italique = gras_italique or (gras if gras != normal else italique)
    noms = {}
    for suffixe, chemin in (("", normal), ("-Bold", gras), ("-Italic", italique), ("-BoldItalic", gras_italique)):
        nom = substitut + suffixe
        if nom not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nom, chemin))
        noms[suffixe] = nom
    pdfmetrics.registerFontFamily(
        substitut, normal=noms[""], bold=noms["-Bold"], italic=noms["-Italic"], boldItalic=noms["-BoldItalic"]
    )
    return substitut


def balisage(texte, style, gras, italique, couleur_defaut):
    """Un morceau de texte stylé en balisage de Paragraph reportlab."""
    texte = escape(texte)
    if style.souligne:
        texte = f"<u>{texte}</u>"
    if italique or style.italique:
        texte = f"<i>{texte}</i>"
    if gras if style.gras is None else style.gras:
        texte = f"<b>{texte}</b>"
    return f'<font color="{style.couleur or couleur_defaut}">{texte}</font>'


class Exporteur:
    def __init__(self, culte):
        self.culte = culte
        self.theme = culte.theme or Theme.par_defaut()
        self.image_fond = lire_image(self.theme.image_fond)
        self.image_bienvenue = lire_image(self.theme.image_bienvenue)

    def exporter(self):
        sortie = io.BytesIO()
        self.page = canvas.Canvas(sortie, pagesize=(LARGEUR, HAUTEUR))
        self.page.setTitle(self.culte.titre)
        self.page.setAuthor("Danzapa")
        for diapo in d.diapos_du_culte(self.culte, inclure_masquees=False):
            self.ajouter(diapo)
            self.page.showPage()
        self.page.save()
        return sortie.getvalue()

    # -------------------------------------------------------------- Diapos

    def ajouter(self, diapo):
        self.fond(diapo.couleur_fond)
        if diapo.type == d.BIENVENUE and self.image_bienvenue:
            self.image_pleine_page(self.image_bienvenue)
        elif diapo.type == d.TITRE:
            self.texte(diapo, self.theme.police_titres, gras=self.theme.gras)
        elif diapo.type == d.IMAGE:
            self.image(diapo)
        else:
            self.texte(diapo, diapo.police or self.theme.police, gras=self.theme.gras)

    def rectangle(self, gauche, haut, largeur, hauteur, couleur):
        """Rectangle plein, coordonnées depuis le coin haut gauche (comme rendu.py)."""
        self.page.setFillColor(couleur)
        self.page.rect(gauche, HAUTEUR - haut - hauteur, largeur, hauteur, stroke=0, fill=1)

    def fond(self, couleur_diapo=""):
        self.rectangle(0, 0, LARGEUR, HAUTEUR, couleur_diapo or self.theme.couleur_fond)
        # Une couleur choisie pour la diapo remplace aussi l'image de fond du thème.
        if self.image_fond and not couleur_diapo:
            self.image_pleine_page(self.image_fond)

    def image_pleine_page(self, contenu):
        self.page.drawImage(ImageReader(io.BytesIO(contenu)), 0, 0, LARGEUR, HAUTEUR, mask="auto")

    def image(self, diapo):
        lue = lire_image_de_diapo(diapo)
        if lue:
            contenu, largeur, hauteur = lue
            gauche, haut, l, h = rendu.contenir(largeur, hauteur, rendu.zone_image(diapo))
            self.page.drawImage(ImageReader(io.BytesIO(contenu)), gauche, HAUTEUR - haut - h, l, h, mask="auto")
        if diapo.lignes:
            self.texte(diapo, self.theme.police_titres, gras=self.theme.gras, haut=HAUTEUR - rendu.HAUTEUR_LEGENDE_PT)

    def texte(self, diapo, police, gras, italique=False, haut=None):
        """Lignes de la diapo, centrées verticalement dans rendu.zone_texte (retour à la ligne automatique)."""
        largeur, hauteur = rendu.zone_texte(diapo)
        gauche = (LARGEUR - largeur) / 2
        if haut is None:
            haut = (HAUTEUR - hauteur) / 2
        taille = rendu.taille_pt(diapo, self.theme)
        majuscules = rendu.en_majuscules(diapo, self.theme)
        style = ParagraphStyle(
            "diapo",
            fontName=famille(police),
            fontSize=taille,
            leading=taille * rendu.interligne(diapo),
            alignment=ALIGNEMENTS.get(diapo.alignement, TA_CENTER),
        )
        if diapo.html:
            lignes = [[(m.texte, m.style) for m in ligne] for ligne in mise_en_forme.lignes(diapo.html)]
        else:
            lignes = [[(ligne, mise_en_forme.Style())] for ligne in diapo.lignes]

        blocs = []
        for morceaux in lignes or [[]]:
            texte = "".join(
                balisage(t.upper() if majuscules else t, s, gras, italique, self.theme.couleur_texte)
                for t, s in morceaux
                if t
            )
            paragraphe = Paragraph(texte or "&nbsp;", style)
            _, h = paragraphe.wrap(largeur, HAUTEUR)
            blocs.append((paragraphe, h))

        total = sum(h for _, h in blocs)
        y = haut + max(0, (hauteur - total) / 2)  # depuis le haut de la page
        for paragraphe, h in blocs:
            paragraphe.drawOn(self.page, gauche, HAUTEUR - y - h)
            y += h


def exporter(culte):
    """Contenu binaire du fichier .pdf du culte."""
    return Exporteur(culte).exporter()
