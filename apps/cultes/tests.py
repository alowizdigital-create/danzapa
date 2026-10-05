from datetime import date

from django.contrib.auth.models import Group
import json

from django.test import TestCase
from django.urls import reverse

from apps.chants.models import Chant, DiapoChant
from apps.comptes import roles
from apps.comptes.models import Utilisateur

from . import diapos
from .models import MOMENT_PAR_DEFAUT, Culte, ElementCulte

SANS_ATTENDRE = """1. Sans attendre
Je veux tendre
Au bonheur promis

Refrain
De mon Dieu je suis l'enfant
Et c'est lui qui me défend

2. Qui s'élance
Qui s'avance
Obtiendra le prix
"""


class DiaposDuCulteTests(TestCase):
    def setUp(self):
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre")
        self.chant.remplacer_paroles(SANS_ATTENDRE)
        self.culte = Culte.objects.create(date=date(2026, 9, 20))
        self.element = ElementCulte.objects.create(
            culte=self.culte, ordre=1, type=ElementCulte.CHANT, chant=self.chant, moment=MOMENT_PAR_DEFAUT
        )

    def test_titre_par_defaut(self):
        self.assertEqual(self.culte.titre, "Culte du 20 septembre 2026")

    def test_structure_de_la_presentation(self):
        liste = diapos.diapos_du_culte(self.culte)
        self.assertEqual([d.type for d in liste], ["bienvenue", "titre", "paroles", "paroles", "paroles"])
        self.assertEqual(liste[0].lignes, ["Bienvenus", "dans la", "maison du Seigneur"])
        self.assertEqual(liste[1].lignes, ["Cantique d'entrée : Sans attendre je veux tendre"])
        self.assertEqual(liste[2].lignes, ["1. Sans attendre", "Je veux tendre", "Au bonheur promis"])
        self.assertEqual(liste[2].html, "<div>1. Sans attendre</div><div>Je veux tendre</div><div>Au bonheur promis</div>")
        # Le refrain n'est plus répété automatiquement : les diapos sont jouées telles que saisies.
        self.assertEqual(liste[3].lignes[0], "De mon Dieu je suis l'enfant")
        self.assertEqual(liste[4].lignes[0], "2. Qui s'élance")
        self.assertEqual([d.numero for d in liste], [1, 2, 3, 4, 5])
        self.assertEqual({d.chant_id for d in liste[1:]}, {self.chant.pk})

    def test_reglages_de_la_diapo(self):
        piece = self.chant.diapos.first()
        piece.alignement, piece.echelle, piece.couleur_fond = "gauche", 150, "#123456"
        piece.save()
        diapo = diapos.diapos_du_culte(self.culte)[2]
        self.assertEqual((diapo.alignement, diapo.echelle, diapo.couleur_fond, diapo.piece_id), ("gauche", 150, "#123456", piece.pk))

    def test_paroles_collees_par_paquets(self):
        self.chant.remplacer_paroles(SANS_ATTENDRE, lignes_par_diapo=2)
        liste = diapos.diapos_du_culte(self.culte)
        self.assertEqual([d.lignes for d in liste[2:4]], [["1. Sans attendre", "Je veux tendre"], ["Au bonheur promis"]])

    def test_sans_bienvenue(self):
        self.culte.texte_bienvenue = "  "
        self.assertEqual(diapos.diapos_du_culte(self.culte)[0].type, "titre")

    def test_texte_libre(self):
        ElementCulte.objects.create(
            culte=self.culte, ordre=2, type=ElementCulte.TEXTE, moment="Annonces", contenu="Réunion mardi\n\nJeûne vendredi"
        )
        liste = diapos.diapos_du_culte(self.culte)[-3:]
        self.assertEqual([d.lignes for d in liste], [["Annonces"], ["Réunion mardi"], ["Jeûne vendredi"]])

    def test_masquees_exclues_sur_demande(self):
        self.element.masque = True
        self.element.save()
        self.assertEqual(len(diapos.diapos_du_culte(self.culte, inclure_masquees=False)), 1)
        self.assertTrue(all(d.masque for d in diapos.diapos_du_culte(self.culte)[1:]))

    def test_nombre_de_requetes_constant(self):
        for i in range(5):
            ElementCulte.objects.create(culte=self.culte, ordre=i + 2, type=ElementCulte.CHANT, chant=self.chant)
        with self.assertNumQueries(2):
            diapos.diapos_du_culte(self.culte)


