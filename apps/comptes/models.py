from django.contrib.auth.models import AbstractUser

from . import roles


class Utilisateur(AbstractUser):
    """Utilisateur de Danzapa.

    Modèle personnalisé dès le départ pour pouvoir ajouter des champs
    (église, préférences d'affichage…) sans migration délicate plus tard.
    """

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def a_le_role(self, nom):
        return self.groups.filter(name=nom).exists()

    @property
    def est_administrateur(self):
        return self.is_superuser or self.a_le_role(roles.ADMINISTRATEUR)

    @property
    def est_editeur(self):
        return self.est_administrateur or self.a_le_role(roles.EDITEUR)

    @property
    def role(self):
        """Libellé du rôle le plus élevé, pour l'affichage."""
        if self.est_administrateur:
            return roles.ADMINISTRATEUR
        if self.a_le_role(roles.EDITEUR):
            return roles.EDITEUR
        if self.a_le_role(roles.LECTEUR):
            return roles.LECTEUR
        return "Aucun rôle"
