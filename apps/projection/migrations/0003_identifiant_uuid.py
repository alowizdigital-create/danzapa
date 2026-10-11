import uuid

from django.db import migrations, models


def remplir(apps, schema_editor):
    """Un UUID différent pour chaque ligne existante (le défaut n'en donne qu'un)."""
    for nom in ('Theme',):
        Modele = apps.get_model("projection", nom)
        for ligne in Modele.objects.only("pk"):
            Modele.objects.filter(pk=ligne.pk).update(uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("projection", "0002_theme_classique")]

    operations = [
        migrations.AddField(
            model_name="theme",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(remplir, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="theme",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
