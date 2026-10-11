from django.urls import path

from . import views

app_name = "projection"

urlpatterns = [
    path("", views.ThemeListe.as_view(), name="theme_liste"),
    path("nouveau/", views.ThemeCreation.as_view(), name="theme_creation"),
    path("<uuid:uuid>/", views.ThemeModification.as_view(), name="theme_modification"),
    path("<uuid:uuid>/supprimer/", views.ThemeSuppression.as_view(), name="theme_suppression"),
]
