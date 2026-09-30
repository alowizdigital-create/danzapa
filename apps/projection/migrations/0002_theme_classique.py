from django.db import migrations


def creer_classique(apps, schema_editor):
    """Thème par défaut, reprenant la présentation PowerPoint actuelle :
    paroles blanches en gras sur fond noir, titres en majuscules, bandeau
    gris pour la bienvenue."""
    Theme = apps.get_model("projection", "Theme")
    Theme.objects.get_or_create(
        nom="Classique",
        defaults={
            "couleur_fond": "#000000",
            "couleur_texte": "#ffffff",
            "police": "Calibri",
            "police_titres": "Georgia",
            "gras": True,
            "taille_paroles": 54,
            "taille_titre": 32,
            "titres_majuscules": True,
            "couleur_bandeau": "#8f8f8f",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("projection", "0001_initial")]

    operations = [migrations.RunPython(creer_classique, migrations.RunPython.noop)]
