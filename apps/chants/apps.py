from django.apps import AppConfig


class ChantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chants"
    label = "chants"
    verbose_name = "Bibliothèque de chants"
