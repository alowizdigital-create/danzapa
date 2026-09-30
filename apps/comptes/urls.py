from django.contrib.auth import views as auth_views
from django.urls import path

app_name = "comptes"

urlpatterns = [
    path(
        "connexion/",
        auth_views.LoginView.as_view(template_name="comptes/connexion.html", redirect_authenticated_user=True),
        name="connexion",
    ),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path(
        "mot-de-passe/",
        auth_views.PasswordChangeView.as_view(
            template_name="comptes/mot_de_passe.html",
            success_url="/comptes/mot-de-passe/modifie/",
        ),
        name="mot_de_passe",
    ),
    path(
        "mot-de-passe/modifie/",
        auth_views.PasswordChangeDoneView.as_view(template_name="comptes/mot_de_passe_modifie.html"),
        name="mot_de_passe_modifie",
    ),
]
