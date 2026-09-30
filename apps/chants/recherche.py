import unicodedata


def normaliser(texte):
    """Minuscules, sans accents ni apostrophes typographiques.

    Permet de trouver « s'élance » en tapant « s elance » ou « S’ÉLANCE »,
    quelle que soit la base de données.
    """
    texte = unicodedata.normalize("NFKD", texte or "")
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower().replace("’", "'").replace("'", " ")
    return " ".join(texte.split())


def filtrer(chants, q):
    """Chants contenant tous les mots de `q` (titre, auteur, tags ou paroles)."""
    for mot in normaliser(q).split():
        chants = chants.filter(recherche__contains=mot)
    return chants


def titres_d_abord(chants, q):
    """Place en tête les chants dont le titre contient tous les mots cherchés."""
    mots = normaliser(q).split()
    return sorted(chants, key=lambda c: not all(m in normaliser(c.titre) for m in mots))
