# Déployer Danzapa avec Dokploy (VPS Hostinger)

Ce guide met Danzapa en ligne sur un VPS qui fait déjà tourner **Dokploy**, à l'adresse `https://danzapa.zweey.com`.

L'application tourne dans un seul conteneur Docker, décrit par le `Dockerfile` du dépôt :

- Django est servi par Gunicorn, et les fichiers CSS/JS par WhiteNoise ;
- un volume monté sur **`/data`** contient la base de données SQLite et les images des thèmes ;
- au démarrage, le conteneur applique les migrations et crée le premier administrateur ;
- Dokploy s'occupe du nom de domaine et du certificat HTTPS.

> Les libellés exacts de Dokploy peuvent varier légèrement selon la version.

---

## 1. Le sous-domaine (hPanel Hostinger)

1. Dans **hPanel → Domaines → votre domaine → DNS / Serveurs de noms**, ajoutez un enregistrement :
   - **Type** : `A`
   - **Nom** : `danzapa` (pour `danzapa.zweey.com`)
   - **Pointe vers** : l'adresse IP de votre VPS (hPanel → VPS → Aperçu)
   - **TTL** : par défaut
2. La propagation prend de quelques minutes à une heure. Pour vérifier : `ping danzapa.zweey.com` doit répondre avec l'IP du VPS.

## 2. Créer l'application dans Dokploy

1. **Projects → Create Project**, nom : `Danzapa`.
2. Dans le projet : **Create Service → Application**, nom : `danzapa`.
3. Onglet **General → Provider** :
   - **Git** (dépôt public, aucun accès GitHub à donner) :
     - Repository URL : `https://github.com/alowizdigital-create/danzapa.git`
     - Branch : `main`
   - ou **GitHub**, si Dokploy est déjà relié à votre compte GitHub : même dépôt, même branche.
4. **Build Type** : `Dockerfile`. Docker File : `Dockerfile`. Contexte : `.` (la racine).

## 3. Réglages : le fichier `config/production.env`

Les réglages sont dans le fichier **[`config/production.env`](config/production.env)** du dépôt. Rien à coller dans Dokploy :

```env
DJANGO_ALLOWED_HOSTS=danzapa.zweey.com
DJANGO_TIME_ZONE=Europe/Paris
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=
```

- **`DJANGO_ALLOWED_HOSTS`** : l'adresse du site, sans `https://`.
- **`DJANGO_TIME_ZONE`** : le fuseau de l'église (`Africa/Kinshasa`, `Africa/Abidjan`, `Europe/Paris`…).
- **`DJANGO_SUPERUSER_USERNAME`** : l'identifiant du premier administrateur.

Pour changer un réglage, modifiez le fichier sur GitHub (icône crayon), validez, puis **Deploy** dans Dokploy.

**Pas de secret dans ce fichier** : le dépôt est public.

- La **clé secrète** est générée automatiquement au premier démarrage et conservée dans le volume (`/data/secret_key`).
- Le **mot de passe** du premier administrateur est généré et affiché une seule fois dans les logs (étape 6).
- Pour imposer vos propres valeurs, ajoutez `DJANGO_SECRET_KEY` ou `DJANGO_SUPERUSER_PASSWORD` dans l'onglet **Environment** de Dokploy, jamais dans le dépôt. Une variable de cet onglet est toujours prioritaire sur le fichier.

`DJANGO_DEBUG=false` et `DATA_DIR=/data` sont déjà réglés dans l'image. Les autres variables possibles sont dans [`.env.example`](.env.example).

## 4. Le volume de données (indispensable)

Onglet **Advanced → Volumes / Mounts → Add Volume** :

- **Type** : `Volume Mount` (volume Docker nommé, recommandé)
- **Volume name** : `danzapa-data`
- **Mount path** : `/data`

Sans ce volume, **tous les chants et cultes seraient perdus à chaque redéploiement**. Un `Bind Mount` vers un dossier du VPS fonctionne aussi : le conteneur donne lui-même les bons droits au dossier.

## 5. Domaine et HTTPS

Onglet **Domains → Add Domain** :

- **Host** : `danzapa.zweey.com`
- **Path** : `/`
- **Container Port** : `8000`
- **HTTPS** : activé, **Certificate** : `Let's Encrypt`

Dokploy fait la redirection HTTP → HTTPS et transmet l'en-tête `X-Forwarded-Proto`, que Danzapa sait lire.

## 6. Déployer et premier accès

