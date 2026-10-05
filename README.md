# Danzapa

Application web Django pour **stocker les chants**, **préparer le culte** et **projeter les paroles** le dimanche, sans refaire une présentation PowerPoint chaque semaine.

## Le problème

Chaque semaine, l'équipe prépare à la main une présentation PowerPoint pour le culte du dimanche. Un même chant revient pourtant environ 6 fois par an, et il faut le ressaisir ou le recopier à chaque fois.

Danzapa enregistre chaque chant **une seule fois** dans une bibliothèque. Pour préparer un culte, on choisit les chants déjà enregistrés (ou on en saisit un nouveau, qui est ajouté à la bibliothèque). L'application génère les diapositives, que l'on peut projeter dans le navigateur ou exporter en `.pptx`.

## Fonctionnalités prévues

- **Bibliothèque de chants** : chaque chant est saisi une fois, diapo par diapo, directement dans l'éditeur de culte, puis retrouvé par son titre, ses tags ou ses paroles dans tous les cultes.
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
| `DiapoChant` | chant, ordre, contenu mis en forme (HTML nettoyé), alignement, taille, couleur de fond |
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

Danzapa se déploie avec Docker Compose, par exemple avec **Dokploy** sur un VPS. Le fichier [`docker-compose.yml`](docker-compose.yml) lance l'application avec sa base **SQLite** dans un volume nommé : chants, cultes et comptes sont conservés à chaque redéploiement. Pour l'instant, l'accès se fait **sans connexion** (`DANZAPA_SANS_CONNEXION=true` dans `config/production.env`). Le guide pas à pas est dans [DEPLOIEMENT.md](DEPLOIEMENT.md) : sous-domaine, service Compose, HTTPS, mises à jour et sauvegardes.

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

## Saisir un chant (dans l'éditeur du culte)

Tout se passe sur la page du culte, comme dans PowerPoint :

1. **Accueil → Nouveau chant** : indiquez le titre et des tags (« adoration, louange »…) pour retrouver le chant plus tard, et le moment du culte. Optionnel : collez des paroles existantes, découpées automatiquement en diapos.
2. L'éditeur passe en **mode édition** : tapez les paroles directement sur la grande diapo. **Chaque frappe est enregistrée automatiquement** (« ✓ Enregistré » en haut à droite).
3. Mettez en forme avec le ruban :
   - **Police** : gras, italique, souligné, couleur du texte sélectionné, effacer la mise en forme ;
   - **Paragraphe** : A+ / A− (taille de la diapo), alignement gauche / centre / droite, couleur de fond de la diapo ou fond du thème.
4. **Nouvelle diapo** (ou Ctrl+Entrée) passe à la diapo suivante. **Dupliquer** copie la diapo, pratique pour un refrain qui revient. Les diapos se réordonnent par glisser-déposer ou avec Monter / Descendre.
5. **Fermer le chant** (ou Échap) quand tout est bon, puis passez au chant suivant.

Le chant est rangé dans la bibliothèque. Dans n'importe quel culte, **Insérer un chant** le retrouve par son titre, ses tags ou ses paroles, sans tenir compte des accents. Pour le corriger, double-cliquez sur une de ses diapos, ou sélectionnez-la puis cliquez sur **Modifier le chant**. La correction s'applique à tous les cultes qui l'utilisent. Un chant qui ne sert dans aucun culte peut être supprimé depuis la fenêtre **Insérer un chant** (🗑).

Les diapos sont projetées telles qu'elles ont été tapées : le refrain n'est plus répété automatiquement. Les chants saisis avec l'ancienne version (couplets et refrains) ont été convertis en diapos, par paquets de 4 lignes.

## Préparer un culte

Dans **Cultes**, choisissez la date et cliquez sur **Créer**. L'éditeur s'ouvre avec la disposition de PowerPoint :

- **Accueil** ou **Insertion** → **Insérer un chant** : cherchez dans la bibliothèque, indiquez le moment (« Cantique d'entrée » est proposé pour le premier chant) et cliquez sur le chant. Un chant absent de la bibliothèque se crée avec **Nouveau chant** (voir ci-dessus).
- **Nouvelle diapo** : texte libre (annonces, lecture…). Une ligne vide sépare deux diapos.
- Les vignettes à gauche sont regroupées par chant. Faites glisser l'en-tête d'un chant pour le déplacer entier, ou utilisez **Monter** / **Descendre**.
- Sous la diapo : moment, titre / tags / auteur du chant, **Modifier le chant**, **Masquer**, **Retirer du culte**.
- **Création** : texte de la diapo de bienvenue, thème, et nombre de lignes par diapo utilisé quand on colle des paroles (4 par défaut ; 6 lignes donnent 3 + 3).
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