def utilisateur(nom, role):
    u = Utilisateur.objects.create_user(nom, password="x")
    u.groups.add(Group.objects.get(name=role))
    return u


class VuesTests(TestCase):
    def setUp(self):
        self.editeur = utilisateur("editeur", roles.EDITEUR)
        self.lecteur = utilisateur("lecteur", roles.LECTEUR)
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre")
        self.chant.remplacer_paroles(SANS_ATTENDRE)
        self.autre = Chant.objects.create(titre="À toi la gloire")
        self.autre.remplacer_paroles("1. À toi la gloire")
        self.culte = Culte.objects.create(date=date(2026, 9, 20))
        self.client.force_login(self.editeur)

    def url(self, nom, *args):
        return reverse(f"cultes:{nom}", args=[self.culte.pk, *args])

    def hx_post(self, url, donnees=None):
        return self.client.post(url, donnees or {}, headers={"HX-Request": "true"})

    def ajouter(self, chant, moment=""):
        self.hx_post(self.url("ajouter_chant"), {"chant": chant.pk, "moment": moment})
        return self.culte.elements.last()

    def test_creation_d_un_culte(self):
        reponse = self.client.post(reverse("cultes:creation"), {"date": "2026-09-27", "titre": ""})
        culte = Culte.objects.get(date=date(2026, 9, 27))
        self.assertRedirects(reponse, culte.get_absolute_url())
        self.assertEqual(culte.titre, "Culte du 27 septembre 2026")
        self.assertEqual(culte.cree_par, self.editeur)

    def test_editeur_affiche_les_diapos_et_suggere_le_cantique_d_entree(self):
        reponse = self.client.get(self.culte.get_absolute_url())
        self.assertContains(reponse, "maison du Seigneur")
        self.assertContains(reponse, 'id="moment-chant" name="moment" value="Cantique d&#x27;entrée"')

    def test_ajout_d_un_chant(self):
        reponse = self.hx_post(self.url("ajouter_chant"), {"chant": self.chant.pk, "moment": MOMENT_PAR_DEFAUT})
        self.assertEqual(reponse.status_code, 200)
        self.assertTemplateUsed(reponse, "cultes/_espace.html")
        self.assertContains(reponse, "Cantique d&#x27;entrée : Sans attendre je veux tendre")
        element = self.culte.elements.get()
        self.assertEqual((element.chant, element.moment, element.ordre), (self.chant, MOMENT_PAR_DEFAUT, 1))

    def test_ajout_sans_htmx_redirige(self):
        reponse = self.client.post(self.url("ajouter_chant"), {"chant": self.chant.pk})
        self.assertRedirects(reponse, self.culte.get_absolute_url())

    def test_recherche_de_chants(self):
        reponse = self.client.get(self.url("chercher_chants"), {"q": "gloire"})
        self.assertContains(reponse, "À toi la gloire")
        self.assertNotContains(reponse, "Sans attendre")

    def test_recherche_titres_d_abord(self):
        self.chant.remplacer_paroles(SANS_ATTENDRE + "\n\n3. Pour la gloire")
        reponse = self.client.get(self.url("chercher_chants"), {"q": "gloire"})
        self.assertEqual([c.titre for c in reponse.context["chants"]], ["À toi la gloire", "Sans attendre je veux tendre"])

    def test_ajout_d_un_texte_libre(self):
        self.hx_post(self.url("ajouter_texte"), {"moment": "Annonces", "titre": "", "contenu": "Réunion mardi"})
        element = self.culte.elements.get()
        self.assertEqual((element.type, element.contenu), (ElementCulte.TEXTE, "Réunion mardi"))

    def test_nouveau_chant_cree_et_ouvert_en_edition(self):
        reponse = self.hx_post(self.url("creer_chant"), {"titre": "Nouveau", "tags": "louange", "moment": "Offrande", "paroles": ""})
        self.assertEqual(reponse.status_code, 200)
        chant = Chant.objects.get(titre="Nouveau")
        element = self.culte.elements.get()
        piece = chant.diapos.get()
        self.assertEqual((element.chant, element.moment, piece.contenu), (chant, "Offrande", ""))
        self.assertContains(reponse, f'data-edition="{chant.pk}"')
        self.assertContains(reponse, f'data-piece="{piece.pk}"')
        self.assertEqual(chant.cree_par, self.editeur)

    def test_nouveau_chant_avec_paroles_collees(self):
        self.hx_post(self.url("creer_chant"), {"titre": "Collé", "paroles": SANS_ATTENDRE})
        self.assertEqual(Chant.objects.get(titre="Collé").diapos.count(), 3)

    def test_nouveau_chant_doublon_refuse(self):
        reponse = self.hx_post(self.url("creer_chant"), {"titre": "sans attendre je veux tendre"})
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("existe déjà", reponse.content.decode())

    def test_proprietes_de_l_element(self):
        element = self.ajouter(self.chant)
        self.hx_post(self.url("modifier_element", element.pk), {"moment": "Louange"})
        element.refresh_from_db()
        self.assertEqual(element.moment, "Louange")

    def test_masquer_puis_afficher(self):
        element = self.ajouter(self.chant)
        self.hx_post(self.url("basculer_masque", element.pk))
        element.refresh_from_db()
        self.assertTrue(element.masque)
        self.hx_post(self.url("basculer_masque", element.pk))
        element.refresh_from_db()
        self.assertFalse(element.masque)

    def test_reordonner_et_deplacer(self):
        a = self.ajouter(self.chant)
        b = self.ajouter(self.autre)
        self.hx_post(self.url("reordonner"), {"ordre": [b.pk, a.pk]})
        self.assertEqual(list(self.culte.elements.values_list("pk", flat=True)), [b.pk, a.pk])
        self.hx_post(self.url("deplacer_element", a.pk), {"sens": "haut"})
        self.assertEqual(list(self.culte.elements.values_list("pk", flat=True)), [a.pk, b.pk])
        self.hx_post(self.url("deplacer_element", a.pk), {"sens": "haut"})  # déjà en tête
        self.assertEqual(list(self.culte.elements.values_list("pk", flat=True)), [a.pk, b.pk])

    def test_reordonner_ignore_les_elements_d_un_autre_culte(self):
        a = self.ajouter(self.chant)
        autre_culte = Culte.objects.create(date=date(2026, 10, 4))
        intrus = ElementCulte.objects.create(culte=autre_culte, ordre=7, type=ElementCulte.TEXTE)
        self.hx_post(self.url("reordonner"), {"ordre": [intrus.pk, a.pk]})
        intrus.refresh_from_db()
        self.assertEqual(intrus.ordre, 7)

    def test_element_d_un_autre_culte_introuvable(self):
        autre_culte = Culte.objects.create(date=date(2026, 10, 4))
        intrus = ElementCulte.objects.create(culte=autre_culte, ordre=1, type=ElementCulte.TEXTE)
        reponse = self.hx_post(self.url("supprimer_element", intrus.pk))
        self.assertEqual(reponse.status_code, 404)

    def test_retirer_un_chant_du_culte(self):
        a = self.ajouter(self.chant)
        b = self.ajouter(self.autre)
        self.hx_post(self.url("supprimer_element", a.pk))
        self.assertEqual(list(self.culte.elements.values_list("pk", "ordre")), [(b.pk, 1)])
        self.assertTrue(Chant.objects.filter(pk=self.chant.pk).exists())

    def test_parametres_partiels(self):
        self.hx_post(self.url("parametres"), {"titre": "Culte de Pâques"})
        self.culte.refresh_from_db()
        self.assertEqual(self.culte.titre, "Culte de Pâques")
        self.assertEqual(self.culte.texte_bienvenue, "Bienvenus\ndans la\nmaison du Seigneur")
        self.hx_post(self.url("parametres"), {"lignes_par_diapo": "3"})
        self.culte.refresh_from_db()
        self.assertEqual((self.culte.titre, self.culte.lignes_par_diapo), ("Culte de Pâques", 3))

    def test_parametres_invalides(self):
        reponse = self.hx_post(self.url("parametres"), {"lignes_par_diapo": "0"})
        self.assertEqual(reponse.status_code, 400)

    def test_duplication(self):
        self.ajouter(self.chant, MOMENT_PAR_DEFAUT)
        reponse = self.client.post(self.url("dupliquer"), {"date": "2026-09-27"})
        copie = Culte.objects.get(date=date(2026, 9, 27))
        self.assertRedirects(reponse, copie.get_absolute_url())
        self.assertEqual(copie.titre, "Culte du 27 septembre 2026")
        self.assertEqual(list(copie.elements.values_list("chant", "moment")), [(self.chant.pk, MOMENT_PAR_DEFAUT)])

    def test_lecteur_en_lecture_seule(self):
        element = self.ajouter(self.chant)
        self.client.force_login(self.lecteur)
        reponse = self.client.get(self.culte.get_absolute_url())
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, 'data-panneau="insertion"')
        for url in (self.url("ajouter_chant"), self.url("parametres"), self.url("supprimer_element", element.pk)):
            self.assertEqual(self.hx_post(url, {"chant": self.chant.pk}).status_code, 403)
        self.assertEqual(self.client.post(reverse("cultes:creation"), {"date": "2026-09-27"}).status_code, 403)

    def test_get_refuse_sur_les_actions(self):
        self.assertEqual(self.client.get(self.url("ajouter_chant")).status_code, 405)


