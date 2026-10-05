# Déployer Danzapa avec Dokploy (VPS Hostinger)

Ce guide met Danzapa en ligne sur un VPS qui fait déjà tourner **Dokploy**, à l'adresse `https://danzapa.zweey.com`.

Le fichier [`docker-compose.yml`](docker-compose.yml) du dépôt décrit Danzapa : un service `web` (Django servi par Gunicorn, CSS/JS par WhiteNoise) et un volume nommé **`danzapa-data`**, monté sur `/data`. Ce volume contient :

- la base de données **SQLite** `/data/db.sqlite3` (chants, cultes, comptes) ;
- les images des thèmes ;
- la clé secrète ;
- les sauvegardes.

Dokploy crée le volume au premier déploiement et **le garde à chaque redéploiement**. Il n'y a rien à ajouter à la main. Au démarrage, `web` applique les migrations et crée le premier administrateur. Dokploy s'occupe du nom de domaine et du certificat HTTPS.

> Les libellés exacts de Dokploy peuvent varier légèrement selon la version.

---

## 1. Le sous-domaine (hPanel Hostinger)

1. Dans **hPanel → Domaines → votre domaine → DNS / Serveurs de noms**, ajoutez un enregistrement :
   - **Type** : `A`
   - **Nom** : `danzapa` (pour `danzapa.zweey.com`)
   - **Pointe vers** : l'adresse IP de votre VPS (hPanel → VPS → Aperçu)
   - **TTL** : par défaut
2. La propagation prend de quelques minutes à une heure. Pour vérifier : `ping danzapa.zweey.com` doit répondre avec l'IP du VPS.

## 2. Supprimer l'ancienne application (si elle existe)

