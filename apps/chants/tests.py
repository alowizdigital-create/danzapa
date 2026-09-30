from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.comptes import roles
from apps.comptes.models import Utilisateur

from . import paroles
from .models import Chant
from .recherche import normaliser

SANS_ATTENDRE = """1. Sans attendre
Je veux tendre
Au bonheur promis

Refrain
Donc en route
Point de doute
Le but est si grand

2. Qui s’élance
Qui s’avance
Obtiendra le prix
"""


class DecoupageTests(TestCase):
    def test_couplets_numerotes_et_refrain(self):
        blocs = paroles.decouper(SANS_ATTENDRE)
        self.assertEqual(
            [(b.type, b.numero) for b in blocs],
            [("couplet", 1), ("refrain", None), ("couplet", 2)],
        )
        self.assertEqual(blocs[0].texte, "Sans attendre\nJe veux tendre\nAu bonheur promis")
        self.assertEqual(blocs[1].texte, "Donc en route\nPoint de doute\nLe but est si grand")

    def test_numerotation_automatique(self):
        blocs = paroles.decouper("Premier\ncouplet\n\nDeuxième\ncouplet")
        self.assertEqual([b.numero for b in blocs], [1, 2])

    def test_numerotation_reprend_apres_numero_explicite(self):
        blocs = paroles.decouper("3. Troisième\n\nSuivant")
        self.assertEqual([b.numero for b in blocs], [3, 4])

    def test_etiquette_en_ligne_et_variantes(self):
        blocs = paroles.decouper("R: Alléluia\nAmen\n\nPont :\nGloire\n\n2) Couplet")
        self.assertEqual([b.type for b in blocs], ["refrain", "pont", "couplet"])
        self.assertEqual(blocs[0].texte, "Alléluia\nAmen")
        self.assertEqual(blocs[2].numero, 2)

    def test_mot_commencant_par_r_n_est_pas_un_refrain(self):
        blocs = paroles.decouper("Roi de gloire\nRègne à jamais")
        self.assertEqual(blocs[0].type, "couplet")
        self.assertEqual(blocs[0].texte, "Roi de gloire\nRègne à jamais")

    def test_retours_windows_espaces_et_lignes_vides_multiples(self):
        blocs = paroles.decouper("  A  \r\n B\r\n\r\n\r\n\r\n C ")
        self.assertEqual([b.texte for b in blocs], ["A\nB", "C"])

    def test_etiquette_sans_texte_ignoree(self):
        self.assertEqual(paroles.decouper("Refrain\n\n\n"), [])

    def test_aller_retour(self):
        blocs = paroles.decouper(SANS_ATTENDRE)
        self.assertEqual(paroles.decouper(paroles.vers_texte(blocs)), blocs)


class RechercheTests(TestCase):
    def test_normaliser(self):
        self.assertEqual(normaliser("Qui S’ÉLANCE  Noël"), "qui s elance noel")


def utilisateur(nom, role):
    u = Utilisateur.objects.create_user(nom, password="x")
    u.groups.add(Group.objects.get(name=role))
    return u


