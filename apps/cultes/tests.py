from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.chants import paroles
from apps.chants.models import Chant
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


def blocs(texte):
    return paroles.decouper(texte)


def types(liste):
    return [(b.type, b.numero) for b in liste]


class OrdreDeLectureTests(TestCase):
    def test_refrain_rejoue_apres_chaque_couplet(self):
        ordre = diapos.ordre_de_lecture(blocs(SANS_ATTENDRE))
        self.assertEqual(
            types(ordre),
            [("couplet", 1), ("refrain", None), ("couplet", 2), ("refrain", None)],
        )

    def test_option_desactivee_garde_l_ordre_saisi(self):
        ordre = diapos.ordre_de_lecture(blocs(SANS_ATTENDRE), repeter_refrain=False)
        self.assertEqual(types(ordre), [("couplet", 1), ("refrain", None), ("couplet", 2)])

    def test_refrain_en_tete(self):
        ordre = diapos.ordre_de_lecture(blocs("Refrain\nR\n\n1. A\n\n2. B"))
        self.assertEqual(
            types(ordre),
            [("refrain", None), ("couplet", 1), ("refrain", None), ("couplet", 2), ("refrain", None)],
        )

    def test_refrain_deja_ecrit_pas_double(self):
        texte = "1. A\n\nRefrain\nR\n\n2. B\n\nRefrain\nR"
        ordre = diapos.ordre_de_lecture(blocs(texte))
        self.assertEqual(len(ordre), 4)

    def test_dernier_refrain_rencontre(self):
        texte = "1. A\n\nRefrain\nPremier\n\n2. B\n\nRefrain\nSecond\n\n3. C"
        ordre = diapos.ordre_de_lecture(blocs(texte))
        self.assertEqual(ordre[-1].texte, "Second")

    def test_chant_sans_refrain(self):
        ordre = diapos.ordre_de_lecture(blocs("1. A\n\n2. B"))
        self.assertEqual(types(ordre), [("couplet", 1), ("couplet", 2)])


class DecoupageLignesTests(TestCase):
    def test_repartition_equilibree(self):
        paquets = diapos.decouper_lignes(list("abcdef"), 4)
        self.assertEqual([len(p) for p in paquets], [3, 3])

    def test_moins_que_le_maximum(self):
        self.assertEqual(diapos.decouper_lignes(["a", "b"], 4), [["a", "b"]])

    def test_neuf_lignes(self):
        self.assertEqual([len(p) for p in diapos.decouper_lignes(list("abcdefghi"), 4)], [3, 3, 3])

    def test_vide(self):
        self.assertEqual(diapos.decouper_lignes([], 4), [])


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
        self.assertEqual(
            [d.type for d in liste],
            ["bienvenue", "titre", "paroles", "paroles", "paroles", "paroles"],
        )
        self.assertEqual(liste[0].lignes, ["Bienvenus", "dans la", "maison du Seigneur"])
        self.assertEqual(liste[1].lignes, ["Cantique d'entrée : Sans attendre je veux tendre"])
        self.assertEqual(liste[2].lignes, ["1. Sans attendre", "Je veux tendre", "Au bonheur promis"])
        self.assertEqual(liste[3].lignes[0], "De mon Dieu je suis l'enfant")
        self.assertEqual(liste[4].lignes[0], "2. Qui s'élance")
        self.assertEqual([d.numero for d in liste], [1, 2, 3, 4, 5, 6])

    def test_lignes_par_diapo(self):
        self.culte.lignes_par_diapo = 2
        liste = diapos.diapos_du_culte(self.culte)
        couplet1 = [d for d in liste if d.libelle == "Couplet 1"]
        self.assertEqual([d.lignes for d in couplet1], [["1. Sans attendre", "Je veux tendre"], ["Au bonheur promis"]])

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

    def test_nouveau_chant_ajoute_a_la_bibliotheque_et_au_culte(self):
        reponse = self.client.post(
            self.url("nouveau_chant"),
            {"moment": "Offrande", "titre": "Nouveau", "auteur": "", "langue": "Français", "tags": "", "paroles": "1. Texte"},
        )
        self.assertRedirects(reponse, self.culte.get_absolute_url())
        chant = Chant.objects.get(titre="Nouveau")
        element = self.culte.elements.get()
        self.assertEqual((element.chant, element.moment), (chant, "Offrande"))

    def test_proprietes_de_l_element(self):
        element = self.ajouter(self.chant)
        self.hx_post(self.url("modifier_element", element.pk), {"moment": "Louange"})
        element.refresh_from_db()
        self.assertEqual(element.moment, "Louange")
        self.assertFalse(element.repeter_refrain)  # case décochée : non envoyée
        self.hx_post(self.url("modifier_element", element.pk), {"moment": "Louange", "repeter_refrain": "on"})
        element.refresh_from_db()
        self.assertTrue(element.repeter_refrain)

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


class LienAvecLaBibliothequeTests(TestCase):
    def setUp(self):
        self.editeur = utilisateur("editeur", roles.EDITEUR)
        self.client.force_login(self.editeur)
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre")
        self.chant.remplacer_paroles(SANS_ATTENDRE)
        self.culte = Culte.objects.create(date=date(2026, 9, 20))
        ElementCulte.objects.create(culte=self.culte, ordre=1, type=ElementCulte.CHANT, chant=self.chant)

    def test_chant_utilise_non_supprimable(self):
        reponse = self.client.post(reverse("chants:suppression", args=[self.chant.pk]), follow=True)
        self.assertContains(reponse, "utilisé dans 1 culte")
        self.assertTrue(Chant.objects.filter(pk=self.chant.pk).exists())

    def test_page_du_chant_liste_les_cultes(self):
        reponse = self.client.get(self.chant.get_absolute_url())
        self.assertContains(reponse, "Utilisé dans 1 culte")
        self.assertContains(reponse, "Culte du 20 septembre 2026")

    def test_correction_des_paroles_revient_au_culte(self):
        url = reverse("chants:modification", args=[self.chant.pk]) + f"?next={self.culte.get_absolute_url()}"
        donnees = {"titre": self.chant.titre, "auteur": "", "langue": "Français", "tags": "", "paroles": "1. Corrigé"}
        reponse = self.client.post(url, donnees)
        self.assertRedirects(reponse, self.culte.get_absolute_url())
        self.assertEqual(diapos.diapos_du_culte(self.culte)[2].lignes, ["1. Corrigé"])

    def test_next_externe_ignore(self):
        url = reverse("chants:modification", args=[self.chant.pk]) + "?next=https://exemple.com/"
        donnees = {"titre": self.chant.titre, "auteur": "", "langue": "Français", "tags": "", "paroles": "1. X"}
        reponse = self.client.post(url, donnees)
        self.assertRedirects(reponse, self.chant.get_absolute_url())
