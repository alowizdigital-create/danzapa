import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chants", "0003_alter_chant_options")]

    operations = [
        migrations.CreateModel(
            name="DiapoChant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordre", models.PositiveIntegerField()),
                ("contenu", models.TextField(blank=True)),
                ("texte", models.TextField(blank=True, editable=False)),
                (
                    "alignement",
                    models.CharField(
                        choices=[("gauche", "Gauche"), ("centre", "Centré"), ("droite", "Droite")],
                        default="centre",
                        max_length=10,
                    ),
                ),
                (
                    "echelle",
                    models.PositiveSmallIntegerField(
                        default=100,
                        validators=[
                            django.core.validators.MinValueValidator(50),
                            django.core.validators.MaxValueValidator(200),
                        ],
                        verbose_name="taille (%)",
                    ),
                ),
                (
                    "couleur_fond",
                    models.CharField(
                        blank=True,
                        help_text="Vide : couleur du thème.",
                        max_length=7,
                        validators=[django.core.validators.RegexValidator("^#[0-9a-fA-F]{6}$", "Couleur au format #RRGGBB.")],
                        verbose_name="couleur de fond",
                    ),
                ),
                (
                    "chant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="diapos", to="chants.chant"
                    ),
                ),
            ],
            options={
                "verbose_name": "diapo de chant",
                "verbose_name_plural": "diapos de chant",
                "ordering": ["chant_id", "ordre", "pk"],
            },
        ),
    ]
