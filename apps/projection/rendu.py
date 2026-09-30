"""Dimensions communes à l'aperçu (navigateur) et à l'export PowerPoint.

Une diapo 16:9 mesure 960 × 540 points. En exprimant les tailles de texte en
points puis en « cqw » (1 % de la largeur de la diapo) pour l'aperçu, la
vignette, la grande diapo et le .pptx gardent les mêmes proportions.
"""

from apps.cultes import diapos as d

from .models import CHASSES

LARGEUR_PT = 960
HAUTEUR_PT = 540
MARGE = 0.05  # de chaque côté
LARGEUR_UTILE_PT = LARGEUR_PT * (1 - 2 * MARGE)
HAUTEUR_UTILE_PT = HAUTEUR_PT * 0.88
INTERLIGNE = 1.2
# Les majuscules sont plus larges ; celles, italiques, du bandeau de bienvenue encore plus.
FACTEUR_MAJUSCULES = 1.3
FACTEUR_BIENVENUE = 1.35
TAILLE_MIN = 24


def en_cqw(points):
    return f"{points * 100 / LARGEUR_PT:.3f}cqw"


# Bandeau de bienvenue : 84 % × 44 % de la diapo, texte à l'intérieur.
LARGEUR_BANDEAU_PT = LARGEUR_PT * 0.84
HAUTEUR_BANDEAU_PT = HAUTEUR_PT * 0.44


def zone_texte(diapo):
    """Largeur et hauteur (pt) disponibles pour le texte de la diapo."""
    if diapo.type == d.BIENVENUE:
        return LARGEUR_BANDEAU_PT * 0.94, HAUTEUR_BANDEAU_PT * 0.94
    return LARGEUR_UTILE_PT, HAUTEUR_UTILE_PT


def taille_nominale(diapo, theme):
    if diapo.type == d.BIENVENUE:
        return theme.taille_bienvenue
    if diapo.type == d.TITRE:
        return theme.taille_titre
    return theme.taille_paroles


def en_majuscules(diapo, theme):
    if diapo.type == d.BIENVENUE:
        return True
    return diapo.type == d.TITRE and theme.titres_majuscules


def chasse_pour(diapo, theme):
    """Largeur moyenne d'un caractère de la diapo, en proportion de la taille."""
    police = theme.police if diapo.type in (d.PAROLES, d.TEXTE) else theme.police_titres
    chasse = CHASSES.get(police, 0.6)
    if diapo.type == d.BIENVENUE:
        return chasse * FACTEUR_BIENVENUE
    if en_majuscules(diapo, theme):
        return chasse * FACTEUR_MAJUSCULES
    return chasse


def taille_pt(diapo, theme):
    """Taille retenue : la taille du thème, réduite si le texte ne tient pas."""
    taille = taille_nominale(diapo, theme)
    largeur, hauteur = zone_texte(diapo)
    lignes = diapo.lignes or [""]
    plus_longue = max(len(l) for l in lignes)
    if plus_longue:
        chasse = chasse_pour(diapo, theme)
        taille = min(taille, largeur / (plus_longue * chasse))
    taille = min(taille, hauteur / (len(lignes) * INTERLIGNE))
    nominale = taille_nominale(diapo, theme)
    return max(min(TAILLE_MIN, nominale), min(taille, nominale))


def annoter(groupes, theme):
    """Ajoute à chaque diapo la taille calculée, pour l'aperçu."""
    for groupe in groupes:
        for diapo in groupe.diapos:
            diapo.taille_cqw = en_cqw(taille_pt(diapo, theme))
    return groupes