class VuesTests(TestCase):
    def setUp(self):
        self.editeur = utilisateur("editeur", roles.EDITEUR)
        self.lecteur = utilisateur("lecteur", roles.LECTEUR)
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre", tags="entrée, louange")
        self.chant.remplacer_paroles(SANS_ATTENDRE)

    def test_anonyme_redirige_vers_connexion(self):
        reponse = self.client.get(reverse("chants:liste"))
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse("comptes:connexion"), reponse.url)

    def test_lecteur_consulte_mais_ne_modifie_pas(self):
        self.client.force_login(self.lecteur)
        self.assertEqual(self.client.get(reverse("chants:liste")).status_code, 200)
        self.assertEqual(self.client.get(self.chant.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(reverse("chants:creation")).status_code, 403)
        url = reverse("chants:modification", args=[self.chant.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        url = reverse("chants:suppression", args=[self.chant.pk])
        self.assertEqual(self.client.post(url).status_code, 403)

    def test_recherche_sans_accents_dans_les_paroles(self):
        self.client.force_login(self.lecteur)
        reponse = self.client.get(reverse("chants:liste"), {"q": "s'elance PRIX"})
        self.assertContains(reponse, "Sans attendre je veux tendre")
        reponse = self.client.get(reverse("chants:liste"), {"q": "inexistant"})
        self.assertNotContains(reponse, "Sans attendre je veux tendre")

    def test_tri_alphabetique_sans_accents(self):
        Chant.objects.create(titre="À toi la gloire").remplacer_paroles("1. A")
        Chant.objects.create(titre="Zachée").remplacer_paroles("1. Z")
        self.client.force_login(self.lecteur)
        reponse = self.client.get(reverse("chants:liste"))
        titres = [c.titre for c in reponse.context["chant_list"]]
        self.assertEqual(titres, ["À toi la gloire", "Sans attendre je veux tendre", "Zachée"])

    def test_recherche_par_tag(self):
        self.client.force_login(self.lecteur)
        reponse = self.client.get(reverse("chants:liste"), {"q": "louange"})
        self.assertContains(reponse, "Sans attendre je veux tendre")

    def test_editeur_cree_un_chant(self):
        self.client.force_login(self.editeur)
        reponse = self.client.post(
            reverse("chants:creation"),
            {"titre": "À toi la gloire", "auteur": "", "langue": "Français", "tags": "",
             "paroles": "1. À toi la gloire\nÔ Ressuscité\n\nRefrain\nÀ toi la victoire"},
        )
        chant = Chant.objects.get(titre="À toi la gloire")
        self.assertRedirects(reponse, chant.get_absolute_url())
        self.assertEqual(chant.cree_par, self.editeur)
        self.assertEqual([c.libelle for c in chant.couplets.all()], ["Couplet 1", "Refrain"])
        self.assertIn("ressuscite", chant.recherche)

    def test_modification_remplace_les_paroles(self):
        self.client.force_login(self.editeur)
        url = reverse("chants:modification", args=[self.chant.pk])
        self.assertContains(self.client.get(url), "1. Sans attendre")
        self.client.post(url, {"titre": self.chant.titre, "auteur": "", "langue": "Français",
                               "tags": "", "paroles": "Nouveau texte"})
        self.assertEqual(list(self.chant.couplets.values_list("texte", flat=True)), ["Nouveau texte"])

    def test_doublon_refuse(self):
        self.client.force_login(self.editeur)
        reponse = self.client.post(
            reverse("chants:creation"),
            {"titre": "sans attendre je veux tendre", "auteur": "", "langue": "Français",
             "tags": "", "paroles": "Texte"},
        )
        self.assertContains(reponse, "existe déjà")
        self.assertEqual(Chant.objects.count(), 1)

    def test_paroles_vides_refusees(self):
        self.client.force_login(self.editeur)
        reponse = self.client.post(
            reverse("chants:creation"),
            {"titre": "Vide", "auteur": "", "langue": "Français", "tags": "", "paroles": "Refrain\n\n"},
        )
        self.assertContains(reponse, "aucun couplet")
        self.assertFalse(Chant.objects.filter(titre="Vide").exists())

    def test_suppression(self):
        self.client.force_login(self.editeur)
        reponse = self.client.post(reverse("chants:suppression", args=[self.chant.pk]))
        self.assertRedirects(reponse, reverse("chants:liste"))
        self.assertFalse(Chant.objects.exists())

    def test_roles_recoivent_les_permissions_des_chants(self):
        self.assertTrue(self.editeur.has_perm("chants.add_chant"))
        self.assertTrue(self.lecteur.has_perm("chants.view_chant"))
        self.assertFalse(self.lecteur.has_perm("chants.add_chant"))
