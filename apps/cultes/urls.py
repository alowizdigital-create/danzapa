from django.urls import path

from . import views

app_name = "cultes"

urlpatterns = [
    path("", views.CulteListe.as_view(), name="liste"),
    path("nouveau/", views.CulteCreation.as_view(), name="creation"),
    path("<int:pk>/", views.editeur, name="editeur"),
    path("<int:pk>/export.pptx", views.exporter_pptx, name="export_pptx"),
    path("<int:pk>/projection/", views.projection, name="projection"),
    path("<int:pk>/supprimer/", views.CulteSuppression.as_view(), name="suppression"),
    path("<int:pk>/dupliquer/", views.dupliquer, name="dupliquer"),
    path("<int:pk>/parametres/", views.parametres, name="parametres"),
    path("<int:pk>/chants/", views.chercher_chants, name="chercher_chants"),
    path("<int:pk>/ajouter-chant/", views.ajouter_chant, name="ajouter_chant"),
    path("<int:pk>/ajouter-texte/", views.ajouter_texte, name="ajouter_texte"),
    path("<int:pk>/creer-chant/", views.creer_chant, name="creer_chant"),
    path("<int:pk>/chants/<int:chant_pk>/infos/", views.infos_chant, name="infos_chant"),
    path("<int:pk>/chants/<int:chant_pk>/supprimer/", views.supprimer_chant_bibliotheque, name="supprimer_chant"),
    path("<int:pk>/chants/<int:chant_pk>/diapos/ajouter/", views.ajouter_diapo, name="ajouter_diapo"),
    path("<int:pk>/chants/<int:chant_pk>/diapos/reordonner/", views.reordonner_diapos, name="reordonner_diapos"),
    path("<int:pk>/chants/<int:chant_pk>/diapos/<int:piece_pk>/", views.enregistrer_diapo, name="enregistrer_diapo"),
    path(
        "<int:pk>/chants/<int:chant_pk>/diapos/<int:piece_pk>/supprimer/",
        views.supprimer_diapo,
        name="supprimer_diapo",
    ),
    path(
        "<int:pk>/chants/<int:chant_pk>/diapos/<int:piece_pk>/deplacer/",
        views.deplacer_diapo,
        name="deplacer_diapo",
    ),
    path("<int:pk>/reordonner/", views.reordonner, name="reordonner"),
    path("<int:pk>/elements/<int:element_pk>/", views.modifier_element, name="modifier_element"),
    path("<int:pk>/elements/<int:element_pk>/masquer/", views.basculer_masque, name="basculer_masque"),
    path("<int:pk>/elements/<int:element_pk>/deplacer/", views.deplacer_element, name="deplacer_element"),
    path("<int:pk>/elements/<int:element_pk>/supprimer/", views.supprimer_element, name="supprimer_element"),
]
