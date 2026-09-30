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
