"""Servizio Lotti: business logic per gestione ingresso merce e lotti.

Orchestra i repository ``core.repositories.lotti`` e ``core.repositories.prodotti``.
Usato dalla UI (ingresso merce, chiudi lotto, vendita) e dal backend SaaS.
"""

from core.repositories import lotti as lotti_repo
from core.repositories import prodotti as prodotti_repo


# ------------------------------------------------------------------------- #
#  Lotti aperti / ingresso merce
# ------------------------------------------------------------------------- #

def lotti_aperti(tenant_id=None):
    """Restituisce l'elenco dei lotti aperti (dict con number/fornit/name/peso).

    Args:
        tenant_id: se valorizzato filtra per tenant (SaaS).
    """
    return lotti_repo.lotti_aperti(tenant_id)


def progressivo_ingresso(tenant_id=None):
    """Restituisce il progressivo di ingresso corrente."""
    return lotti_repo.recupera_progressivo_ingresso(tenant_id)


# ------------------------------------------------------------------------- #
#  Fornitori
# ------------------------------------------------------------------------- #

def lista_fornitori_ingresso(tenant_id=None):
    """Restituisce i fornitori abilitati all'ingresso merce."""
    return lotti_repo.recupera_lista_fornitori(tenant_id)


# ------------------------------------------------------------------------- #
#  Prodotti / merceologie / tagli
# ------------------------------------------------------------------------- #

def prodotti_menu(tenant_id=None):
    """Restituisce i prodotti del menu raggruppati per merceologia.

    Args:
        tenant_id: se valorizzato filtra per tenant (SaaS).

    Returns:
        dict con chiavi ``primi``, ``secondi``, ``contorni``.
    """
    return {
        "primi": prodotti_repo.recupera_primi(tenant_id),
        "secondi": prodotti_repo.recupera_secondi(tenant_id),
        "contorni": prodotti_repo.recupera_contorni(tenant_id),
    }


def tagli_per_merceologia(merceologia_id, tenant_id=None):
    """Restituisce i nomi dei tagli di una merceologia."""
    return prodotti_repo.lista_tagli(merceologia_id, tenant_id)


def nome_merceologia(merceologia_id):
    """Restituisce il nome della merceologia dato il suo ID."""
    return prodotti_repo.recupera_merceologia_da_id(merceologia_id)
