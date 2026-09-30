from django.urls import path

from . import views

app_name = "cultes"

urlpatterns = [
    path("", views.CulteListe.as_view(), name="liste"),
    path("nouveau/", views.CulteCreation.as_view(), name="creation"),
    path("<int:pk>/", views.editeur, name="editeur"),
    path("<int:pk>/export.pptx", views.exporter_pptx, name="export_pptx"),
    path("<int:pk>/supprimer/", views.CulteSuppression.as_view(), name="suppression"),
    path("<int:pk>/dupliquer/", views.dupliquer, name="dupliquer"),
    path("<int:pk>/parametres/", views.parametres, name="parametres"),
    path("<int:pk>/chants/", views.chercher_chants, name="chercher_chants"),
    path("<int:pk>/ajouter-chant/", views.ajouter_chant, name="ajouter_chant"),
    path("<int:pk>/ajouter-texte/", views.ajouter_texte, name="ajouter_texte"),
    path("<int:pk>/nouveau-chant/", views.nouveau_chant, name="nouveau_chant"),
    path("<int:pk>/reordonner/", views.reordonner, name="reordonner"),
    path("<int:pk>/elements/<int:element_pk>/", views.modifier_element, name="modifier_element"),
    path("<int:pk>/elements/<int:element_pk>/masquer/", views.basculer_masque, name="basculer_masque"),
    path("<int:pk>/elements/<int:element_pk>/deplacer/", views.deplacer_element, name="deplacer_element"),
    path("<int:pk>/elements/<int:element_pk>/supprimer/", views.supprimer_element, name="supprimer_element"),
]
