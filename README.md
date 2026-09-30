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
- `python-pptx` pour l'export PowerPoint
- SQLite en développement, PostgreSQL en production

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
3. **Préparation d'un culte** : éditeur façon PowerPoint, ajout de chants, réordonnancement.
4. **Export PowerPoint** : génération du `.pptx` selon le thème.
5. **Mode projection** : plein écran, clavier, vue présentateur.
6. **Module Bible** : import d'une version libre de droits, recherche, projection de versets.

## Installation

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

## Tests

```bash
python manage.py test
```
