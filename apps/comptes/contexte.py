from django.conf import settings


def etat_du_serveur(request):
    """Signale dans toutes les pages un déploiement sans volume de données."""
    return {
        "donnees_persistantes": settings.DONNEES_PERSISTANTES,
        "medias_persistants": settings.MEDIAS_PERSISTANTS,
        "connexion_desactivee": settings.CONNEXION_DESACTIVEE,
    }
