# Danzapa

Application web Django pour **stocker les chants**, **préparer le culte** et **projeter les paroles** le dimanche, sans refaire une présentation PowerPoint chaque semaine.

## Le problème

Chaque semaine, l'équipe prépare à la main une présentation PowerPoint pour le culte du dimanche. Un même chant revient pourtant environ 6 fois par an, et il faut le ressaisir ou le recopier à chaque fois.

Danzapa enregistre chaque chant **une seule fois** dans une bibliothèque. Pour préparer un culte, on choisit les chants déjà enregistrés (ou on en saisit un nouveau, qui est ajouté à la bibliothèque). L'application génère les diapositives, que l'on peut projeter dans le navigateur ou exporter en `.pptx`.

## Fonctionnalités prévues

- **Bibliothèque de chants** : ajout, modification, recherche, découpage des paroles en couplets et refrains.
- **Préparation d'un culte** : diapo de bienvenue, puis ajout de chants de la bibliothèque, de texte libre ou d'annonces, rangés par moment (« Cantique d'entrée », « Adoration », « Offrande »…) et réordonnés par glisser-déposer.
- **Génération automatique des diapositives** : pour chaque chant, une diapo titre (moment + titre du chant), puis les paroles découpées en diapos de 4 lignes (réglable), avec le numéro du couplet en tête.
- **Export PowerPoint** (`.pptx`) avec `python-pptx`.
- **Mode projection** plein écran dans le navigateur, navigation au clavier, vue présentateur.
- **Thèmes** : fond, police, couleurs, image de fond. Le thème par défaut reprend le style actuel (texte blanc gras sur fond noir).
- **Comptes utilisateurs et rôles** : administrateur, éditeur, lecteur.
- **Plus tard : module Bible** pour rechercher et projeter des versets.

## Interface

L'éditeur de culte reprend la disposition de PowerPoint Web, familière à l'équipe :

| Zone | Contenu |
|------|---------|
| Barre de titre | Nom du culte, enregistrement automatique, recherche, Partager, utilisateur |
| Ruban | Onglets **Fichier**, **Accueil**, **Insertion**, **Création**, **Transitions**, **Diaporama**, **Affichage** |
| Panneau gauche | Vignettes numérotées, réordonnables par glisser-déposer (les diapos d'un chant restent groupées) |
| Zone centrale | Aperçu 16:9 de la diapo sélectionnée, texte modifiable sur place |
| Barre d'état | « Diapositive X sur N », notes, vues (normal, trieuse, lecture), zoom |

Onglets du ruban :

- **Fichier** : nouveau culte, ouvrir, dupliquer un culte passé, exporter en `.pptx`, imprimer les paroles.
- **Accueil** : annuler/rétablir, nouvelle diapo, disposition, masquer une diapo, mise en forme du texte.
- **Insertion** : chant de la bibliothèque, nouveau chant, texte libre, image, verset biblique (plus tard).
- **Création** : thèmes, modèle de diapo titre, nombre de lignes par diapo.
- **Transitions** : aucune ou fondu.
- **Diaporama** : projeter depuis le début ou depuis la diapo courante, vue présentateur.
- **Affichage** : normal, trieuse de diapositives, lecture.

## Modèle de données

| Modèle | Champs principaux |
|--------|-------------------|
| `Chant` | titre, auteur, langue, tags, date d'ajout |
| `Couplet` | chant, ordre, type (couplet, refrain, pont), texte |
| `Culte` | date, titre, thème, statut (brouillon, prêt), diapo de bienvenue, créé par |
| `ElementCulte` | culte, ordre, moment, type (chant, lecture, annonce, texte libre), chant, contenu libre |
| `Theme` | nom, fond (couleur ou image), police, taille, couleur du texte, lignes par diapo |

Les rôles s'appuient sur les groupes et permissions de Django.

## Stack technique

- Python 3.11+, Django 5.2
- Templates Django + HTMX, SortableJS pour le glisser-déposer
- `python-pptx` pour l'export PowerPoint, Pillow pour les images des thèmes
- SQLite (dans un volume Docker en production), PostgreSQL possible
- Gunicorn et WhiteNoise en production, image Docker (`Dockerfile`)

## Structure prévue

```
danzapa/
├── manage.py
├── requirements.txt
├── config/            # paramètres Django
└── apps/
    ├── chants/        # bibliothèque de chants
    ├── cultes/        # préparation des cultes et éditeur
    ├── projection/    # mode projection et export .pptx
    └── bible/         # module Bible (plus tard)
```

## Feuille de route

1. ✅ **Fondations** : projet Django, authentification, rôles, admin.
2. ✅ **Bibliothèque de chants** : CRUD, recherche, import de paroles collées avec découpage automatique.
3. ✅ **Préparation d'un culte** : éditeur façon PowerPoint, ajout de chants, réordonnancement.
4. ✅ **Export PowerPoint** : génération du `.pptx` selon le thème.
5. **Mode projection** : plein écran, clavier, vue présentateur.
6. **Module Bible** : import d'une version libre de droits, recherche, projection de versets.

## Mise en ligne

Danzapa se déploie avec Docker, par exemple avec **Dokploy** sur un VPS. Le guide pas à pas est dans [DEPLOIEMENT.md](DEPLOIEMENT.md) : sous-domaine, variables, volume de données, HTTPS, mises à jour et sauvegardes.

## Installation (développement)

```bash
git clone https://github.com/alowizdigital-create/danzapa.git
cd danzapa
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ouvrir ensuite http://127.0.0.1:8000 et se connecter avec le compte créé.

La configuration passe par des variables d'environnement, toutes optionnelles en développement : voir [`.env.example`](.env.example). En production, définir au minimum `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` et `DJANGO_ALLOWED_HOSTS`.

## Utilisateurs et rôles

Les trois rôles sont créés automatiquement par `migrate` sous forme de groupes Django :

| Rôle | Droits |
|------|--------|
| Administrateur | Gère les utilisateurs et tout le contenu, accède à `/admin/` |
| Éditeur | Crée, modifie et supprime chants, cultes et thèmes |
| Lecteur | Consulte les chants et les cultes, lance la projection |

Pour ajouter quelqu'un : `/admin/` → **Utilisateurs** → **Ajouter**, puis cocher son groupe. Pour qu'un administrateur accède à `/admin/`, cocher aussi « Statut équipe ».

## Saisir les paroles d'un chant

Dans **Chants** → **Nouveau chant**, collez les paroles dans un seul champ. Danzapa les découpe automatiquement :

```
1. Sans attendre
Je veux tendre
Au bonheur promis

Refrain
De mon Dieu je suis l'enfant
Et c'est lui qui me défend

2. Qui s'élance
Qui s'avance
```

- Une ligne vide sépare deux blocs.
- `1.`, `2)` ou `3 -` en tête de bloc donne le numéro du couplet. Sans numéro, les couplets sont numérotés à la suite.
- `Refrain`, `R:`, `Chorus`, `Pont` ou `Bridge` sur la première ligne marque le type du bloc.

La page du chant affiche chaque bloc en aperçu de diapositive. La recherche ignore les accents et regarde le titre, l'auteur, les tags et les paroles : « s'elance » trouve « Qui s'élance ». Un chant qui existe déjà (même titre et même auteur) ne peut pas être recréé.

## Préparer un culte

Dans **Cultes**, choisissez la date et cliquez sur **Créer**. L'éditeur s'ouvre avec la disposition de PowerPoint :

- **Accueil** ou **Insertion** → **Insérer un chant** : cherchez dans la bibliothèque, indiquez le moment (« Cantique d'entrée » est proposé pour le premier chant) et cliquez sur le chant. Un chant absent de la bibliothèque se saisit avec **Nouveau chant** : il est enregistré dans la bibliothèque et ajouté au culte.
- **Nouvelle diapo** : texte libre (annonces, lecture…). Une ligne vide sépare deux diapos.
- Les vignettes à gauche sont regroupées par chant. Faites glisser l'en-tête d'un chant pour le déplacer entier, ou utilisez **Monter** / **Descendre**.
- Sous la diapo : moment, **Répéter le refrain après chaque couplet**, **Corriger les paroles** (la correction s'applique à la bibliothèque, donc à tous les cultes), **Masquer**, **Retirer du culte**.
- **Création** : texte de la diapo de bienvenue et nombre de lignes par diapo (4 par défaut ; 6 lignes donnent 3 + 3).
- **Fichier** → **Dupliquer** : copie tout le culte sur une autre date, pratique d'un dimanche à l'autre.
- **Affichage** ou barre d'état : vue normale ou trieuse de diapositives. Les flèches du clavier passent d'une diapo à l'autre.

Chaque modification est enregistrée aussitôt (« ✓ Enregistré » en haut à droite). Un chant utilisé dans un culte ne peut pas être supprimé de la bibliothèque, et sa page indique les cultes où il a servi.

## Exporter en PowerPoint et choisir un thème

- **Fichier → Exporter en PowerPoint** télécharge « Culte du 20 septembre 2026.pptx », prêt à projeter. Le fichier contient exactement les diapos de l'éditeur :
  - les éléments masqués deviennent des diapos masquées de PowerPoint (présentes dans le fichier, mais sautées pendant la projection) ;
  - les notes du présentateur indiquent le chant et le couplet ;
  - une ligne trop longue est réduite automatiquement pour tenir sur la diapo, avec le même calcul dans l'aperçu et dans le fichier.
- **Création → Thème** : choisir l'apparence du culte. **Gérer les thèmes** (ou `/themes/`) pour créer un thème :
  - couleur ou image de fond ;
  - couleur du texte ;
  - polices et tailles des paroles et des titres ;
  - titres en majuscules ou non ;
  - couleur du bandeau de bienvenue, ou une image qui remplace toute la diapo de bienvenue.

  L'aperçu se met à jour pendant la saisie.
- Le thème **Classique** reproduit la présentation actuelle : paroles blanches en gras sur fond noir, titres en majuscules, bandeau gris pour la bienvenue. Il est utilisé par défaut et ne peut pas être supprimé.
- Les polices proposées existent sur Windows et Mac, pour que le fichier s'affiche comme prévu sur l'ordinateur de projection.

En production, les images des thèmes (dossier `media/`) doivent être servies par l'hébergeur ; en développement, Django s'en charge.

## Tests

```bash
python manage.py test
```
