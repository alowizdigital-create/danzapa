from django.contrib import admin

from .models import Theme


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("nom", "police", "taille_paroles", "couleur_fond", "couleur_texte", "date_modification")
    search_fields = ("nom",)
