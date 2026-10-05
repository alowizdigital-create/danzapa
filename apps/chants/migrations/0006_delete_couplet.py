from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("chants", "0005_couplets_en_diapos")]

    operations = [migrations.DeleteModel(name="Couplet")]
