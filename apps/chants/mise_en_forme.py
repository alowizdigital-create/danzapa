"""Texte mis en forme des diapos : nettoyage et lecture.

L'éditeur produit du HTML (contenteditable : gras, italique, souligné,
couleur, une ligne par <div> ou <br>). Ce HTML n'est jamais stocké tel quel :
il est relu en « lignes de morceaux stylés », puis réécrit sous une forme
canonique ne contenant que <div>, <br>, <b>, <i>, <u> et <span style="…"> (couleur,
ou « pas gras » quand le thème met déjà les paroles en gras).
Tout le reste (scripts, liens, images, attributs, autres styles) disparaît,
ce qui protège contre l'injection de code dans les pages.

La même lecture sert à l'export PowerPoint (un paragraphe par ligne, un
« run » par morceau stylé) et au calcul de la taille du texte.
"""

import re
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser

BLOCS = {"div", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
IGNORES = {"script", "style", "head", "title", "template", "noscript", "iframe", "object"}

RE_HEX = re.compile(r"^#([0-9a-f]{3}|[0-9a-f]{6})$", re.IGNORECASE)
RE_RGB = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*[\d.]+\s*)?\)$", re.IGNORECASE)


def couleur_valide(valeur):
    """Couleur au format #rrggbb, ou None si la valeur n'est pas reconnue."""
    valeur = (valeur or "").strip().lower()
    if m := RE_HEX.match(valeur):
        code = m.group(1)
        if len(code) == 3:
            code = "".join(c * 2 for c in code)
        return f"#{code}"
    if m := RE_RGB.match(valeur):
        r, g, b = (min(255, int(x)) for x in m.groups())
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


@dataclass(frozen=True)
class Style:
    # gras : True (gras), False (explicitement pas gras), None (comme le thème).
    gras: bool | None = None
    italique: bool = False
    souligne: bool = False
    couleur: str | None = None


@dataclass
class Morceau:
    texte: str
    style: Style


def _style_depuis_css(css, style):
    for declaration in (css or "").split(";"):
        if ":" not in declaration:
            continue
        nom, valeur = (x.strip().lower() for x in declaration.split(":", 1))
        if nom == "font-weight":
            if valeur in ("bold", "bolder") or valeur.isdigit() and int(valeur) >= 600:
                gras = True
            elif valeur in ("normal", "lighter") or valeur.isdigit():
                gras = False
            else:
                continue
            style = Style(gras, style.italique, style.souligne, style.couleur)
        elif nom == "font-style":
            style = Style(style.gras, valeur in ("italic", "oblique"), style.souligne, style.couleur)
        elif nom in ("text-decoration", "text-decoration-line"):
            style = Style(style.gras, style.italique, "underline" in valeur, style.couleur)
        elif nom == "color" and (c := couleur_valide(valeur)):
            style = Style(style.gras, style.italique, style.souligne, c)
    return style


class _Lecteur(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lignes = [[]]
        self.pile = [("racine", Style())]
        self.ignore = 0

    @property
    def style(self):
        return self.pile[-1][1]

    def nouvelle_ligne(self, forcer=False):
        if forcer or self.lignes[-1]:
            self.lignes.append([])

    def handle_starttag(self, balise, attributs):
        if balise in IGNORES:
            self.ignore += 1
            return
        if balise == "br":
            self.nouvelle_ligne(forcer=True)
            return
        if balise in BLOCS:
            self.nouvelle_ligne()
        attributs = dict(attributs)
        style = self.style
        if balise in ("b", "strong"):
            style = Style(True, style.italique, style.souligne, style.couleur)
        elif balise in ("i", "em"):
            style = Style(style.gras, True, style.souligne, style.couleur)
        elif balise == "u":
            style = Style(style.gras, style.italique, True, style.couleur)
        elif balise == "font" and (c := couleur_valide(attributs.get("color"))):
            style = Style(style.gras, style.italique, style.souligne, c)
        style = _style_depuis_css(attributs.get("style"), style)
        self.pile.append((balise, style))

    def handle_startendtag(self, balise, attributs):
        if balise == "br":
            self.nouvelle_ligne(forcer=True)

    def handle_endtag(self, balise):
        if balise in IGNORES:
            self.ignore = max(0, self.ignore - 1)
            return
        # Retire jusqu'à la balise ouvrante correspondante (HTML mal fermé toléré).
        for i in range(len(self.pile) - 1, 0, -1):
            if self.pile[i][0] == balise:
                del self.pile[i:]
                break
        if balise in BLOCS:
            self.nouvelle_ligne()

    def handle_data(self, donnees):
        if self.ignore:
            return
        texte = donnees.replace("\xa0", " ").replace("\r", "").replace("\n", " ")
        if not texte:
            return
        ligne = self.lignes[-1]
        if ligne and ligne[-1].style == self.style:
            ligne[-1].texte += texte
        else:
            ligne.append(Morceau(texte, self.style))


def lignes(html):
    """Lignes de morceaux stylés ; lignes vides au début et à la fin retirées."""
    lecteur = _Lecteur()
    lecteur.feed(html or "")
    lecteur.close()
    resultat = []
    for ligne in lecteur.lignes:
        morceaux = [m for m in ligne if m.texte]
        if morceaux:
            morceaux[0].texte = morceaux[0].texte.lstrip()
            morceaux[-1].texte = morceaux[-1].texte.rstrip()
            morceaux = [m for m in morceaux if m.texte]
        resultat.append(morceaux)
    while resultat and not resultat[0]:
        resultat.pop(0)
    while resultat and not resultat[-1]:
        resultat.pop()
    return resultat


def _html_morceau(morceau):
    html = escape(morceau.texte, quote=False)
    s = morceau.style
    css = []
    if s.couleur:
        css.append(f"color: {s.couleur}")
    if s.gras is False:
        css.append("font-weight: normal")
    if css:
        html = f'<span style="{"; ".join(css)}">{html}</span>'
    if s.souligne:
        html = f"<u>{html}</u>"
    if s.italique:
        html = f"<i>{html}</i>"
    if s.gras:
        html = f"<b>{html}</b>"
    return html


def nettoyer(html):
    """HTML canonique et sûr : une <div> par ligne, mise en forme autorisée seulement."""
    return "".join(
        f"<div>{''.join(_html_morceau(m) for m in ligne)}</div>" if ligne else "<div><br></div>"
        for ligne in lignes(html)
    )


def texte_brut(html):
    return "\n".join("".join(m.texte for m in ligne) for ligne in lignes(html))


def depuis_texte(texte):
    """HTML d'une diapo à partir de texte simple (une ligne par ligne)."""
    return "".join(
        f"<div>{escape(l.strip(), quote=False)}</div>" if l.strip() else "<div><br></div>"
        for l in (texte or "").strip().splitlines()
    )
