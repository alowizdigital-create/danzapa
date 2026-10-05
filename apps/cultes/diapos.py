"""Transforme un culte en liste de diapositives.

Module sans dépendance à l'affichage : l'éditeur, l'export PowerPoint et
la projection s'appuient tous sur `groupes_du_culte` / `diapos_du_culte`.

- une diapo de bienvenue si le culte a un texte de bienvenue ;
- pour chaque chant, une diapo titre « Moment : Titre » puis ses diapos,
  exactement comme elles ont été tapées et mises en forme ;
- pour un texte libre, un paragraphe par diapo.
"""

from dataclasses import dataclass, field

from apps.chants import paroles

BIENVENUE = "bienvenue"
TITRE = "titre"
PAROLES = "paroles"
TEXTE = "texte"


@dataclass
class Diapo:
    type: str
    lignes: list[str]
    element_id: int | None = None
    masque: bool = False
    libelle: str = ""
    numero: int = 0  # position dans le culte, à partir de 1
    # Diapos de chant : texte mis en forme (HTML nettoyé) et réglages de la diapo.
    html: str = ""
    alignement: str = "centre"
    echelle: int = 100
    taille: int | None = None  # pt choisis ; None : automatique
    police: str = ""  # vide : police du thème
    couleur_fond: str = ""
    chant_id: int | None = None
    piece_id: int | None = None  # DiapoChant correspondante


@dataclass
class Groupe:
    """Les diapos d'un même élément du culte (déplacées ensemble)."""

    element: object | None
    diapos: list[Diapo] = field(default_factory=list)


def diapos_du_chant(element):
    """Diapo titre « Moment : Titre », puis les diapos du chant telles que saisies."""
    chant = element.chant
    titre = f"{element.moment} : {chant.titre}" if element.moment else chant.titre
    diapos = [Diapo(TITRE, [titre], element.pk, element.masque, "Titre", chant_id=chant.pk)]
    for rang, piece in enumerate(chant.diapos.all(), start=1):
        diapos.append(
            Diapo(
                PAROLES,
                piece.texte.split("\n") if piece.texte else [""],
                element.pk,
                element.masque,
                f"Diapo {rang}",
                html=piece.contenu,
                alignement=piece.alignement,
                echelle=piece.echelle,
                taille=piece.taille,
                police=piece.police,
                couleur_fond=piece.couleur_fond,
                chant_id=chant.pk,
                piece_id=piece.pk,
            )
        )
    return diapos


def diapos_du_texte(element):
    diapos = []
    entete = " : ".join(p for p in (element.moment, element.titre) if p)
    if entete:
        diapos.append(Diapo(TITRE, [entete], element.pk, element.masque, "Titre"))
    for paragraphe in paroles.decouper_paragraphes(element.contenu):
        diapos.append(Diapo(TEXTE, paragraphe, element.pk, element.masque, "Texte"))
    if not diapos:
        diapos.append(Diapo(TEXTE, [""], element.pk, element.masque, "Texte"))
    return diapos


def groupes_du_culte(culte, elements=None):
    """Diapos regroupées par élément ; le premier groupe (bienvenue) n'a pas d'élément."""
    if elements is None:
        elements = culte.elements_complets()
    groupes = []
    if culte.texte_bienvenue.strip():
        lignes = [l.strip() for l in culte.texte_bienvenue.splitlines() if l.strip()]
        groupes.append(Groupe(None, [Diapo(BIENVENUE, lignes, libelle="Bienvenue")]))
    for element in elements:
        if element.type == element.CHANT and element.chant:
            diapos = diapos_du_chant(element)
        else:
            diapos = diapos_du_texte(element)
        groupes.append(Groupe(element, diapos))

    numero = 0
    for groupe in groupes:
        for diapo in groupe.diapos:
            numero += 1
            diapo.numero = numero
    return groupes


def diapos_du_culte(culte, inclure_masquees=True):
    diapos = [d for g in groupes_du_culte(culte) for d in g.diapos]
    if not inclure_masquees:
        diapos = [d for d in diapos if not d.masque]
    return diapos
