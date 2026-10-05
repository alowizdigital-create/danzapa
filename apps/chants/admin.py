from django.contrib import admin

from .models import Chant, DiapoChant


class DiapoInline(admin.TabularInline):
    model = DiapoChant
    extra = 0
    fields = ("ordre", "texte", "alignement", "taille", "police", "couleur_fond")
    readonly_fields = ("texte",)


@admin.register(Chant)
class ChantAdmin(admin.ModelAdmin):
    list_display = ("titre", "auteur", "tags", "date_modification")
    search_fields = ("titre", "auteur", "tags", "recherche")
    readonly_fields = ("cree_par", "date_ajout", "date_modification")
    inlines = [DiapoInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.mettre_a_jour_recherche()