Si vous aviez déjà créé Danzapa comme **Application** dans Dokploy, supprimez-la (page de l'application → **Delete**), ou au moins retirez-lui le domaine `danzapa.zweey.com` et arrêtez-la. Sinon, les deux se disputeraient le même domaine.

Rien n'est à récupérer dans l'ancienne application : faute de volume, sa base était recréée vide à chaque déploiement.

## 3. Créer le service Compose dans Dokploy

1. Dans le projet `Danzapa` (sinon **Projects → Create Project**), cliquez sur **Create Service → Compose**, nom : `danzapa`.
2. Onglet **General → Provider** :
   - **GitHub** (Dokploy est relié à votre compte) : dépôt `danzapa`, branche `main` ;
   - ou **Git** : Repository URL `https://github.com/alowizdigital-create/danzapa.git`, branche `main`.
3. **Compose Path** : `./docker-compose.yml`. Le type est **Docker Compose**, pas Stack.
4. **Save**.

## 4. Réglages

### Le fichier `config/production.env`

Les réglages courants sont dans le fichier **[`config/production.env`](config/production.env)** du dépôt :

```env
DJANGO_ALLOWED_HOSTS=danzapa.zweey.com
DJANGO_TIME_ZONE=Europe/Paris
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=
```

- **`DJANGO_ALLOWED_HOSTS`** : l'adresse du site, sans `https://`.
- **`DJANGO_TIME_ZONE`** : le fuseau de l'église (`Africa/Kinshasa`, `Africa/Abidjan`, `Europe/Paris`…).
- **`DJANGO_SUPERUSER_USERNAME`** : l'identifiant du premier administrateur.

Pour changer un réglage, modifiez le fichier sur GitHub (icône crayon), validez, puis cliquez sur **Deploy** dans Dokploy.

**Pas de secret dans ce fichier** : le dépôt est public.

- La **clé secrète** est générée au premier démarrage et conservée dans le volume `danzapa-data`.
- Le **mot de passe** du premier administrateur est généré et affiché une seule fois dans les logs (étape 6).

### Accès sans connexion (temporaire)

Pour l'instant, `config/production.env` contient `DANZAPA_SANS_CONNEXION=true`. Tout le monde arrive directement dans l'application, sans page de connexion, avec le compte administrateur.

**Attention** : toute personne qui connaît l'adresse du site peut alors modifier ou supprimer les chants et les cultes. Pour réactiver la connexion, mettez `DANZAPA_SANS_CONNEXION=false` dans ce fichier (ou supprimez la ligne), puis cliquez sur **Deploy**. Les données ne changent pas.

### L'onglet Environment (facultatif)

Les variables de l'onglet **Environment** du service Compose sont prioritaires sur le fichier. Les secrets vont ici, jamais dans le dépôt. Rien n'est obligatoire. Variables possibles : `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SECRET_KEY`, et celles de [`.env.example`](.env.example).

## 5. Domaine et HTTPS

Onglet **Domains → Add Domain** du service Compose :

- **Service Name** : `web`
- **Host** : `danzapa.zweey.com`
- **Path** : `/`
- **Container Port** : `8000`
- **HTTPS** : activé, **Certificate** : `Let's Encrypt`

Dokploy fait la redirection HTTP → HTTPS et transmet l'en-tête `X-Forwarded-Proto`, que Danzapa sait lire. Aucun port n'est ouvert sur le VPS, donc il n'y a pas de conflit avec vos autres sites.

## 6. Déployer et premier accès

1. Cliquez sur **Deploy** et suivez l'onglet **Deployments**. La construction prend 1 à 3 minutes. Dans l'onglet **Logs**, choisissez le service `web`. Vous devez voir :
   ```
   Administrateur « admin » créé.
   ============================================================
     Créé le 05/10/2026 09:00
     Identifiant : admin
     Mot de passe provisoire : k7mq-x3vp-9rtd-h2wa
   ============================================================
   Listening at: http://0.0.0.0:8000
   ```
   Notez ce mot de passe : il n'est affiché **qu'une seule fois**, au tout premier démarrage. Il servira quand la connexion sera réactivée. Les déploiements suivants ne le réaffichent pas, car le compte existe déjà dans la base.
2. Ouvrez `https://danzapa.zweey.com`. Avec l'accès sans connexion, l'application s'ouvre directement. Sinon, connectez-vous avec `admin` et le mot de passe provisoire, puis changez-le (**Mot de passe**, en haut à droite). Il est enregistré dans la base, dans le volume, et reste valable après chaque redéploiement.
3. Créez les comptes de l'équipe : **Administration** (en haut à droite) → **Utilisateurs → Ajouter**. Choisissez ensuite le **groupe** de chacun :
   - **Éditeur** : prépare les cultes et gère les chants ;
   - **Lecteur** : consulte, exporte et projette ;
   - **Administrateur** : gère aussi les comptes. Cochez en plus « Statut équipe » pour qu'il accède à l'administration.

## Mot de passe incorrect ou oublié

Pour choisir un nouveau mot de passe, deux méthodes :

- **Avec le terminal** : dans l'onglet **Terminal** de Dokploy, choisissez le conteneur `web`. En SSH, utilisez `docker exec -it $(docker ps -qf "name=danzapa.*-web-" | head -1) sh`. Puis :
  ```bash
  python manage.py changepassword admin
  ```
- **Sans terminal** : dans l'onglet **Environment**, ajoutez
  ```env
  DJANGO_SUPERUSER_PASSWORD=VotreNouveauMotDePasse
  DJANGO_SUPERUSER_RESET=1
  ```
  Puis cliquez sur **Deploy**. Les logs de `web` affichent « Mot de passe de « admin » remplacé ». Connectez-vous, puis **retirez ces deux lignes** et redéployez. Sinon, le mot de passe serait réimposé à chaque démarrage.

Pour vérifier que l'application répond, ouvrez `https://danzapa.zweey.com/sante/` : la page doit afficher `ok`. C'est aussi le healthcheck du conteneur.

## 7. Mettre à jour

À chaque nouvelle version poussée sur `main`, cliquez sur **Deploy** dans Dokploy. L'image `web` est reconstruite et les migrations s'appliquent toutes seules. Le volume `danzapa-data`, donc toutes les données, est conservé.

Pour automatiser le déploiement, activez **Autodeploy** (Dokploy relié à GitHub). Vous pouvez aussi copier l'URL du **webhook** de l'onglet Deployments dans GitHub (**Settings → Webhooks → Add webhook**, type `application/json`, évènement *push*).

> Ne lancez jamais `docker compose down -v` et ne supprimez pas le volume `danzapa-data` : c'est là que sont les données. Supprimer le service Compose dans Dokploy peut aussi supprimer ses volumes ; faites une sauvegarde avant.

## 8. Sauvegardes

Dans le conteneur `web`, la commande suivante crée `/data/sauvegardes/danzapa-AAAAMMJJ-HHMMSS.tar.gz`. L'archive contient `db.sqlite3` (copie cohérente de la base, même pendant l'utilisation) et les images des thèmes. Les 14 dernières sont gardées.