class SaisieDesChantsTests(TestCase):
    """Saisie et mise en forme des chants directement dans l'éditeur."""

    def setUp(self):
        self.editeur = utilisateur("editeur", roles.EDITEUR)
        self.lecteur = utilisateur("lecteur", roles.LECTEUR)
        self.client.force_login(self.editeur)
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre")
        self.chant.remplacer_paroles(SANS_ATTENDRE)
        self.culte = Culte.objects.create(date=date(2026, 9, 20))
        self.element = ElementCulte.objects.create(culte=self.culte, ordre=1, type=ElementCulte.CHANT, chant=self.chant)
        self.pieces = list(self.chant.diapos.all())

    def url(self, nom, *args):
        return reverse(f"cultes:{nom}", args=[self.culte.pk, self.chant.pk, *args])

    def hx_post(self, url, donnees=None):
        return self.client.post(url, donnees or {}, headers={"HX-Request": "true"})

    def ordre(self):
        return list(self.chant.diapos.values_list("pk", flat=True))

    def test_sauvegarde_automatique_d_une_diapo(self):
        piece = self.pieces[0]
        reponse = self.client.post(
            self.url("enregistrer_diapo", piece.pk),
            {"contenu": '1. Sans <b>attendre</b><div><font color="#ffd700">Je veux</font> tendre</div><script>x</script>',
             "alignement": "gauche", "echelle": "120", "couleur_fond": "#001122"},
        )
        donnees = json.loads(reponse.content)
        self.assertEqual(
            donnees["contenu"],
            '<div>1. Sans <b>attendre</b></div><div><span style="color: #ffd700">Je veux</span> tendre</div>',
        )
        self.assertTrue(donnees["taille"].endswith("cqw"))
        piece.refresh_from_db()
        self.assertEqual((piece.texte, piece.alignement, piece.echelle, piece.couleur_fond),
                         ("1. Sans attendre\nJe veux tendre", "gauche", 120, "#001122"))
        self.chant.refresh_from_db()
        self.assertIn("je veux tendre", self.chant.recherche)

    def test_reglages_invalides_refuses(self):
        reponse = self.client.post(self.url("enregistrer_diapo", self.pieces[0].pk), {"couleur_fond": "red;x"})
        self.assertEqual(reponse.status_code, 400)

    def test_ajouter_apres_et_dupliquer(self):
        premiere = self.pieces[0]
        reponse = self.hx_post(self.url("ajouter_diapo"), {"apres": premiere.pk})
        ids = self.ordre()
        self.assertEqual(len(ids), 4)
        nouvelle = DiapoChant.objects.get(pk=ids[1])
        self.assertEqual(nouvelle.contenu, "")
        self.assertContains(reponse, f'data-piece="{nouvelle.pk}"')
        self.hx_post(self.url("ajouter_diapo"), {"dupliquer": premiere.pk})
        ids = self.ordre()
        self.assertEqual(DiapoChant.objects.get(pk=ids[1]).texte, premiere.texte)

    def test_ajouter_en_fin_sans_reference(self):
        self.hx_post(self.url("ajouter_diapo"))
        self.assertEqual(DiapoChant.objects.get(pk=self.ordre()[-1]).contenu, "")

    def test_supprimer_deplacer_reordonner(self):
        a, b, c = (p.pk for p in self.pieces)
        self.hx_post(self.url("deplacer_diapo", c), {"sens": "haut"})
        self.assertEqual(self.ordre(), [a, c, b])
        self.hx_post(self.url("reordonner_diapos"), {"ordre": [b, a, c]})
        self.assertEqual(self.ordre(), [b, a, c])
        self.hx_post(self.url("supprimer_diapo", a))
        self.assertEqual(self.ordre(), [b, c])
        self.assertEqual(list(self.chant.diapos.values_list("ordre", flat=True)), [1, 2])

    def test_infos_du_chant(self):
        self.hx_post(self.url("infos_chant"), {"titre": "Sans attendre", "tags": "entrée, louange", "auteur": ""})
        self.chant.refresh_from_db()
        self.assertEqual((self.chant.titre, self.chant.tags), ("Sans attendre", "entrée, louange"))
        self.assertIn("louange", self.chant.recherche)

    def test_chant_hors_du_culte_introuvable(self):
        autre = Chant.objects.create(titre="Autre")
        piece = DiapoChant.objects.create(chant=autre, ordre=1)
        url = reverse("cultes:enregistrer_diapo", args=[self.culte.pk, autre.pk, piece.pk])
        self.assertEqual(self.client.post(url, {"contenu": "x"}).status_code, 404)

    def test_lecteur_ne_peut_pas_modifier(self):
        self.client.force_login(self.lecteur)
        piece = self.pieces[0]
        self.assertEqual(self.client.post(self.url("enregistrer_diapo", piece.pk), {"contenu": "x"}).status_code, 403)
        self.assertEqual(self.hx_post(self.url("ajouter_diapo")).status_code, 403)
        self.assertEqual(self.hx_post(reverse("cultes:creer_chant", args=[self.culte.pk]), {"titre": "X"}).status_code, 403)
        reponse = self.client.get(self.culte.get_absolute_url())
        self.assertNotContains(reponse, 'data-format="bold"')

    def test_modification_visible_dans_les_autres_cultes(self):
        autre = Culte.objects.create(date=date(2026, 9, 27))
        ElementCulte.objects.create(culte=autre, ordre=1, type=ElementCulte.CHANT, chant=self.chant)
        self.client.post(self.url("enregistrer_diapo", self.pieces[0].pk), {"contenu": "1. Corrigé"})
        self.assertEqual(diapos.diapos_du_culte(autre)[2].lignes, ["1. Corrigé"])

    def test_suppression_de_la_bibliotheque(self):
        url_utilise = self.url("supprimer_chant")
        reponse = self.hx_post(url_utilise)
        self.assertContains(reponse, "utilisé dans 1 culte")
        self.assertTrue(Chant.objects.filter(pk=self.chant.pk).exists())
        libre = Chant.objects.create(titre="Libre")
        reponse = self.hx_post(reverse("cultes:supprimer_chant", args=[self.culte.pk, libre.pk]))
        self.assertContains(reponse, "a été supprimé")
        self.assertFalse(Chant.objects.filter(pk=libre.pk).exists())

    def test_editeur_affiche_le_ruban_de_mise_en_forme(self):
        reponse = self.client.get(self.culte.get_absolute_url())
        for attendu in ('data-format="bold"', 'data-couleur-texte', 'data-diapo-action="ajouter"', 'id="dlg-nouveau-chant"'):
            self.assertContains(reponse, attendu)
        self.assertContains(reponse, f'data-piece="{self.pieces[0].pk}"')
