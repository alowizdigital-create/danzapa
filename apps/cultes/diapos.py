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
IMAGE = "image"


@dataclass
class Diapo:
    type: str
    lignes: list[str]
    element_id: str | None = None  # identifiants publics (UUID) : élément, chant, diapo
    masque: bool = False
    libelle: str = ""
    numero: int = 0  # position dans le culte, à partir de 1
    # Diapos de chant : texte mis en forme (HTML nettoyé) et réglages de la diapo.
    html: str = ""
    alignement: str = "centre"
    echelle: int = 100
    taille: int | None = None  # pt choisis ; None : automatique
    police: str = ""  # vide : police du thème
    interligne: int | None = None  # en % ; None : automatique
    image_url: str = ""  # diapo image
    image_nom: str = ""  # fichier dans MEDIA_ROOT (exports)
    animation: str = ""  # entrée du texte (DiapoChant.ANIMATIONS)
    vitesse_animation: str = "normale"
    couleur_fond: str = ""
    chant_id: str | None = None
    piece_id: str | None = None  # DiapoChant correspondante


@dataclass
class Groupe:
    """Les diapos d'un même élément du culte (déplacées ensemble)."""

    element: object | None
    diapos: list[Diapo] = field(default_factory=list)


def diapos_du_chant(element):
    """Diapo titre « Moment : Titre », puis les diapos du chant telles que saisies."""
    chant = element.chant
    titre = f"{element.moment} : {chant.titre}" if element.moment else chant.titre
    diapos = [Diapo(TITRE, [titre], str(element.uuid), element.masque, "Titre", chant_id=str(chant.uuid))]
    for rang, piece in enumerate(chant.diapos.all(), start=1):
        diapos.append(
            Diapo(
                PAROLES,
                piece.texte.split("\n") if piece.texte else [""],
                str(element.uuid),
                element.masque,
                f"Diapo {rang}",
                html=piece.contenu,
                alignement=piece.alignement,
                echelle=piece.echelle,
                taille=piece.taille,
                police=piece.police,
                interligne=piece.interligne,
                animation=piece.animation,
                vitesse_animation=piece.vitesse_animation,
                couleur_fond=piece.couleur_fond,
                chant_id=str(chant.uuid),
                piece_id=str(piece.uuid),
            )
        )
    return diapos


def diapos_du_texte(element):
    diapos = []
    entete = " : ".join(p for p in (element.moment, element.titre) if p)
    if entete:
        diapos.append(Diapo(TITRE, [entete], str(element.uuid), element.masque, "Titre"))
    for paragraphe in paroles.decouper_paragraphes(element.contenu):
        diapos.append(Diapo(TEXTE, paragraphe, str(element.uuid), element.masque, "Texte"))
    if not diapos:
        diapos.append(Diapo(TEXTE, [""], str(element.uuid), element.masque, "Texte"))
    return diapos


def diapos_de_l_image(element):
    """Diapo titre « Moment : Titre » si un moment est donné, puis l'image (titre en légende)."""
    diapos = []
    if element.moment:
        entete = " : ".join(p for p in (element.moment, element.titre) if p)
        diapos.append(Diapo(TITRE, [entete], str(element.uuid), element.masque, "Titre"))
    diapos.append(
        Diapo(
            IMAGE,
            [element.titre] if element.titre else [],
            str(element.uuid),
            element.masque,
            "Image",
            image_url=element.image.url if element.image else "",
            image_nom=element.image.name if element.image else "",
        )
    )
    return diapos


# Identifiant d'édition de la diapo de bienvenue (comme un chant à une seule diapo).
ID_BIENVENUE = "bienvenue"


def diapo_de_bienvenue(culte):
    """Diapo de bienvenue : texte simple modifiable sur place, avec ses réglages.
    Vide, elle reste dans l'éditeur mais n'est ni projetée ni exportée (masquée)."""
    from apps.chants import mise_en_forme

    reglages = culte.bienvenue_reglages or {}
    html = culte.bienvenue_html
    texte = mise_en_forme.texte_brut(html) if html else ""
    vide = not texte.strip()
    return Diapo(
        BIENVENUE,
        texte.split("\n") if texte else [""],
        masque=vide,
        libelle="Bienvenue (vide : non projetée)" if vide else "Bienvenue",
        html=html,
        alignement=reglages.get("alignement") or "centre",
        taille=reglages.get("taille"),
        police=reglages.get("police") or "",
        interligne=reglages.get("interligne"),
        couleur_fond=reglages.get("couleur_fond") or "",
        animation=reglages.get("animation") or "",
        vitesse_animation=reglages.get("vitesse_animation") or "normale",
        chant_id=ID_BIENVENUE,
        piece_id=ID_BIENVENUE,
    )


def groupes_du_culte(culte, elements=None):
    """Diapos regroupées par élément ; le premier groupe (bienvenue) n'a pas d'élément."""
    if elements is None:
        elements = culte.elements_complets()
    groupes = []
    groupes.append(Groupe(None, [diapo_de_bienvenue(culte)]))
    for element in elements:
        if element.type == element.CHANT and element.chant:
            diapos = diapos_du_chant(element)
        elif element.type == element.IMAGE:
            diapos = diapos_de_l_image(element)
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
