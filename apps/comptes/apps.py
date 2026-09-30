from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ComptesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comptes"
    label = "comptes"
    verbose_name = "Comptes et rôles"

    def ready(self):
        from .roles import synchroniser_roles

        # Recrée les groupes et leurs permissions après chaque migration :
        # les permissions des applications ajoutées plus tard sont ainsi
        # rattachées aux rôles sans étape manuelle.
        post_migrate.connect(synchroniser_roles, dispatch_uid="danzapa_roles")
