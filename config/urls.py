from django.contrib import admin
from django.urls import include, path

from apps.comptes.views import accueil

urlpatterns = [
    path("", accueil, name="accueil"),
    path("comptes/", include("apps.comptes.urls")),
    path("chants/", include("apps.chants.urls")),
    path("cultes/", include("apps.cultes.urls")),
    path("admin/", admin.site.urls),
]
