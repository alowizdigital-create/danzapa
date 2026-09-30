from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "role_affiche", "is_active")
    list_filter = ("groups", "is_active", "is_staff")

    @admin.display(description="rôle")
    def role_affiche(self, obj):
        return obj.role


admin.site.site_header = "Administration Danzapa"
admin.site.site_title = "Danzapa"
admin.site.index_title = "Gestion de l'application"
