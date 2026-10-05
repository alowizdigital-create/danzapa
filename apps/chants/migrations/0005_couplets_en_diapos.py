"""Convertit les couplets (blocs découpés automatiquement) en diapos explicites.

Même découpage que l'éditeur jusqu'ici : paquets équilibrés d'au plus 4 lignes,
numéro du couplet devant sa première ligne. Les refrains ne sont pas répétés :
chaque chant reprend exactement l'ordre dans lequel il avait été saisi.
"""

from html import escape
from math import ceil

from django.db import migrations

LIGNES_PAR_DIAPO = 4


def paquets(lignes, maximum=LIGNES_PAR_DIAPO):
    if not lignes:
        return []
    nb = ceil(len(lignes) / maximum)
    taille, reste = divmod(len(lignes), nb)
    resultat, debut = [], 0
    for i in range(nb):
        fin = debut + taille + (1 if i < reste else 0)
        resultat.append(lignes[debut:fin])
        debut = fin
    return resultat


def convertir(apps, schema_editor):
    Chant = apps.get_model("chants", "Chant")
    Couplet = apps.get_model("chants", "Couplet")
    DiapoChant = apps.get_model("chants", "DiapoChant")
    for chant in Chant.objects.all():
        ordre = 0
        for couplet in Couplet.objects.filter(chant=chant).order_by("ordre", "pk"):
            lignes = [l.strip() for l in couplet.texte.splitlines() if l.strip()]
            for i, paquet in enumerate(paquets(lignes)):
                if i == 0 and couplet.type == "couplet" and couplet.numero:
                    paquet = [f"{couplet.numero}. {paquet[0]}"] + paquet[1:]
                ordre += 1
                DiapoChant.objects.create(
                    chant=chant,
                    ordre=ordre,
                    contenu="".join(f"<div>{escape(l, quote=False)}</div>" for l in paquet),
                    texte="\n".join(paquet),
                )


class Migration(migrations.Migration):
    dependencies = [("chants", "0004_diapochant")]

    operations = [migrations.RunPython(convertir, migrations.RunPython.noop)]
