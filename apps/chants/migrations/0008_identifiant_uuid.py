import uuid

from django.db import migrations, models


def remplir(apps, schema_editor):
    """Un UUID différent pour chaque ligne existante (le défaut n'en donne qu'un)."""
    for nom in ('Chant', 'DiapoChant'):
        Modele = apps.get_model("chants", nom)
        for ligne in Modele.objects.only("pk"):
            Modele.objects.filter(pk=ligne.pk).update(uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("chants", "0007_taille_et_police_par_diapo")]

    operations = [
        migrations.AddField(
            model_name="chant",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="diapochant",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(remplir, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chant",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="diapochant",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
