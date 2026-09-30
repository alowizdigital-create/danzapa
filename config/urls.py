from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.comptes.views import accueil

urlpatterns = [
    path("", accueil, name="accueil"),
    path("comptes/", include("apps.comptes.urls")),
    path("chants/", include("apps.chants.urls")),
    path("cultes/", include("apps.cultes.urls")),
    path("themes/", include("apps.projection.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # En production, les images envoyées (thèmes) sont servies par l'hébergeur.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
