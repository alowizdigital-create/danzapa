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


class ProductionTests(TestCase):
    def test_sante(self):
        reponse = self.client.get(reverse("sante"))
        self.assertEqual((reponse.status_code, reponse.content), (200, b"ok"))

    def test_origines_csrf_deduites_des_hotes(self):
        from config.settings import origines_https

        self.assertEqual(
            origines_https(["danzapa.eglise.org", ".eglise.org", "localhost", "127.0.0.1", "*"]),
            ["https://danzapa.eglise.org", "https://eglise.org"],
        )


class SauvegardeTests(TestCase):
    def test_archive_contient_la_base_et_garde_les_dernieres(self):
        import tarfile
        import tempfile
        from io import StringIO
        from pathlib import Path

        from django.core.management import call_command
        from django.test import override_settings

        with tempfile.TemporaryDirectory() as dossier:
            with override_settings(DATA_DIR=Path(dossier), MEDIA_ROOT=Path(dossier) / "media"):
                (Path(dossier) / "media" / "themes").mkdir(parents=True)
                (Path(dossier) / "media" / "themes" / "fond.png").write_bytes(b"png")
                sauvegardes = Path(dossier) / "sauvegardes"
                sauvegardes.mkdir()
                for i in range(3):
                    (sauvegardes / f"danzapa-2020010{i}-000000.tar.gz").write_bytes(b"")
                call_command("sauvegarde", garder=2, stdout=StringIO())
                archives = sorted(sauvegardes.glob("*.tar.gz"))
                self.assertEqual(len(archives), 2)
                with tarfile.open(archives[-1]) as tar:
                    noms = tar.getnames()
                self.assertIn("db.sqlite3", noms)
                self.assertIn("media/themes/fond.png", noms)
                with tarfile.open(archives[-1]) as tar:
                    tar.extract("db.sqlite3", dossier, filter="data")
                import sqlite3

                base = sqlite3.connect(Path(dossier) / "db.sqlite3")
                groupes = [n for (n,) in base.execute("SELECT name FROM auth_group")]
                base.close()
                self.assertIn("Éditeur", groupes)


class ConfigurationProductionTests(TestCase):
    def test_fichier_env_valeurs_par_defaut_sans_ecraser(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest import mock

        from config.settings import charger_fichier_env

        with tempfile.TemporaryDirectory() as dossier:
            fichier = Path(dossier) / "production.env"
            fichier.write_text("# commentaire\nDANZAPA_A=fichier\nDANZAPA_B=fichier\nDANZAPA_VIDE=\n\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"DANZAPA_B": "dokploy"}, clear=False):
                charger_fichier_env(fichier)
                self.assertEqual(os.environ["DANZAPA_A"], "fichier")
                self.assertEqual(os.environ["DANZAPA_B"], "dokploy")
                self.assertNotIn("DANZAPA_VIDE", os.environ)
                os.environ.pop("DANZAPA_A")

    def test_fichier_versionne_sans_secret(self):
        from django.conf import settings

        contenu = (settings.BASE_DIR / "config" / "production.env").read_text(encoding="utf-8")
        lignes = [l for l in contenu.splitlines() if l.strip() and not l.startswith("#")]
        self.assertFalse([l for l in lignes if "PASSWORD" in l or "SECRET" in l])

    def test_cle_secrete_generee_une_fois(self):
        import tempfile
        from pathlib import Path

        from config.settings import cle_persistante

        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "data" / "secret_key"
            cle = cle_persistante(chemin)
            self.assertGreater(len(cle), 40)
            self.assertEqual(cle_persistante(chemin), cle)
            self.assertEqual(chemin.stat().st_mode & 0o777, 0o600)


class PremierAdminTests(TestCase):
    def appeler(self, **env):
        import os
        from io import StringIO
        from unittest import mock

        from django.core.management import call_command

        sortie = StringIO()
        variables = {"DJANGO_SUPERUSER_USERNAME": "", "DJANGO_SUPERUSER_PASSWORD": "", "DJANGO_SUPERUSER_RESET": "", **env}
        with mock.patch.dict(os.environ, variables):
            call_command("premier_admin", stdout=sortie)
        return sortie.getvalue()

    def test_mot_de_passe_provisoire_affiche_une_fois(self):
        import re

        sortie = self.appeler(DJANGO_SUPERUSER_USERNAME="admin")
        mot_de_passe = re.search(r"Mot de passe provisoire : (\S+)", sortie).group(1)
        self.assertRegex(mot_de_passe, r"^[a-hjkmnp-z2-9]{4}(-[a-hjkmnp-z2-9]{4}){3}$")
        admin = Utilisateur.objects.get(username="admin")
        self.assertTrue(admin.is_superuser and admin.check_password(mot_de_passe))
        self.assertEqual(admin.role, roles.ADMINISTRATEUR)
        self.assertEqual(self.appeler(DJANGO_SUPERUSER_USERNAME="admin"), "")

    def test_mot_de_passe_fourni(self):
        sortie = self.appeler(DJANGO_SUPERUSER_USERNAME="chef", DJANGO_SUPERUSER_PASSWORD="Fourni-2026")
        self.assertNotIn("provisoire", sortie)
        self.assertTrue(Utilisateur.objects.get(username="chef").check_password("Fourni-2026"))

    def test_sans_identifiant_rien(self):
        self.appeler()
        self.assertFalse(Utilisateur.objects.exists())

    def test_reinitialisation_seulement_avec_reset(self):
        self.appeler(DJANGO_SUPERUSER_USERNAME="admin", DJANGO_SUPERUSER_PASSWORD="Ancien-2026")
        admin = Utilisateur.objects.get(username="admin")
        self.appeler(DJANGO_SUPERUSER_USERNAME="admin", DJANGO_SUPERUSER_PASSWORD="Nouveau-2026")
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Ancien-2026"))
        sortie = self.appeler(
            DJANGO_SUPERUSER_USERNAME="admin", DJANGO_SUPERUSER_PASSWORD="Nouveau-2026", DJANGO_SUPERUSER_RESET="1"
        )
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Nouveau-2026"))
        self.assertIn("remplacé", sortie)


class AlerteVolumeTests(TestCase):
    def test_bandeau_sans_volume(self):
        from django.test import override_settings

        with override_settings(DONNEES_PERSISTANTES=False):
            reponse = self.client.get(reverse("comptes:connexion"))
            self.assertContains(reponse, "ne sont pas enregistrées durablement")
            sante = self.client.get(reverse("sante"))
            self.assertEqual(sante.status_code, 200)
            self.assertIn(b"sans volume", sante.content)
        reponse = self.client.get(reverse("comptes:connexion"))
        self.assertNotContains(reponse, "ne sont pas enregistrées durablement")

    def test_detection(self):
        from pathlib import Path

        from config.settings import donnees_persistantes

        self.assertTrue(donnees_persistantes(Path("/home/projet")))  # hors Docker
