from django.contrib import admin

from .models import Culte, ElementCulte


class ElementInline(admin.TabularInline):
    model = ElementCulte
    extra = 0
    fields = ("ordre", "type", "moment", "chant", "repeter_refrain", "masque", "titre")
    autocomplete_fields = ("chant",)


@admin.register(Culte)
class CulteAdmin(admin.ModelAdmin):
    list_display = ("titre", "date", "statut", "cree_par", "date_modification")
    list_filter = ("statut",)
    date_hierarchy = "date"
    search_fields = ("titre",)
    readonly_fields = ("cree_par", "date_creation", "date_modification")
    inlines = [ElementInline]
