"""Découpage des paroles collées en couplets, refrains et ponts.

Format attendu (celui des présentations actuelles) :

    1. Sans attendre
    Je veux tendre
    Au bonheur promis

    Refrain
    Donc en route
    Point de doute

    2. Deuxième couplet…

- Les blocs sont séparés par une ligne vide.
- « 1. », « 1) » ou « 1 - » en tête de bloc donne le numéro du couplet.
  Sans numéro, les couplets sont numérotés à la suite.
- « Refrain », « R: », « Chorus », « Pont » ou « Bridge », seul sur la
  première ligne ou suivi de « : », marque le type du bloc.

`vers_texte` fait l'opération inverse, pour réafficher les paroles dans le
formulaire de modification.
"""

import re
from dataclasses import dataclass

COUPLET = "couplet"
REFRAIN = "refrain"
PONT = "pont"

ETIQUETTES = {
    "refrain": REFRAIN,
    "chorus": REFRAIN,
    "r": REFRAIN,
    "pont": PONT,
    "bridge": PONT,
}

_MOTS = "|".join(ETIQUETTES)
# Étiquette seule sur sa ligne : « Refrain », « Refrain : », « R. »
RE_ETIQUETTE_SEULE = re.compile(rf"^({_MOTS})\s*[:.)]?$", re.IGNORECASE)
# Étiquette suivie du texte : « Refrain : Donc en route »
RE_ETIQUETTE_EN_LIGNE = re.compile(rf"^({_MOTS})\s*[:.)]\s*(.+)$", re.IGNORECASE)
# Numéro de couplet : « 1. », « 2) », « 3 - », « 4: »
RE_NUMERO = re.compile(r"^(\d{1,3})\s*[.):\-]\s*(.*)$")

LIBELLES = {COUPLET: "Couplet", REFRAIN: "Refrain", PONT: "Pont"}


@dataclass
class Bloc:
    type: str
    numero: int | None
    texte: str


def _blocs_bruts(texte):
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    lignes = [ligne.strip() for ligne in texte.split("\n")]
    bloc = []
    for ligne in lignes:
        if ligne:
            bloc.append(ligne)
        elif bloc:
            yield bloc
            bloc = []
    if bloc:
        yield bloc


def decouper_paragraphes(texte):
    """Listes de lignes non vides, un paragraphe par ligne vide."""
    return list(_blocs_bruts(texte or ""))


def decouper(texte):
    """Transforme le texte collé en une liste de `Bloc`."""
    blocs = []
    dernier_numero = 0
    for lignes in _blocs_bruts(texte or ""):
        premiere = lignes[0]
        type_bloc, numero = COUPLET, None

        if m := RE_ETIQUETTE_SEULE.match(premiere):
            type_bloc = ETIQUETTES[m.group(1).lower()]
            lignes = lignes[1:]
        elif m := RE_ETIQUETTE_EN_LIGNE.match(premiere):
            type_bloc = ETIQUETTES[m.group(1).lower()]
            lignes = [m.group(2)] + lignes[1:]
        elif m := RE_NUMERO.match(premiere):
            numero = int(m.group(1))
            lignes = ([m.group(2)] if m.group(2) else []) + lignes[1:]

        if not lignes:
            # Étiquette ou numéro sans texte : on l'ignore.
            continue

        if type_bloc == COUPLET:
            if numero is None:
                numero = dernier_numero + 1
            dernier_numero = numero

        blocs.append(Bloc(type=type_bloc, numero=numero, texte="\n".join(lignes)))
    return blocs


def vers_texte(blocs):
    """Inverse de `decouper` : produit un texte qui redonne les mêmes blocs."""
    parties = []
    for bloc in blocs:
        if bloc.type == COUPLET:
            parties.append(f"{bloc.numero}. {bloc.texte}" if bloc.numero else bloc.texte)
        else:
            parties.append(f"{LIBELLES[bloc.type]}\n{bloc.texte}")
    return "\n\n".join(parties)
