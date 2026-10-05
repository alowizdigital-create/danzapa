from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.comptes.views import accueil, sante

urlpatterns = [
    path("", accueil, name="accueil"),
    path("sante/", sante, name="sante"),
    path("comptes/", include("apps.comptes.urls")),
    path("cultes/", include("apps.cultes.urls")),
    path("themes/", include("apps.projection.urls")),
    path("admin/", admin.site.urls),
]

# Images envoyées (thèmes). Elles sont peu nombreuses et peu consultées : Django
# les sert lui-même, y compris en production, ce qui évite un serveur Nginx
# dédié à côté du conteneur. (`static()` ne fonctionne qu'en DEBUG.)
def media(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [re_path(r"^media/(?P<path>.*)$", media)]
