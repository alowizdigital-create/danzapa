from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from . import mise_en_forme, paroles
from .models import Chant, DiapoChant
from .recherche import filtrer, normaliser

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


class DecoupageLignesTests(TestCase):
    def test_repartition_equilibree(self):
        self.assertEqual([len(p) for p in paroles.decouper_lignes(list("abcdef"), 4)], [3, 3])

    def test_moins_que_le_maximum(self):
        self.assertEqual(paroles.decouper_lignes(["a", "b"], 4), [["a", "b"]])

    def test_vide(self):
        self.assertEqual(paroles.decouper_lignes([], 4), [])

    def test_paroles_collees_en_diapos_sans_repeter_le_refrain(self):
        self.assertEqual(
            paroles.en_diapos(SANS_ATTENDRE),
            [
                "1. Sans attendre\nJe veux tendre\nAu bonheur promis",
                "Donc en route\nPoint de doute\nLe but est si grand",
                "2. Qui s’élance\nQui s’avance\nObtiendra le prix",
            ],
        )


class MiseEnFormeTests(TestCase):
    def test_mise_en_forme_conservee(self):
        html = 'Sans attendre<div>Je <b>veux</b> <i><u>tendre</u></i></div><div><font color="#FF0000">Au bonheur</font></div>'
        self.assertEqual(
            mise_en_forme.nettoyer(html),
            "<div>Sans attendre</div><div>Je <b>veux</b> <i><u>tendre</u></i></div>"
            '<div><span style="color: #ff0000">Au bonheur</span></div>',
        )

    def test_styles_css_du_navigateur(self):
        html = '<span style="font-weight: 700; color: rgb(255, 204, 0); position: fixed">Jaune</span>'
        self.assertEqual(mise_en_forme.nettoyer(html), '<div><b><span style="color: #ffcc00">Jaune</span></b></div>')

    def test_code_dangereux_retire(self):
        html = (
            '<script>alert(1)</script><img src=x onerror=alert(1)><a href="javascript:x">lien</a>'
            '<div onclick="x" style="background:url(x)">texte</div><span style="color: red; expression(x)">!</span>'
        )
        propre = mise_en_forme.nettoyer(html)
        for interdit in ("script", "alert", "img", "onerror", "href", "onclick", "background", "expression", "red"):
            self.assertNotIn(interdit, propre)
        self.assertEqual(mise_en_forme.texte_brut(html), "lien\ntexte\n!")

    def test_pas_gras_explicite_conserve(self):
        # Le thème met les paroles en gras : « G » sur un mot produit font-weight: normal.
        html = '1. Sans <span style="font-weight: normal;">attendre</span>'
        propre = mise_en_forme.nettoyer(html)
        self.assertEqual(propre, '<div>1. Sans <span style="font-weight: normal">attendre</span></div>')
        morceaux = mise_en_forme.lignes(propre)[0]
        self.assertEqual([(m.texte, m.style.gras) for m in morceaux], [("1. Sans ", None), ("attendre", False)])
        self.assertEqual(mise_en_forme.nettoyer(propre), propre)

    def test_texte_echappe(self):
        self.assertEqual(mise_en_forme.nettoyer("&lt;b&gt;x&lt;/b&gt;"), "<div>&lt;b&gt;x&lt;/b&gt;</div>")

    def test_lignes_vides_internes_gardees_bords_retires(self):
        html = "<div><br></div><div>a</div><div><br></div><div>b</div><div><br></div>"
        self.assertEqual(mise_en_forme.texte_brut(html), "a\n\nb")

    def test_couleurs(self):
        self.assertEqual(mise_en_forme.couleur_valide("#ABC"), "#aabbcc")
        self.assertEqual(mise_en_forme.couleur_valide("rgb(1, 2, 300)"), "#0102ff")
        self.assertIsNone(mise_en_forme.couleur_valide("red; x"))


class DiapoChantTests(TestCase):
    def setUp(self):
        self.chant = Chant.objects.create(titre="Sans attendre je veux tendre", tags="entrée")

    def test_enregistrement_nettoie_et_extrait_le_texte(self):
        diapo = DiapoChant.objects.create(chant=self.chant, ordre=1, contenu="1. Sans <b>attendre</b><script>x</script>")
        self.assertEqual(diapo.contenu, "<div>1. Sans <b>attendre</b></div>")
        self.assertEqual(diapo.texte, "1. Sans attendre")

    def test_echelle_bornee(self):
        diapo = DiapoChant.objects.create(chant=self.chant, ordre=1, echelle=500)
        self.assertEqual(diapo.echelle, 200)

    def test_paroles_collees_et_recherche_dans_les_diapos(self):
        self.chant.remplacer_paroles(SANS_ATTENDRE)
        self.assertEqual(self.chant.diapos.count(), 3)
        self.assertEqual(self.chant.premiere_ligne, "1. Sans attendre")
        self.assertIn(self.chant, filtrer(Chant.objects.all(), "s'elance PRIX"))
        self.assertIn(self.chant, filtrer(Chant.objects.all(), "entree"))


class MigrationCoupletsTests(TransactionTestCase):
    """Les chants saisis avant le passage aux diapos sont convertis sans perte."""

    avant = [("chants", "0003_alter_chant_options")]
    apres = [("chants", "0006_delete_couplet")]

    def tearDown(self):
        executeur = MigrationExecutor(connection)
        executeur.loader.build_graph()
        executeur.migrate(executeur.loader.graph.leaf_nodes())

    def test_couplets_convertis_en_diapos(self):
        executeur = MigrationExecutor(connection)
        executeur.migrate(self.avant)
        anciennes = executeur.loader.project_state(self.avant).apps
        Chant_ = anciennes.get_model("chants", "Chant")
        Couplet = anciennes.get_model("chants", "Couplet")
        chant = Chant_.objects.create(titre="Ancien chant")
        Couplet.objects.create(chant=chant, ordre=1, type="couplet", numero=1, texte="a\nb\nc\nd\ne\nf")
        Couplet.objects.create(chant=chant, ordre=2, type="refrain", texte="Refrain <b>")

        executeur = MigrationExecutor(connection)
        executeur.loader.build_graph()
        executeur.migrate(self.apres)
        nouvelles = executeur.loader.project_state(self.apres).apps
        Diapo = nouvelles.get_model("chants", "DiapoChant")
        diapos = list(Diapo.objects.filter(chant_id=chant.pk).order_by("ordre"))
        self.assertEqual([d.texte for d in diapos], ["1. a\nb\nc", "d\ne\nf", "Refrain <b>"])
        self.assertEqual(diapos[2].contenu, "<div>Refrain &lt;b&gt;</div>")
