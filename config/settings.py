"""Paramètres Django du projet Danzapa.

Les valeurs propres à l'environnement se lisent dans les variables
d'environnement (voir `.env.example`), avec pour valeurs par défaut celles de
`config/production.env` (versionné, sans aucun secret).
"""

import os
import secrets
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nom, defaut=False):
    return os.environ.get(nom, str(defaut)).lower() in ("1", "true", "yes", "oui")


def env_list(nom, defaut=""):
    return [v.strip() for v in os.environ.get(nom, defaut).split(",") if v.strip()]


def charger_fichier_env(chemin):
    """Lit des lignes NOM=valeur comme valeurs par défaut.

    Les variables déjà définies (onglet « Environment » de Dokploy) restent
    prioritaires ; les lignes vides, les commentaires et les valeurs vides
    sont ignorés.
    """
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        nom, valeur = (morceau.strip() for morceau in ligne.split("=", 1))
        if valeur:
            os.environ.setdefault(nom, valeur)


def cle_persistante(chemin):
    """Clé secrète générée une fois puis conservée dans le volume de données.

    Évite de devoir la saisir dans Dokploy. La création exclusive (O_EXCL)
    empêche deux processus de générer chacun une clé différente.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    try:
        descripteur = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        for _ in range(50):  # un autre processus est peut-être en train de l'écrire
            cle = chemin.read_text().strip()
            if cle:
                return cle
            time.sleep(0.1)
        raise RuntimeError(f"Clé secrète vide dans {chemin}.")
    cle = secrets.token_urlsafe(50)
    with os.fdopen(descripteur, "w") as fichier:
        fichier.write(cle)
    return cle


charger_fichier_env(BASE_DIR / "config" / "production.env")

DEBUG = env_bool("DJANGO_DEBUG", True)

# Données persistantes (base SQLite, images envoyées, clé secrète). Dans l'image
# Docker, DATA_DIR=/data : un seul volume à monter pour tout conserver.
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))


def donnees_persistantes(dossier):
    """Faux quand, dans l'image Docker, aucun volume n'est monté sur /data :
    la base est alors dans le conteneur et disparaît au prochain déploiement."""
    if str(dossier) != "/data":
        return True  # hors Docker (développement)
    try:
        return os.stat(dossier).st_dev != os.stat("/").st_dev
    except OSError:
        return True



SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-uniquement-ne-pas-utiliser-en-production"
    else:
        SECRET_KEY = cle_persistante(DATA_DIR / "secret_key")

# localhost reste toujours autorisé : le healthcheck du conteneur l'interroge en interne.
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS") + ["localhost", "127.0.0.1"]
# Derrière le proxy HTTPS (Dokploy/Traefik, Nginx…), Django exige que l'origine
# des formulaires soit déclarée. Par défaut : https:// + chaque hôte autorisé.
def origines_https(hotes):
    return [f"https://{h.lstrip('.')}" for h in hotes if h not in ("*", "localhost", "127.0.0.1")]


CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS") or origines_https(ALLOWED_HOSTS)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.comptes",
    "apps.chants",
    "apps.cultes",
    "apps.projection",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sert les fichiers statiques (CSS, JS) en production, sans Nginx dédié.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.comptes.contexte.etat_du_serveur",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

def base_postgresql(url):
    """Réglages Django à partir d'une adresse postgresql://utilisateur:mot_de_passe@hôte:port/base
    (l'« Internal Connection URL » affichée par Dokploy pour une base PostgreSQL)."""
    morceaux = urlsplit(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(morceaux.path.lstrip("/")),
        "USER": unquote(morceaux.username or ""),
        "PASSWORD": unquote(morceaux.password or ""),
        "HOST": morceaux.hostname or "localhost",
        "PORT": str(morceaux.port or 5432),
        "CONN_MAX_AGE": 60,
    }


# Base de données :
# - DATABASE_URL=postgresql://… (base PostgreSQL séparée, par exemple créée dans
#   Dokploy) : comptes, mots de passe, chants et cultes y sont conservés,
#   indépendamment du conteneur de l'application ;
# - sinon DATABASE_ENGINE=postgresql avec les variables DATABASE_* ;
# - sinon SQLite dans DATA_DIR (développement, ou volume /data).
if os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
    DATABASES = {"default": base_postgresql(os.environ["DATABASE_URL"])}
elif os.environ.get("DATABASE_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DATABASE_NAME", "danzapa"),
            "USER": os.environ.get("DATABASE_USER", "danzapa"),
            "PASSWORD": os.environ.get("DATABASE_PASSWORD", ""),
            "HOST": os.environ.get("DATABASE_HOST", "localhost"),
            "PORT": os.environ.get("DATABASE_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "db.sqlite3",
            # Plusieurs workers Gunicorn : attendre un verrou plutôt qu'échouer.
            "OPTIONS": {"timeout": 20},
        }
    }

BASE_EXTERNE = DATABASES["default"]["ENGINE"].endswith("postgresql")
# Avec une base PostgreSQL séparée, les données ne dépendent plus du volume /data
# (qui ne garde alors que les images des thèmes et la clé secrète générée).
DONNEES_PERSISTANTES = BASE_EXTERNE or donnees_persistantes(DATA_DIR)

AUTH_USER_MODEL = "comptes.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "comptes:connexion"
LOGIN_REDIRECT_URL = "accueil"
LOGOUT_REDIRECT_URL = "comptes:connexion"

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Europe/Paris")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"
# Taille maximale d'un envoi (images de thème : 5 Mo, voir apps/projection).
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # La redirection HTTP → HTTPS est faite par le proxy (Dokploy) ; l'activer
    # ici aussi casserait le healthcheck interne en HTTP.
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", False)
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "0"))

# Journaux sur la sortie standard : visibles dans l'onglet « Logs » de Dokploy.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"), "propagate": False},
    },
}