1. Cliquez sur **Deploy**. Suivez l'onglet **Deployments / Logs**. La construction prend 1 à 3 minutes. À la fin, vous devez voir :
   ```
   Administrateur « admin » créé.
   ============================================================
     Créé le 04/10/2026 09:00
     Identifiant : admin
     Mot de passe provisoire : k7mq-x3vp-9rtd-h2wa
   ============================================================
   Listening at: http://0.0.0.0:8000
   ```
   Notez ce mot de passe : il n'est affiché qu'au premier démarrage. Il apparaît dans les logs du **conteneur** (onglet Logs de l'application), pas forcément dans ceux de la construction.
2. Ouvrez `https://danzapa.zweey.com`, connectez-vous avec `admin` et le mot de passe provisoire, puis changez-le tout de suite (**Mot de passe**, en haut à droite).
3. Créez les comptes de l'équipe : **Administration** (en haut à droite) → **Utilisateurs → Ajouter**. Choisissez ensuite le **groupe** de chacun :
   - **Éditeur** : prépare les cultes et gère les chants ;
   - **Lecteur** : consulte, exporte et projette ;
   - **Administrateur** : gère aussi les comptes. Cochez en plus « Statut équipe » pour qu'il accède à l'administration.
4. Mot de passe refusé ou perdu : voir la section suivante.

## Mot de passe incorrect ou oublié

Si plusieurs blocs « Mot de passe provisoire » apparaissent dans les logs, seul **le plus récent** (voir « Créé le ») est valable. S'il y en a un à chaque déploiement, le volume `/data` manque : les logs affichent alors « ATTENTION : aucun volume n'est monté sur /data » (étape 4).

Pour choisir un nouveau mot de passe, deux méthodes :

- **Avec le terminal** (onglet **Terminal** de l'application dans Dokploy, ou en SSH `docker exec -it $(docker ps -qf "name=danzapa" | head -1) sh`) :
  ```bash
  python manage.py changepassword admin
  ```
- **Sans terminal** : dans l'onglet **Environment**, ajoutez
  ```env
  DJANGO_SUPERUSER_PASSWORD=VotreNouveauMotDePasse
  DJANGO_SUPERUSER_RESET=1
  ```
  Puis **Deploy**. Les logs affichent « Mot de passe de « admin » remplacé ». Connectez-vous, puis **retirez ces deux lignes** et redéployez, sinon le mot de passe serait réimposé à chaque démarrage.

Pour vérifier que l'application répond : `https://danzapa.zweey.com/sante/` affiche `ok`. C'est aussi le healthcheck du conteneur.

## 7. Mettre à jour

À chaque nouvelle version poussée sur la branche, cliquez sur **Deploy** dans Dokploy. Les migrations s'appliquent toutes seules et les données du volume `/data` sont conservées.

Pour l'automatiser : onglet **Deployments**, copiez l'URL du **webhook**. Sur GitHub, ajoutez-la dans le dépôt (**Settings → Webhooks → Add webhook**, type `application/json`, évènement *push*). Vous pouvez aussi activer **Autodeploy** si Dokploy est relié à GitHub.

## 8. Sauvegardes

La commande suivante crée `/data/sauvegardes/danzapa-AAAAMMJJ-HHMMSS.tar.gz`, qui contient la base et les images. Elle garde les 14 dernières.

```bash
python manage.py sauvegarde
```

- **Planifier** : si votre version de Dokploy a l'onglet **Schedules** de l'application, ajoutez une tâche quotidienne avec la commande `python manage.py sauvegarde`. Sinon, ajoutez sur le VPS une ligne dans `crontab -e` :
  ```cron
  30 3 * * * docker exec $(docker ps -qf "name=danzapa" | head -1) python manage.py sauvegarde >/dev/null 2>&1
  ```
- **Copier une sauvegarde hors du VPS**, ce qui est recommandé :
  ```bash
  docker cp $(docker ps -qf "name=danzapa" | head -1):/data/sauvegardes ./sauvegardes-danzapa
  ```
- **Restaurer** : arrêtez l'application dans Dokploy, remplacez `db.sqlite3` et `media/` dans le volume par ceux de l'archive, puis relancez.

## 9. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| **Bad Request (400)** | Le domaine n'est pas dans `DJANGO_ALLOWED_HOSTS` | Corriger `config/production.env`, redéployer |
| **Erreur CSRF (403)** à la connexion | Le site est ouvert par une adresse différente de `DJANGO_ALLOWED_HOSTS`, ou sans HTTPS | Ouvrir `https://` + le sous-domaine ; si besoin, définir `DJANGO_CSRF_TRUSTED_ORIGINS=https://danzapa.zweey.com` |
| **Bad Gateway (502)** | Mauvais port dans le domaine, ou le conteneur a planté | Container Port = `8000` ; lire les logs du conteneur |
| Données perdues après un redéploiement, « ATTENTION : aucun volume » dans les logs | Pas de volume sur `/data` | Ajouter le volume (étape 4) avant de ressaisir |
| « Mot de passe incorrect » pour `admin` | Mot de passe d'un ancien démarrage, ou faute de frappe | Section « Mot de passe incorrect ou oublié » |
| Pas de certificat HTTPS | Le DNS ne pointe pas encore vers le VPS | Attendre la propagation, puis régénérer le certificat |

## Et si Nginx est devant Dokploy ?

Si un Nginx du VPS reçoit le trafic avant de le passer au conteneur, sa configuration doit transmettre l'hôte et le protocole :

```nginx
location / {
    proxy_pass http://127.0.0.1:PORT_DU_CONTENEUR;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    client_max_body_size 10m;   # envoi d'images de thème
}
```

## Tester l'image sur votre ordinateur

```bash
cp .env.example .env      # puis remplir DJANGO_SECRET_KEY et DJANGO_SUPERUSER_PASSWORD
# pour un test sans HTTPS, mettre aussi : DJANGO_ALLOWED_HOSTS=localhost
docker compose up --build
```

Ouvrez ensuite http://localhost:8000. Les cookies de connexion étant marqués « sécurisés », passez par `localhost` et non par une adresse IP.
