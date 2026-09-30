from django.urls import path

from . import views

app_name = "chants"

urlpatterns = [
    path("", views.ChantListe.as_view(), name="liste"),
    path("nouveau/", views.ChantCreation.as_view(), name="creation"),
    path("<int:pk>/", views.ChantDetail.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.ChantModification.as_view(), name="modification"),
    path("<int:pk>/supprimer/", views.ChantSuppression.as_view(), name="suppression"),
]
