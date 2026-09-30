from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from . import roles
from .models import Utilisateur


class RolesTests(TestCase):
    def test_les_trois_groupes_existent_apres_migration(self):
        noms = set(Group.objects.values_list("name", flat=True))
        self.assertTrue({roles.ADMINISTRATEUR, roles.EDITEUR, roles.LECTEUR} <= noms)

    def test_administrateur_gere_les_utilisateurs(self):
        groupe = Group.objects.get(name=roles.ADMINISTRATEUR)
        codes = set(groupe.permissions.values_list("codename", flat=True))
        self.assertIn("add_utilisateur", codes)
        self.assertIn("change_utilisateur", codes)

    def test_editeur_et_lecteur_ne_gerent_pas_les_utilisateurs(self):
        for nom in (roles.EDITEUR, roles.LECTEUR):
            codes = set(Group.objects.get(name=nom).permissions.values_list("codename", flat=True))
            self.assertNotIn("add_utilisateur", codes)

    def test_synchronisation_idempotente(self):
        roles.synchroniser_roles()
        roles.synchroniser_roles()
        self.assertEqual(Group.objects.filter(name=roles.EDITEUR).count(), 1)

    def test_role_affiche(self):
        u = Utilisateur.objects.create_user("marie", password="x")
        self.assertEqual(u.role, "Aucun rôle")
        u.groups.add(Group.objects.get(name=roles.EDITEUR))
        self.assertEqual(u.role, roles.EDITEUR)
        self.assertTrue(u.est_editeur)
        self.assertFalse(u.est_administrateur)


class ConnexionTests(TestCase):
    def setUp(self):
        self.utilisateur = Utilisateur.objects.create_user("paul", password="MotDePasse-Solide-42")

    def test_accueil_redirige_vers_connexion_si_anonyme(self):
        reponse = self.client.get(reverse("accueil"))
        self.assertRedirects(reponse, f"{reverse('comptes:connexion')}?next=/")

    def test_connexion_puis_accueil(self):
        reponse = self.client.post(
            reverse("comptes:connexion"),
            {"username": "paul", "password": "MotDePasse-Solide-42"},
        )
        self.assertRedirects(reponse, reverse("accueil"))
        reponse = self.client.get(reverse("accueil"))
        self.assertContains(reponse, "paul")

    def test_mauvais_mot_de_passe(self):
        reponse = self.client.post(
            reverse("comptes:connexion"), {"username": "paul", "password": "faux"}
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(reponse.wsgi_request.user.is_authenticated)

    def test_deconnexion(self):
        self.client.force_login(self.utilisateur)
        reponse = self.client.post(reverse("comptes:deconnexion"))
        self.assertRedirects(reponse, reverse("comptes:connexion"))
