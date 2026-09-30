"""Rôles de Danzapa, portés par les groupes Django.

- Administrateur : gère les utilisateurs et a tous les droits sur le contenu.
- Éditeur : crée et modifie les chants, les cultes et les thèmes.
- Lecteur : consulte les chants et les cultes, lance la projection.

Les permissions sont exprimées par application et par action. Celles des
applications pas encore créées (chants, cultes…) sont simplement ignorées
jusqu'à ce que leurs migrations existent.
"""

from django.contrib.auth.models import Group, Permission

ADMINISTRATEUR = "Administrateur"
EDITEUR = "Éditeur"
LECTEUR = "Lecteur"

# Applications dont le contenu est géré par les rôles.
APPS_CONTENU = ["chants", "cultes", "projection", "bible"]

ROLES = {
    ADMINISTRATEUR: {
        "apps": APPS_CONTENU + ["comptes"],
        "actions": ["view", "add", "change", "delete"],
        "extra": ["auth.view_group"],
    },
    EDITEUR: {
        "apps": APPS_CONTENU,
        "actions": ["view", "add", "change", "delete"],
        "extra": [],
    },
    LECTEUR: {
        "apps": APPS_CONTENU,
        "actions": ["view"],
        "extra": [],
    },
}


def permissions_du_role(nom):
    config = ROLES[nom]
    perms = Permission.objects.none()
    for action in config["actions"]:
        perms |= Permission.objects.filter(
            content_type__app_label__in=config["apps"],
            codename__startswith=f"{action}_",
        )
    for code in config["extra"]:
        app_label, codename = code.split(".")
        perms |= Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        )
    return perms.distinct()


def synchroniser_roles(**kwargs):
    """Crée les groupes manquants et aligne leurs permissions sur ROLES."""
    for nom in ROLES:
        groupe, _ = Group.objects.get_or_create(name=nom)
        groupe.permissions.set(permissions_du_role(nom))
