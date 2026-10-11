from django.urls import path

from . import views

app_name = "cultes"

urlpatterns = [
    path("", views.CulteListe.as_view(), name="liste"),
    path("nouveau/", views.CulteCreation.as_view(), name="creation"),
    path("<uuid:pk>/", views.editeur, name="editeur"),
    path("<uuid:pk>/export.pptx", views.exporter_pptx, name="export_pptx"),
    path("<uuid:pk>/export.pdf", views.exporter_pdf, name="export_pdf"),
    path("<uuid:pk>/projection/", views.projection, name="projection"),
    path("<uuid:uuid>/supprimer/", views.CulteSuppression.as_view(), name="suppression"),
    path("<uuid:pk>/dupliquer/", views.dupliquer, name="dupliquer"),
    path("<uuid:pk>/parametres/", views.parametres, name="parametres"),
    path("<uuid:pk>/chants/", views.chercher_chants, name="chercher_chants"),
    path("<uuid:pk>/ajouter-chant/", views.ajouter_chant, name="ajouter_chant"),
    path("<uuid:pk>/ajouter-texte/", views.ajouter_texte, name="ajouter_texte"),
    path("<uuid:pk>/ajouter-image/", views.ajouter_image, name="ajouter_image"),
    path("<uuid:pk>/bienvenue/", views.enregistrer_bienvenue, name="enregistrer_bienvenue"),
    path("<uuid:pk>/creer-chant/", views.creer_chant, name="creer_chant"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/infos/", views.infos_chant, name="infos_chant"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/supprimer/", views.supprimer_chant_bibliotheque, name="supprimer_chant"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/diapos/ajouter/", views.ajouter_diapo, name="ajouter_diapo"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/fond/", views.fond_du_chant, name="fond_chant"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/animation/", views.animation_du_chant, name="animation_chant"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/diapos/reordonner/", views.reordonner_diapos, name="reordonner_diapos"),
    path("<uuid:pk>/chants/<uuid:chant_pk>/diapos/<uuid:piece_pk>/", views.enregistrer_diapo, name="enregistrer_diapo"),
    path(
        "<uuid:pk>/chants/<uuid:chant_pk>/diapos/<uuid:piece_pk>/supprimer/",
        views.supprimer_diapo,
        name="supprimer_diapo",
    ),
    path(
        "<uuid:pk>/chants/<uuid:chant_pk>/diapos/<uuid:piece_pk>/deplacer/",
        views.deplacer_diapo,
        name="deplacer_diapo",
    ),
    path("<uuid:pk>/reordonner/", views.reordonner, name="reordonner"),
    path("<uuid:pk>/elements/<uuid:element_pk>/", views.modifier_element, name="modifier_element"),
    path("<uuid:pk>/elements/<uuid:element_pk>/masquer/", views.basculer_masque, name="basculer_masque"),
    path("<uuid:pk>/elements/<uuid:element_pk>/deplacer/", views.deplacer_element, name="deplacer_element"),
    path("<uuid:pk>/elements/<uuid:element_pk>/supprimer/", views.supprimer_element, name="supprimer_element"),
]
