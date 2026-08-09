"""Servizio Menu: business logic per il nuovo menu.

Orchestra il repository ``prodotti`` per recuperare i piatti classificati
per merceologia (primi, secondi, contorni). Usato dalla UI Nuovo Menu e dal
backend SaaS (endpoint /menu).
"""

from core.repositories import prodotti as prodotti_repo


def prodotti_menu(tenant_id=None):
    """Restituisce i prodotti del menu raggruppati per merceologia.

    Args:
        tenant_id: se valorizzato filtra per tenant (SaaS).

    Returns:
        dict con chiavi ``primi``, ``secondi``, ``contorni``.
        Ogni voce e' una lista di dict ``{'prodotto': ..., 'plu': ...}``.
    """
    return {
        "primi": prodotti_repo.recupera_primi(tenant_id),
        "secondi": prodotti_repo.recupera_secondi(tenant_id),
        "contorni": prodotti_repo.recupera_contorni(tenant_id),
    }


def primi(tenant_id=None):
    """Prodotti della merceologia 'Primi piatti'."""
    return prodotti_repo.recupera_primi(tenant_id)


def secondi(tenant_id=None):
    """Prodotti della merceologia 'Secondi piatti'."""
    return prodotti_repo.recupera_secondi(tenant_id)


def contorni(tenant_id=None):
    """Prodotti della merceologia 'Contorni'."""
    return prodotti_repo.recupera_contorni(tenant_id)
