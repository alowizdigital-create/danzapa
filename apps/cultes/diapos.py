"""Transforme un culte en liste de diapositives.

Module sans dépendance à l'affichage : l'éditeur, l'export PowerPoint et
la projection s'appuient tous sur `diapos_du_culte`.

Règles, reprises de la présentation PowerPoint utilisée jusqu'ici :
- une diapo de bienvenue si le culte a un texte de bienvenue ;
- pour chaque chant, une diapo titre « Moment : Titre » puis les paroles ;
- le refrain, saisi une fois, est rejoué après chaque couplet (désactivable) ;
- chaque bloc est découpé en diapos d'au plus N lignes, réparties de façon
  équilibrée, le numéro du couplet devant la première ligne.
"""

from dataclasses import dataclass, field
from math import ceil

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


@dataclass
class Groupe:
    """Les diapos d'un même élément du culte (déplacées ensemble)."""

    element: object | None
    diapos: list[Diapo] = field(default_factory=list)


def ordre_de_lecture(blocs, repeter_refrain=True):
    """Ordre de projection des blocs d'un chant.

    Après chaque couplet qui n'est pas déjà suivi d'un refrain, on rejoue le
    dernier refrain rencontré (ou, s'il n'y en a pas encore eu, le premier
    refrain du chant).
    """
    blocs = list(blocs)
    if not repeter_refrain:
        return blocs
    refrains = [b for b in blocs if b.type == paroles.REFRAIN]
    if not refrains:
        return blocs

    resultat = []
    dernier_refrain = None
    for i, bloc in enumerate(blocs):
        resultat.append(bloc)
        if bloc.type == paroles.REFRAIN:
            dernier_refrain = bloc
        elif bloc.type == paroles.COUPLET:
            suivant = blocs[i + 1] if i + 1 < len(blocs) else None
            if not (suivant and suivant.type == paroles.REFRAIN):
                resultat.append(dernier_refrain or refrains[0])
    return resultat


def decouper_lignes(lignes, maximum):
    """Répartit les lignes en paquets d'au plus `maximum`, de tailles proches.

    6 lignes avec un maximum de 4 donnent 3 + 3 plutôt que 4 + 2.
    """
    lignes = list(lignes)
    if not lignes:
        return []
    maximum = max(1, maximum)
    nb = ceil(len(lignes) / maximum)
    taille, reste = divmod(len(lignes), nb)
    paquets, debut = [], 0
    for i in range(nb):
        fin = debut + taille + (1 if i < reste else 0)
        paquets.append(lignes[debut:fin])
        debut = fin
    return paquets


def _libelle_bloc(bloc):
    if bloc.type == paroles.COUPLET and bloc.numero:
        return f"Couplet {bloc.numero}"
    return paroles.LIBELLES.get(bloc.type, "")


def diapos_du_chant(element, lignes_par_diapo):
    chant = element.chant
    titre = f"{element.moment} : {chant.titre}" if element.moment else chant.titre
    diapos = [Diapo(TITRE, [titre], element.pk, element.masque, "Titre")]
    for bloc in ordre_de_lecture(chant.couplets.all(), element.repeter_refrain):
        for i, paquet in enumerate(decouper_lignes(bloc.texte.splitlines(), lignes_par_diapo)):
            if i == 0 and bloc.type == paroles.COUPLET and bloc.numero:
                paquet = [f"{bloc.numero}. {paquet[0]}"] + paquet[1:]
            diapos.append(Diapo(PAROLES, paquet, element.pk, element.masque, _libelle_bloc(bloc)))
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
            diapos = diapos_du_chant(element, culte.lignes_par_diapo)
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
