import uuid

from django.db import migrations, models


def remplir(apps, schema_editor):
    """Un UUID différent pour chaque ligne existante (le défaut n'en donne qu'un)."""
    for nom in ('Culte', 'ElementCulte'):
        Modele = apps.get_model("cultes", nom)
        for ligne in Modele.objects.only("pk"):
            Modele.objects.filter(pk=ligne.pk).update(uuid=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("cultes", "0003_remove_elementculte_repeter_refrain")]

    operations = [
        migrations.AddField(
            model_name="culte",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="elementculte",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(remplir, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="culte",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="elementculte",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