```bash
python manage.py sauvegarde
```

- **Planifier** : dans l'onglet **Schedules** de Dokploy (si votre version l'a), ajoutez une tâche quotidienne sur le service `web` avec la commande `python manage.py sauvegarde`. Sinon, ajoutez sur le VPS une ligne dans `crontab -e` :
  ```cron
  30 3 * * * docker exec $(docker ps -qf "name=danzapa.*-web-" | head -1) python manage.py sauvegarde >/dev/null 2>&1
  ```
- **Copier une sauvegarde hors du VPS** (recommandé) :
  ```bash
  docker cp $(docker ps -qf "name=danzapa.*-web-" | head -1):/data/sauvegardes ./sauvegardes-danzapa
  ```
- **Restaurer** une archive : extrayez-la (`tar xzf danzapa-….tar.gz`), recopiez la base et les images dans le conteneur, puis redémarrez-le :
  ```bash
  W=$(docker ps -qf "name=danzapa.*-web-" | head -1)
  docker cp db.sqlite3 $W:/data/db.sqlite3 && docker cp media/. $W:/data/media/ && docker restart $W
  ```

## 9. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| **Bad Request (400)** | Le domaine n'est pas dans `DJANGO_ALLOWED_HOSTS` | Corriger `config/production.env`, redéployer |
| **Erreur CSRF (403)** à la connexion | Le site est ouvert par une adresse différente de `DJANGO_ALLOWED_HOSTS`, ou sans HTTPS | Ouvrir `https://` + le sous-domaine ; si besoin, définir `DJANGO_CSRF_TRUSTED_ORIGINS=https://danzapa.zweey.com` |
| **Bad Gateway (502)** ou **404** de Traefik | Domaine rattaché au mauvais service ou au mauvais port | Domains : Service Name `web`, Container Port `8000` ; lire les logs de `web` |
| Bandeau rouge « données pas enregistrées durablement » | Déployé comme Application, sans le volume | Déployer en service Compose (étapes 2 et 3) |
| « Mot de passe incorrect » pour `admin` | Faute de frappe, ou ancien mot de passe provisoire | Section « Mot de passe incorrect ou oublié » |
| Le domaine affiche encore l'ancienne version | L'ancienne Application occupe toujours le domaine | Étape 2 |
| Pas de certificat HTTPS | Le DNS ne pointe pas encore vers le VPS | Attendre la propagation, puis régénérer le certificat |

## Passer à PostgreSQL plus tard

Danzapa sait déjà utiliser PostgreSQL : il suffit de lui donner une variable `DATABASE_URL=postgresql://utilisateur:motdepasse@hôte:5432/base`. Le plus simple sera d'ajouter un service `db` (image `postgres:16-alpine`, avec son propre volume) dans `docker-compose.yml`. Les données SQLite se transfèrent avec `python manage.py dumpdata` puis `loaddata`.

## Tester sur votre ordinateur

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

Ouvrez ensuite http://localhost:8000. Le mot de passe provisoire de `admin` s'affiche dans le terminal. Les cookies de connexion étant marqués « sécurisés », passez par `localhost` et non par une adresse IP. `docker compose … down` arrête tout en gardant les données. Ajoutez `-v` seulement pour tout effacer.
